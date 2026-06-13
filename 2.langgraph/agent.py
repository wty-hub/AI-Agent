from typing import TypedDict
from langgraph.graph import StateGraph, END
import requests

from env import env
from web_search import web_search
from openai import OpenAI


# 全局状态，每个节点的共享数据
class ReportState(TypedDict):
    topic: str  # 调研主题
    search_data: str  # 查阅到的资料
    draft: str  # 报告草稿
    feedback: str  # 审核员的修改意见
    iterations: int  # 重写的次数


client = OpenAI(api_key=env["API_KEY"], base_url="https://api.deepseek.com")


def call_llm(system: str, user: str):
    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content.strip()


def search_node(state: ReportState):
    print(f"[调研员] 正在全网搜索关于 {state['topic']} 的内容")
    topic = state["topic"]
    search_data = web_search(topic, 5)
    return {"search_data": search_data}


def write_node(state: ReportState):
    current_iter = state.get("iterations", 0)
    print(f"[主笔] 正在撰写报告的第 {current_iter} 稿")
    if state.get("feedback"):
        print(f"[主笔] 收到修改意见：{state['feedback']}")
        # 根据意见撰写下一稿
        user_prompt = f"""请根据审核意见修改报告。
主题：{state['topic']}
参考资料：
{state['search_data']}
上一稿：
{state['draft']}
审核意见：
{state['feedback']}
请输出修改后的完整报告，不要只写改动部分。"""
    else:
        user_prompt = f"""请根据以下资料，撰写一份结构清晰的调研报告。
主题：{state['topic']}
参考资料：
{state['search_data']}
要求：
- 包含：背景、核心发现、分析、结论
- 基于资料，不要编造
- 中文，800~1500 字"""

    draft = call_llm(
        system="你是专业调研报告主笔，擅长把搜索结果整理成有条理的分析报告。",
        user=user_prompt,
    )
    return {"draft": draft, "iterations": current_iter + 1}


def reviewer_node(state: ReportState):
    print("[审核员] 正在检查报告")
    user_prompt = f"""请审核以下调研报告。
主题：{state['topic']}
报告正文：
{state['draft']}
审核标准：
1. 是否紧扣主题
2. 结论是否有资料支撑
3. 结构是否清晰（背景、发现、分析、结论）
4. 有无明显事实错误或空洞内容
如果报告合格，只回复 exactly: OK
如果不合格，列出具体修改意见（条目式，不超过 5 条），不要输出 OK。"""
    feedback = call_llm(
        system="你是严格的报告审核员。合格时只回复 OK，不合格时只给修改意见。",
        user=user_prompt,
    )
    return {"feedback": feedback}


# 节点间传递的状态是 ReportState
workflow = StateGraph(ReportState)

workflow.add_node("searcher", search_node)
workflow.add_node("writer", write_node)
workflow.add_node("reviewer", reviewer_node)

workflow.set_entry_point("searcher")
workflow.add_edge("searcher", "writer")
workflow.add_edge("writer", "reviewer")


def review_route(state: ReportState):
    if state["feedback"].strip() == "OK":
        return "accept"
    elif state["iterations"] > 5:
        # 最多迭代 5 次
        return "timeout"
    else:
        return "reject"


workflow.add_conditional_edges(
    "reviewer",
    review_route,
    {
        "accept": END,
        "reject": "writer",
        "timeout": END,
    },
)

app = workflow.compile()

if __name__ == "__main__":
    initial_state = {"topic": "三星最新手机的产品分析"}
    # 阻塞执行，直到 END
    final_state = app.invoke(initial_state)
    print("最终版报告：\n" + final_state["draft"])
