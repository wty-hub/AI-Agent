# web_search.py

from env import env
import requests

def web_search(query: str, max_results: int = 5):
    api_key = env["TAVILY_API_KEY"]
    response = requests.post(
        "https://api.tavily.com/search",
        json={
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            # 搜索资料全文，而不是默认的 简介 + url
            "search_depth": "advanced",
            "include_raw_content": True,
        },
        timeout=10,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    # results是列表，拼成字符串
    snippets = []
    for i, r in enumerate(results, 1):
        title = r.get('title', '无标题')
        content = r.get('content', '无内容')
        snippets.append(f"{i}. {title}\n{content}")
    return "\n\n".join(snippets) if snippets else "未找到相关资料"

if __name__ == '__main__':
    print(web_search("铁锈战争"))
