# summarization_agent.py
# 使用摘要机制的实现：按 token 预算压缩旧对话，只保留摘要 + 最近上下文

import tiktoken
from env import env
from openai import OpenAI

client = OpenAI(api_key=env["API_KEY"], base_url=env["API_URL"])

# cl100k_base 与多数现代模型接近；DeepSeek 略有偏差，教学场景足够
_encoder = tiktoken.get_encoding("cl100k_base")

system_prompt = "你是一个专业、严谨且贴心的私人健康管理师"

# 原始对话（不含摘要）超过此 token 数时触发压缩
MAX_HISTORY_TOKENS = 2000
# 压缩后至少保留最近这么多 token 的原始对话
MIN_RECENT_TOKENS = 600
# 兜底：至少保留最近 2 轮（4 条消息），避免短句来回时过度压缩
MIN_RECENT_TURNS = 2

summary = ""
chat_history = [{"role": "system", "content": system_prompt}]


def _count_tokens(text: str) -> int:
    return len(_encoder.encode(text))


def _count_messages_tokens(messages: list[dict]) -> int:
    return sum(_count_tokens(m["content"]) for m in messages)


def _non_system_messages() -> list[dict]:
    return [m for m in chat_history if m["role"] != "system"]


def _build_context_messages() -> list[dict]:
    """发给模型的上下文 = system + 摘要 + 最近对话"""
    messages = [{"role": "system", "content": system_prompt}]
    if summary:
        messages.append(
            {
                "role": "system",
                "content": f"【此前对话摘要，请据此延续上下文】\n{summary}",
            }
        )
    messages.extend(_non_system_messages())
    return messages


def _compress_old_messages(old_messages: list[dict]) -> str:
    """把一段旧对话合并进叙事摘要"""
    chat_text = "\n".join(
        f"{m['role']}: {m['content']}" for m in old_messages
    )
    prompt = f"""请将以下对话压缩为简洁摘要（不超过 200 字）。
重点保留：过敏史、疾病、饮食禁忌、健康目标、用户情绪与近期重要事件。
不要编造未出现的信息。

已有摘要：
{summary or "（无）"}

待压缩对话：
{chat_text}

只输出更新后的摘要正文，不要加标题或解释。"""

    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


def _find_compress_split(non_system: list[dict]) -> int | None:
    """
    从头部找出可压缩的分割点：尾部保留 >= MIN_RECENT_TOKENS 且 >= MIN_RECENT_TURNS 轮。
    返回 split 索引（compress = [:split], keep = [split:]）；None 表示不应压缩。
    """
    min_keep_messages = MIN_RECENT_TURNS * 2
    if len(non_system) <= min_keep_messages:
        return None

    tail_tokens = 0
    split_idx = len(non_system)

    for i in range(len(non_system) - 1, -1, -1):
        tail_tokens += _count_tokens(non_system[i]["content"])
        kept_count = len(non_system) - i
        if tail_tokens >= MIN_RECENT_TOKENS and kept_count >= min_keep_messages:
            split_idx = i
            break

    if split_idx == 0:
        return None
    return split_idx


def maybe_summarize() -> None:
    """对话 token 超预算时：压缩头部旧消息，保留尾部原文"""
    global summary
    # 提取非系统prompt，保证系统prompt不会被摘要
    non_system = _non_system_messages()
    if _count_messages_tokens(non_system) <= MAX_HISTORY_TOKENS:
        return

    split_idx = _find_compress_split(non_system)
    if split_idx is None:
        return

    to_compress = non_system[:split_idx]
    to_keep = non_system[split_idx:]

    summary = _compress_old_messages(to_compress)
    chat_history[:] = [{"role": "system", "content": system_prompt}] + to_keep

    kept_tokens = _count_messages_tokens(to_keep)
    print(
        f"\n[已压缩 {len(to_compress)} 条消息"
        f"（{_count_messages_tokens(to_compress)} tokens）"
        f"，保留 {kept_tokens} tokens 原文，当前摘要]\n{summary}\n"
    )


print("个人健康助理（摘要模式），输入 quit 退出")

while True:
    user_input = input("User: ")

    if user_input.lower().strip() == "quit":
        break

    chat_history.append({"role": "user", "content": user_input})

    try:
        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            # 如果有摘要，那么上下文采用“system + 摘要 + 最近对话“的形式
            messages=_build_context_messages(),
        )

        agent_reply = response.choices[0].message.content

        print(f"\nAgent: {agent_reply}\n")

        chat_history.append({"role": "assistant", "content": agent_reply})
        # 如果对话长度超过一定token，则触发摘要操作
        maybe_summarize()

    except Exception as e:
        print(f"[发生错误] {e}")
        break
