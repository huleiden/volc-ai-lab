import os
import sys
import time
from dotenv import load_dotenv

# 确保可以导入 core 模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ark_client import ArkClient
from core.cv_client import CvClient

def lab_multimodal():
    load_dotenv()
    
    # 1. 多模态分析测试 (优先使用 Seed 2.0 Mini 或 1.5 Vision)
    vision_endpoint = (
        os.getenv("SEED_2_0_MINI_ENDPOINT_ID") or
        os.getenv("DOUBAO_1_5_VISION_ENDPOINT_ID") or 
        os.getenv("SEED_2_0_LITE_ENDPOINT_ID")
    )
    
    if vision_endpoint:
        print(f"\n--- 实验 1: 多模态分析 (接入点: {vision_endpoint}) ---")
        ark = ArkClient()
        prompt = "描述这张图片中的主要内容和艺术风格。"
        image_url = "https://ark-project.tos-cn-beijing.volces.com/public/image-demo.jpg"
        try:
            res = ark.multimodal_chat(vision_endpoint, prompt, image_url)
            print(f"分析结果:\n{res}")
        except Exception as e:
            print(f"多模态分析失败: {e}")

    # 2. SeaDance 视频生成测试 (优先 2.0)
    video_endpoint = os.getenv("SEADANCE_2_0_ENDPOINT_ID") or os.getenv("SEADANCE_1_0_ENDPOINT_ID")
    if video_endpoint:
        print(f"\n⚠️ 风险提示: 视频生成 (接入点: {video_endpoint}) 费用较高。")
        confirm = input(f"是否继续执行视频生成实验? (y/N): ")
        if confirm.lower() == 'y':
            print(f"\n--- 实验 2: SeaDance 视频生成 ---")
            cv = CvClient()
            prompt = "一只可爱的小猫在草地上追逐蝴蝶，电影感，高质量。"
            try:
                task = cv.submit_video_task(video_endpoint, prompt)
                task_id = task.get("id")
                if task_id:
                    print(f"任务提交成功，ID: {task_id}")
                    video_url = cv.wait_for_result(task_id)
                    print(f"视频生成成功! 地址: {video_url}")
                else:
                    print(f"任务提交失败: {task}")
            except Exception as e:
                print(f"视频生成实验出错: {e}")

    # 3. SeaDREAM 图像生成测试 (优先 5.0)
    dream_endpoint = os.getenv("SEADREAM_5_0_ENDPOINT_ID") or os.getenv("SEADREAM_4_0_ENDPOINT_ID")
    if dream_endpoint:
        print(f"\n⚠️ 风险提示: 图像生成 (接入点: {dream_endpoint}) 存在计费。")
        confirm = input(f"是否继续执行图像生成实验? (y/N): ")
        if confirm.lower() == 'y':
            print(f"\n--- 实验 3: SeaDREAM 图像生成 ---")
            cv = CvClient()
            prompt = "一个极简主义风格的未来城市，夕阳西下，赛博朋克风格。"
            try:
                task = cv.submit_image_task(dream_endpoint, prompt)
                task_id = task.get("id")
                if task_id:
                    print(f"任务提交成功，ID: {task_id}")
                    image_url = cv.wait_for_result(task_id)
                    print(f"图像生成成功! 地址: {image_url}")
                else:
                    print(f"任务提交失败: {task}")
            except Exception as e:
                print(f"图像生成实验出错: {e}")

if __name__ == "__main__":
    lab_multimodal()
