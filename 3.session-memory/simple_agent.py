# simple_agent.py
# 最简的 AI 健康助理实现，不采用记忆机制

from env import env
from openai import OpenAI

client = OpenAI(api_key=env["API_KEY"], base_url=env["API_URL"])

system_prompt = "你是一个专业、严谨且贴心的私人健康管理师"

chat_history = [{"role": "system", "content": system_prompt}]

print("个人健康助理，输入 quit 退出")

while True:
    user_input = input("User: ")
    
    if user_input.lower().strip() == "quit":
        break

    chat_history.append({"role": "user", "content": user_input})

    try:
        response = client.chat.completions.create(
            model="deepseek-v4-flash", messages=chat_history
        )

        agent_reply = response.choices[0].message.content

        print(f"\nAgent: {agent_reply}\n")

        chat_history.append({"role": "assistant", "content": agent_reply})

    except Exception as e:
        print(f"[发生错误] {e}")
        break
