#!/usr/bin/env python3
"""将测试场景写入 SQLite，用于触发 agent.py 的压缩逻辑。"""

import argparse
import json
import sqlite3
from pathlib import Path

from count_tokens import count_tokens
from memory import DB_FILE, save_chat_log, save_user_memory

TOKEN_LIMIT = 15_000
CHAT_WINDOW_LIMIT = 20
DEFAULT_USER = "user_001"
SCENARIO_PATH = Path(__file__).parent / "test_data" / "compression_trigger_scenario.json"

# 每条 filler 末尾附加的填充句，用于把单条消息撑到目标 token 数
_PADDING_SENTENCE = (
    "另外我想补充一下最近的生活节奏：工作日久坐、周末偶尔爬山、"
    "饮食以家常中餐为主，少油少盐，但应酬时会喝少量啤酒。"
)


def _pad_to_tokens(text: str, target_tokens: int) -> str:
    """在文本末尾循环追加填充句，直到 count_tokens 达到目标。"""
    if target_tokens <= 0:
        return text
    if count_tokens([{"role": "user", "content": text}]) >= target_tokens:
        return text
    padded = text
    while count_tokens([{"role": "user", "content": padded}]) < target_tokens:
        padded += _PADDING_SENTENCE
    return padded


def build_messages(scenario: dict) -> list[dict]:
    """根据场景配置展开完整对话列表。"""
    messages: list[dict] = []

    for turn in scenario["turns"]:
        messages.append({"role": "user", "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["assistant"]})

    per_message_tokens = scenario["padding"]["tokens_per_message"]
    for template in scenario["filler_templates"]:
        user_text = _pad_to_tokens(template["user"], per_message_tokens)
        assistant_text = _pad_to_tokens(template["assistant"], per_message_tokens)
        messages.append({"role": "user", "content": user_text})
        messages.append({"role": "assistant", "content": assistant_text})

    return messages


def verify_window(messages: list[dict]) -> tuple[list[dict], int]:
    """模拟 agent.py：取最近 CHAT_WINDOW_LIMIT 条并计算 token。"""
    window = messages[-CHAT_WINDOW_LIMIT:]
    return window, count_tokens(window)


def seed_user(user_id: str, messages: list[dict], reset: bool) -> None:
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        if reset:
            cursor.execute("DELETE FROM chat_logs WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
            conn.commit()

    for msg in messages:
        save_chat_log(user_id, msg["role"], msg["content"])

    save_user_memory(user_id, "", {})


def write_scenario_file(scenario: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(scenario, f, ensure_ascii=False, indent=2)


def build_default_scenario() -> dict:
    return {
        "name": "compression_trigger_scenario",
        "description": (
            "为 agent.py 准备的压缩触发场景：第 1 轮埋入青霉素严重过敏史，"
            "中间插入多条带 padding 的低价值寒暄，使最近 20 条消息超过 "
            f"{TOKEN_LIMIT} tokens；最后一轮用阿莫西林探针验证压缩后是否保留关键事实。"
        ),
        "target_user_id": DEFAULT_USER,
        "agent_token_limit": TOKEN_LIMIT,
        "agent_chat_window_limit": CHAT_WINDOW_LIMIT,
        "critical_fact": {
            "introduced_at_turn": 1,
            "user_statement": "我对青霉素严重过敏，之前打青霉素休克进过 ICU，这个务必记牢。",
            "expected_behavior": "涉及 β-内酰胺类抗生素（如阿莫西林）时必须明确禁止并提醒过敏风险",
            "probe_user_message": "社区医生想给我开阿莫西林治咽炎，我能吃吗？",
        },
        "padding": {
            "tokens_per_message": 1100,
            "note": "共 9 轮 filler + 1 轮关键事实 = 20 条消息；窗口满时仍含过敏史，且 token 总数超过 15000",
        },
        "turns": [
            {
                "user": "我对青霉素严重过敏，之前打青霉素休克进过 ICU，这个务必记牢。",
                "assistant": (
                    "已记录：您对青霉素有严重过敏史并曾发生休克，属于高风险禁忌。"
                    "今后涉及抗生素方案时我会优先排除青霉素类及交叉过敏可能的相关药物，"
                    "并建议您就医时主动告知医护人员。"
                ),
            }
        ],
        "filler_templates": [
            {
                "user": "嗯嗯",
                "assistant": "好的，我在。您今天感觉怎么样？如果暂时没有具体健康问题，也可以随便聊聊日常习惯，我会尽量给出简单易行的建议。",
            },
            {
                "user": "好的",
                "assistant": "收到。健康管理很多时候就是从小处着手：规律作息、均衡饮食、适度活动。您有想改善的方面可以慢慢说，不用一次说完。",
            },
            {
                "user": "哈哈",
                "assistant": "看来心情不错，保持愉快对免疫和睡眠都有帮助。要是愿意，我们可以聊聊您最近的运动或饮食，看看有没有可以轻松调整的地方。",
            },
            {
                "user": "OK",
                "assistant": "明白。若暂时没有新问题，建议您今天记得适量喝水、避免久坐。有情况随时叫我。",
            },
            {
                "user": "知道了",
                "assistant": "好的，已了解。日常保健不必追求一步到位，能坚持每天一点小进步就很不错。",
            },
            {
                "user": "谢谢",
                "assistant": "不客气，这是我应该做的。您如果之后想到任何健康相关的问题，无论是饮食、运动还是睡眠，都可以继续问我。",
            },
            {
                "user": "收到",
                "assistant": "好的，祝您今天顺利。记得适当活动一下，长时间看屏幕的话每隔一小时起来走走。",
            },
            {
                "user": "好哒",
                "assistant": "嗯嗯，有进展随时同步。维持习惯比偶尔突击更重要，我们慢慢来调整就好。",
            },
            {
                "user": "嗯",
                "assistant": "我在听。您要是现在没有特别想问的，也可以告诉我今天吃了什么、睡了多久，我帮您做个简单回顾。",
            },
        ],
        "usage": {
            "seed": "python seed_test_data.py",
            "run_agent": "python agent.py",
            "probe_after_seed": "启动 agent 后输入 probe 消息，或再发任意消息即可触发压缩",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="生成并导入压缩触发测试数据")
    parser.add_argument("--user", default=DEFAULT_USER, help="写入的目标用户 ID")
    parser.add_argument(
        "--scenario",
        default=str(SCENARIO_PATH),
        help="场景 JSON 路径；不存在则自动生成",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="不清空该用户已有记录，追加写入",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只计算 token，不写入数据库",
    )
    args = parser.parse_args()

    scenario_path = Path(args.scenario)
    if scenario_path.exists():
        with scenario_path.open(encoding="utf-8") as f:
            scenario = json.load(f)
    else:
        scenario = build_default_scenario()
        write_scenario_file(scenario, scenario_path)
        print(f"[生成] 场景文件已写入: {scenario_path}")

    messages = build_messages(scenario)
    window, window_tokens = verify_window(messages)

    print(f"场景: {scenario['name']}")
    print(f"总消息数: {len(messages)}（{len(messages) // 2} 轮）")
    print(f"滑动窗口: 最近 {len(window)} 条 -> {window_tokens} tokens")
    print(f"压缩阈值: {TOKEN_LIMIT} tokens -> {'会触发' if window_tokens > TOKEN_LIMIT else '不会触发'}")

    if not args.dry_run:
        seed_user(args.user, messages, reset=not args.no_reset)
        print(f"\n[完成] 已导入用户 {args.user}，数据库: {DB_FILE}")
        print("下一步: 运行 python agent.py，输入任意消息即可观察压缩流程。")
        print(f"探针问题: {scenario['critical_fact']['probe_user_message']}")
    else:
        print("\n[dry-run] 未写入数据库。")


if __name__ == "__main__":
    main()
