import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VALID_PROFILES = ["personal", "enterprise", "client"]
DEFAULT_PROFILE = "personal"


def get_profile():
    profile = os.getenv("PROFILE", DEFAULT_PROFILE)
    if profile not in VALID_PROFILES:
        raise ValueError(f"无效的 PROFILE: {profile}，可选值: {VALID_PROFILES}")
    return profile


def load_profile():
    profile = get_profile()
    env_file = os.path.join(BASE_DIR, f".env.{profile}")

    if not os.path.exists(env_file):
        raise FileNotFoundError(
            f"配置文件不存在: {env_file}\n"
            f"请创建 .env.{profile} 文件，可参考 .env.personal 模板"
        )

    load_dotenv(env_file, override=True)
    print(f"[配置] 已加载 Profile: {profile} ({env_file})")
    return profile
