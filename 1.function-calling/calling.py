import requests


# 按照一定的标准，写好这个工具的描述字典
tools = [{"type": "function", "function": {"name": "get_weather", ...}}]

# 
messages = [{"role": "user", "content": "今天天气怎么样？"}]