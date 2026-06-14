from openai import OpenAI
from env import env
from memory import *
from count_tokens import count_tokens

client = OpenAI(api_key=env["API_KEY"], base_url=env["API_URL"])


def _extract_json(text: str) -> str:
    """从模型回复中提取 JSON 正文（兼容 ```json 代码块）。"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]  # 去掉 ```json
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def run_compression_engine(
    stale_messages: list, current_summary: str, current_profile: dict
):
    """为了压缩而进行的模型调用"""

    chat_text = "\n".join([f"{m['role']}: {m['content']}" for m in stale_messages])
    schema_hint = json.dumps(MemoryState.model_json_schema(), ensure_ascii=False, indent=2)
    system_instruction = f"""
你是内存管理守护进程。你的任务是合并上下文并更新用户档案。

[当前系统状态]
旧版摘要: {current_summary if current_summary else '无'}
现有档案: {current_profile}

[待合并的新鲜对话]
{chat_text}

[执行指令]
1. 提取新鲜对话中的核心健康事实，与【现有档案】进行合并/去重/覆盖。
2. 将新鲜对话中的关键语境，补充到【旧版摘要】中，生成连贯的新摘要，抛弃寒暄废话。
3. 只输出一个 JSON 对象，不要输出任何解释、Markdown 或代码块。

[输出 JSON Schema]
{schema_hint}
    """

    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {"role": "system", "content": "你是一个只输出 JSON 的数据整理机。"},
            {"role": "user", "content": system_instruction},
        ],
    )
    raw = response.choices[0].message.content or ""
    return MemoryState.model_validate_json(_extract_json(raw))


def assemble_prompt(profile: dict, summary: str):
    profile_str = json.dumps(profile, ensure_ascii=False, indent=2)
    return f"""你是一个顶尖的健康管理师。下面是你获取到的用户信息：

[绝对遵循的底层生理指标]
{profile_str}

[历史对话摘要]
{summary if summary else "暂无历史"}

请基于以上事实，直接回应用户的最新问题。不要重复陈述上述已知信息。"""



TOKEN_LIMIT = 15_000  # 为了方便在 Demo 中触发压缩，调小阈值
CURRENT_USER = "user_001"  # 模拟当前登录的用户 ID
base_persona = "你是一个专业、严谨且贴心的私人健康管理师"

print(f"个人健康 Agent 启动。当前用户: {CURRENT_USER}")

while True:
    user_input = input("User: ")
    if user_input.lower() == "quit":
        break

    # 实时持久化保存用户输入
    save_chat_log(CURRENT_USER, "user", user_input)

    # 从数据库重新载入当前的滑动窗口与记忆状态（确保无内存泄漏、支持并发）
    db_summary, db_profile = load_user_memory(CURRENT_USER)
    chat_window = load_recent_chat_history(CURRENT_USER, limit=20)

    # 检测是否超过 token 限制
    current_tokens = count_tokens(chat_window)
    if current_tokens > TOKEN_LIMIT:
        print(
            f"\n[系统] Context Window 饱和 ({current_tokens} tokens)。触发压缩操作..."
        )

        # 将最新的 4 条留在窗口，其余判定为陈旧数据
        stale_data = chat_window[:-4]

        # 运行压缩引擎
        new_state = run_compression_engine(stale_data, db_summary, db_profile)

        # 状态回写数据库
        db_summary = new_state.narrative_summary
        db_profile = new_state.updated_profile.model_dump()
        save_user_memory(CURRENT_USER, db_summary, db_profile)

        # 重新载入裁剪后的滑动窗口
        chat_window = load_recent_chat_history(CURRENT_USER, limit=4)
        print(f"[系统] 状态已成功归档到 SQLite。当前档案: {db_profile}\n")

    # 组装最终 Payload
    system_prompt = assemble_prompt(db_profile, db_summary)
    payload = [{"role": "system", "content": system_prompt}] + chat_window

    # 发起对话推理
    response = client.chat.completions.create(
        model="deepseek-v4-flash", messages=payload
    )

    reply = response.choices[0].message.content
    print(f"\nAgent: {reply}\n")

    # 持久化助手回复
    save_chat_log(CURRENT_USER, "assistant", reply)
