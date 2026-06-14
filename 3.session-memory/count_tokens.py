import tiktoken


def count_tokens(messages: list, model: str = "gpt-4o") -> int:
    """Token 计算器，包含 API 调用的隐藏头部开销"""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    num_tokens = 0
    for message in messages:
        num_tokens += 3  # 每条消息的基础开销
        for key, value in message.items():
            if isinstance(value, str):
                num_tokens += len(encoding.encode(value))
    num_tokens += 3  # 助手回复的首字母开销
    return num_tokens
