import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import load_profile
from core.ark_client import ArkClient

def test_chat():
    load_profile()
    
    # 按照优先级自动寻找可用的接入点，优先消耗极速版和轻量版的免费 Token
    endpoint_id = (
        os.getenv("SEED_2_0_MINI_ENDPOINT_ID") or
        os.getenv("DOUBAO_1_6_FLASH_ENDPOINT_ID") or
        os.getenv("SEED_2_0_LITE_ENDPOINT_ID") or 
        os.getenv("DOUBAO_1_5_LITE_ENDPOINT_ID")
    )
    
    print(f"\n--- 豆包大模型文本对话测试 ---")
    if not endpoint_id:
        print("跳过: 请在 .env 中配置任意一个 ENDPOINT_ID (如 DOUBAO_MINI_ENDPOINT_ID)")
        return

    print(f"正在使用接入点: {endpoint_id}")
    client = ArkClient()
    # 在 Prompt 中显式要求不使用 Markdown 格式
    prompt = "你好，请简单介绍一下火山引擎 Seed 2.0 大模型。请注意：直接输出纯文本内容，不要使用 Markdown 语法（如星号、加粗等）。"
    response = client.chat(endpoint_id, prompt)
    print(f"AI 回复:\n{response}")

if __name__ == "__main__":
    test_chat()
