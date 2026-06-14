import os


def read_env_file(env_path="api.properities") -> dict:
    env_vars = {}
    if not os.path.exists(env_path):
        raise FileNotFoundError(f"Could not find the config file at {env_path}")
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()
    return env_vars


env = read_env_file()