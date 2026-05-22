import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import load_profile
from core.ark_client import ArkClient
from core.cv_client import CvClient

def run_fashion_change():
    load_profile()
    
    # 1. 配置接入点 (按优先级寻找可用的 SeaDREAM 版本)
    mini_id = os.getenv("SEED_2_0_MINI_ENDPOINT_ID")
    dream_id = (
        os.getenv("SEADREAM_5_0_ENDPOINT_ID") or 
        os.getenv("SEADREAM_4_5_ENDPOINT_ID") or 
        os.getenv("SEADREAM_4_0_ENDPOINT_ID")
    )
    
    if not mini_id or not dream_id:
        print("错误: 请在 .env 中配置 SEED_2_0_MINI_ENDPOINT_ID 以及任意一个 SEADREAM 接入点")
        return

    print("\n--- 场景：电商模特换装实验 ---")
    
    # 2. 第一步：利用 Seed 2.0 Mini 生成专业的绘图 Prompt
    # 这一步是免费的（消耗赠送 Token），能极大提高换装的成功率
    print("Step 1: 正在调用 Seed 2.0 Mini 优化换装提示词...")
    ark = ArkClient()
    user_request = "我想把这个模特的白色 T 恤换成一件蓝色的真丝衬衫，保持背景和模特姿势不变。"
    
    system_instruction = (
        "你是一个专业的电商摄影提示词专家。请根据用户的需求，完成以下任务：\n"
        "1. 生成一段用于 SeaDREAM 的英文提示词（Prompt）。\n"
        "2. 提供该提示词的中文翻译。\n"
        "输出格式要求：\n"
        "中文翻译：[此处写中文]\n"
        "EN_PROMPT: [此处只写英文提示词，不要有星号]"
    )
    
    ai_response = ark.chat(mini_id, f"{system_instruction}\n用户需求：{user_request}")
    
    # 解析中英文
    import re
    chinese_part = "未提取到翻译"
    refined_prompt = ai_response # 兜底
    
    if "中文翻译：" in ai_response and "EN_PROMPT:" in ai_response:
        chinese_part = re.search(r"中文翻译：(.*?)EN_PROMPT:", ai_response, re.S).group(1).strip()
        refined_prompt = re.search(r"EN_PROMPT:(.*)", ai_response, re.S).group(1).strip()
    
    print(f"提示词含义: {chinese_part}")
    print(f"发送给 AI 的英文提示词: {refined_prompt}")

    # 3. 第二步：调用 SeaDREAM 4.5 Lite 执行生成
    print("\nStep 2: 准备调用 SeaDREAM 4.5 Lite 进行图像生成...")
    print("⚠️ 提示：这将消耗 1 张免费额度（或约 ¥0.1 余额）。")
    
    confirm = input("确认执行生成任务? (y/N): ")
    if confirm.lower() == 'y':
        cv = CvClient()
        try:
            # 尝试 1: 异步任务模式 (5.0 推荐)
            task = cv.submit_image_task(dream_id, refined_prompt)
            task_id = task.get("id")
            
            if task_id:
                print(f"任务已提交 (异步)，ID: {task_id}。正在轮询结果...")
                image_url = cv.wait_for_result(task_id)
                print(f"\n✅ 换装成功！图片地址:\n{image_url}")
            else:
                # 尝试 2: 同步直接生成模式 (兼容 4.5)
                print("异步模式不支持该模型，正在尝试同步直接生成模式...")
                res = cv.generate_image_direct(dream_id, refined_prompt)
                
                # 解析同步结果
                if "data" in res and len(res["data"]) > 0:
                    image_url = res["data"][0].get("url")
                    print(f"\n✅ 换装成功 (同步模式)！图片地址:\n{image_url}")
                else:
                    error_msg = res.get("error", {}).get("message", str(res))
                    print(f"同步模式也失败了: {error_msg}")
                    
        except Exception as e:
            print(f"执行出错: {e}")

if __name__ == "__main__":
    run_fashion_change()
