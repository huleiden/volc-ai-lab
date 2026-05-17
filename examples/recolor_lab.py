import os
import sys
from dotenv import load_dotenv

# 确保可以导入 core 模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ark_client import ArkClient
from core.cv_client import CvClient
from datetime import datetime

def run_recolor():
    load_dotenv()
    
    start_time = datetime.now()
    print(f"任务开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 请填入你刚才生成的模特图片 URL
    ORIGINAL_IMAGE_URL = os.getenv("ORIGINAL_IMAGE_URL")
    if not ORIGINAL_IMAGE_URL:
        raise ValueError("请在 .env 中配置 ORIGINAL_IMAGE_URL")
    
    mini_id = os.getenv("SEED_2_0_MINI_ENDPOINT_ID")
    dream_id = os.getenv("SEADREAM_5_0_ENDPOINT_ID") or os.getenv("SEADREAM_4_5_ENDPOINT_ID")
    ark = ArkClient()
    new_color = "燕麦色 (Oatmeal)"
    print(f"\n--- 场景：保持版型，仅更换颜色：{new_color}")
    
    # 1. 调用 Mini 生成“仅改颜色”的 Prompt
    user_request = f"保持图片中模特的姿势、衬衫的版型和褶皱完全不变，仅将蓝色衬衫改为{new_color}。"
    
    system_instruction = (
        "你是一个图像重绘专家。请生成一段英文 Prompt，强调‘保持原样’和‘仅修改颜色’。"
        "必须包含词汇：keep the same style and wrinkles, change color only to deep red, maintaining original pose."
        "输出格式：EN_PROMPT: [仅英文内容]"
    )
    
    ai_res = ark.chat(mini_id, f"{system_instruction}\n需求：{user_request}")
    prompt = ai_res.split("EN_PROMPT:")[-1].strip()
    print(f"生成的重绘提示词: {prompt}")

    # 2. 调用 CvClient 执行图生图
    cv = CvClient()
    print("\n正在提交图生图任务...")
    try:
        # 尝试 1: 异步模式
        task = cv.submit_img2img_task(dream_id, prompt, ORIGINAL_IMAGE_URL)
        task_id = task.get("id")
        
        if task_id:
            print(f"任务提交成功 (异步)，ID: {task_id}。正在等待结果...")
            new_image_url = cv.wait_for_result(task_id)
            print(f"\n✅ 颜色更换成功！新图地址:\n{new_image_url}")
        else:
            # 尝试 2: 同步直连模式 (针对 4.5 版本)
            print("异步模式不支持该模型，正在尝试同步直接生成模式...")
            res = cv.generate_img2img_direct(dream_id, prompt, ORIGINAL_IMAGE_URL)
            
            if "data" in res and len(res["data"]) > 0:
                new_image_url = res["data"][0].get("url")
                print(f"\n✅ 颜色更换成功 (同步模式)！新图地址:\n{new_image_url}")
            else:
                error_msg = res.get("error", {}).get("message", str(res))
                print(f"同步模式也失败了: {error_msg}")
                
    except Exception as e:
        print(f"执行出错: {e}")
    finally:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"\n--------------------------------")
        print(f"性能统计报告:")
        print(f"开始时间: {start_time.strftime('%H:%M:%S')}")
        print(f"结束时间: {end_time.strftime('%H:%M:%S')}")
        print(f"总计耗时: {duration:.2f} 秒")
        print(f"--------------------------------")

if __name__ == "__main__":
    run_recolor()
