# memory.py

import json
import sqlite3
from pydantic import BaseModel, Field
from typing import List


# 使用 pydantic 规定记忆的结构，限制 AI 输出正确的格式
class HealthProfile(BaseModel):
    allergies: List[str] = Field(default=[], description="明确的过敏源")
    chronic_conditions: List[str] = Field(default=[], description="慢病或确诊旧伤")
    dietary_restrictions: List[str] = Field(default=[], description="饮食禁忌")
    current_goals: List[str] = Field(default=[], description="当前健康目标")
    unresolved_issues: List[str] = Field(
        default=[], description="用户提出但尚未解决的问题"
    )


class MemoryState(BaseModel):
    narrative_summary: str = Field(
        ..., description="对抛弃的旧对话进行不超过200字的硬核摘要"
    )
    updated_profile: HealthProfile = Field(..., description="全量更新后的结构化档案")


# 使用 sqlite 持久化保存用户档案和对话历史
DB_FILE = "agent_memory.db"


def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # 用户状态表
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_states (
                user_id TEXT PRIMARY KEY,
                narrative_summary TEXT DEFAULT '',
                structured_profile TEXT DEFAULT '{}',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        # 对话历史表
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                role TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        conn.commit()


init_db()


def load_user_memory(user_id):
    """从数据库读取用户的档案"""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT narrative_summary, structured_profile FROM user_states WHERE user_id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        if row:
            return row[0], json.loads(row[1])
        # 默认初始状态
        return "", HealthProfile().model_dump()


def save_user_memory(user_id: str, summary: str, profile: dict):
    """将状态持久化写入 SQLite"""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_states (user_id, narrative_summary, structured_profile, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                narrative_summary = excluded.narrative_summary,
                structured_profile = excluded.structured_profile,
                updated_at = CURRENT_TIMESTAMP
        """,
            (user_id, summary, json.dumps(profile, ensure_ascii=False)),
        )
        conn.commit()


def load_recent_chat_history(user_id: str, limit: int = 20) -> list:
    """从数据库捞取最近 N 条裸对话日志"""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content FROM chat_logs WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
        rows = cursor.fetchall()
        # 倒序捞出需要正序排列
        return [{"role": row[0], "content": row[1]} for row in reversed(rows)]


def save_chat_log(user_id: str, role: str, content: str):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_logs (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content),
        )
        conn.commit()
