from openai import OpenAI
import json
from get_weather import get_weather

# 我把 url 这些环境变量独立为一个组件了
from env import env

# 使用 deepseek api，其兼容 openai 库
client = OpenAI(api_key=env["API_KEY"], base_url="https://api.deepseek.com")

# 初始化一个上下文
messages = [
    {
        "role": "system",
        "content": "你是一个硬核的AI助手。你需要调用工具来获取实时信息，并给出精准的回答。",
    },
    {"role": "user", "content": "武汉和深圳今天哪里更适合出行？"},
]

# 定义 AI 如何调用 本地函数
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",  # 必须和 Python 里的函数名一致
            # 这里必须描述得精确详细
            "description": "当用户询问天气、气温、穿衣建议时调用此工具。必须传入具体的城市名称。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市或区县名称，例如：北京, 深圳, 南山",
                    }
                },
                "required": ["city"],  # 告诉模型这个参数不给不行
            },
        },
    }
]


print("Agent启动，开始思考...")

while True:
    # 获得模型的回复
    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=messages,  # 传入 context
        tools=tools,  # 传入工具定义
        tool_choice="auto",
    )

    # 获取模型的回复（默认选第一条回复）
    ai_message = response.choices[0].message

    # 加入 context
    messages.append(ai_message)

    if ai_message.tool_calls:
        # 如果模型决定调用工具
        print(f"模型决定分配 {len(ai_message.tool_calls)} 个任务")

        for tool_call in ai_message.tool_calls:
            # 提取函数名和参数
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)
            print(f'  ai 决定执行：{func_name}({func_args})')
            
            if func_name == "get_weather":
                print(f"    [执行工具]：正在查询 {func_args['city']} 的天气")

                weather_result = get_weather(func_args["city"])
                print(f"    [查询结果]：{weather_result}")

                #
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": func_name,
                        "content": weather_result,
                    }
                )

    else:
        print("最终回答：")
        print(ai_message.content)
        break
