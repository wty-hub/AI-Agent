import requests

def get_local_city():
    """通过IP推断本地城市"""
    res = requests.get("http://ip-api.com/json/?lang=zh-CN", timeout=5)
    if res.status_code != 200:
        raise RuntimeError(f"IP城市定位请求失败，HTTP {res.status_code}: {res.text[:200]}")
    data = res.json()
    if data.get("status") == "success" and "city" in data:
        return data["city"]
    else:
        raise RuntimeError(f"无法通过IP获取本地城市, 原始响应: {data}")

if __name__ == '__main__':
    print(f'本地城市: {get_local_city()}')