import os
from dotenv import load_dotenv
from volcenginesdkarkruntime import Ark

# 自动定位项目根目录下的 .env 文件
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

class ArkClient:
    def __init__(self):
        api_key = os.getenv("ARK_API_KEY")
        if not api_key:
            raise ValueError(f"请在 {os.path.join(BASE_DIR, '.env')} 文件中配置 ARK_API_KEY")
        # 移除可能的引号
        api_key = api_key.strip('"').strip("'")
        self.client = Ark(api_key=api_key)

    def chat(self, endpoint_id, prompt):
        """Seed 2.0 基础文本对话"""
        if not endpoint_id:
            return "错误: 请提供 SEED_ENDPOINT_ID"
            
        completion = self.client.chat.completions.create(
            model=endpoint_id,
            messages=[
                {"role": "system", "content": "你是一个专业的AI助手。请以纯文本格式回复，不要包含Markdown语法。"},
                {"role": "user", "content": prompt},
            ],
        )
        content = completion.choices[0].message.content
        # 强制移除所有的 ** 加粗符号
        return content.replace("**", "")

    def multimodal_chat(self, endpoint_id, prompt, image_url):
        """Seed 2.0 多模态分析 (图片 + 文本)"""
        if not endpoint_id:
            return "错误: 请提供 SEED_ENDPOINT_ID"

        completion = self.client.chat.completions.create(
            model=endpoint_id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url}
                        },
                    ],
                }
            ],
        )
        return completion.choices[0].message.content
