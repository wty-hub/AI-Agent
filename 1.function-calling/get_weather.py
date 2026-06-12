# get_weather.py

from sys import stderr
import requests
from env import env

def get_weather(city: str):
    # 每个账号专属的 url
    api_host = env["HF_API_HOST"]
    # 申请的 API key
    api_key = env["HF_API_KEY"]

    if api_host.startswith("your-api-host"):
        msg = "请先在 api.properities 中填写 HF_API_HOST（控制台 → 设置 → API Host）"
        print(msg, file=stderr)
        return msg

    headers = {"X-QW-Api-Key": api_key}
    # 获取地理位置的 url
    geo_url = f"https://{api_host}/geo/v2/city/lookup"

    try:
        geo_res = requests.get(
            geo_url,
            params={"location": city, "range": "cn", "lang": "zh"},
            headers=headers,
            timeout=5,
        )

        if geo_res.status_code != 200:
            print(
                f"获取城市ID失败，HTTP {geo_res.status_code}: {geo_res.text[:200]}",
                file=stderr,
            )
            return f"获取城市ID失败，HTTP {geo_res.status_code}"

        geo_data = geo_res.json()

        # print("geo_data:", geo_data)
        city_id = geo_data["location"][0]["id"]
        standard_name = geo_data["location"][0]["name"]
        # print(f"城市: {standard_name}, ID: {city_id}")

        # 获取城市的实时天气
        weather_url = f"https://{api_host}/v7/weather/now"
        weather_params = {"location": city_id, "lang": "zh", "unit": "m"}
        weather_res = requests.get(
            weather_url,
            params=weather_params,
            headers=headers,
            timeout=5,
        )

        if weather_res.status_code != 200:
            print(
                f"获取实时天气失败，HTTP {weather_res.status_code}: {weather_res.text[:200]}",
                file=stderr,
            )
            return f"获取实时天气失败，HTTP {weather_res.status_code}"

        weather_data = weather_res.json()
        now = weather_data.get("now", {})
        text = now.get("text", "未知")
        temp = now.get("temp", "未知")
        feelsLike = now.get("feelsLike", "未知")
        windDir = now.get("windDir", "未知")
        windScale = now.get("windScale", "未知")
        humidity = now.get("humidity", "未知")

        # 获取当天最高/最低温度
        daily_url = f"https://{api_host}/v7/weather/3d"
        daily_res = requests.get(
            daily_url,
            params={"location": city_id, "lang": "zh", "unit": "m"},
            headers=headers,
            timeout=5,
        )

        temp_max = temp_min = "未知"
        if daily_res.status_code == 200:
            daily_data = daily_res.json()
            if daily_data.get("code") == "200" and daily_data.get("daily"):
                today = daily_data["daily"][0]
                temp_max = today.get("tempMax", "未知")
                temp_min = today.get("tempMin", "未知")

        weather_msg = (
            f"{standard_name}当前天气：{text}，温度{temp}°C（今日{temp_min}~{temp_max}°C），"
            f"体感温度{feelsLike}°C，风向{windDir}，风力{windScale}级，湿度{humidity}%"
        )

        # print(weather_msg)
        return weather_msg

    except Exception as e:
        print(f"异常：{e}", file=stderr)
        return f"异常：{e}"


if __name__ == "__main__":
    print("西安的天气：", get_weather("西安", env))
