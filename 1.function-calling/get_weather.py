# get_weather.py

import requests
import os

# 这里我用 .env 文件保存了 API_KEY 等敏感变量
def read_env_file(env_path="../.env"):
    env_vars = {}
    if not os.path.exists(env_path):
        raise FileNotFoundError(f"Could not find the .env file at {env_path}")
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()
    return env_vars


def get_weather()


if __name__ == '__main__':
    env = read_env_file()