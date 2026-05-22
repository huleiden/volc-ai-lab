import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ark_client import ArkClient
from core.cv_client import CvClient
from datetime import datetime


def run_single_model(cv, model_id, model_name, prompt, image_url):
    start = datetime.now()
    print(f"\n{'='*50}")
    print(f"正在测试模型: {model_name} (ID: {model_id})")
    print(f"开始时间: {start.strftime('%H:%M:%S')}")

    result_url = None
    mode = None
    submit_duration = 0.0
    generate_duration = 0.0

    try:
        submit_start = datetime.now()
        task = cv.submit_img2img_task(model_id, prompt, image_url)
        task_id = task.get("id")
        submit_duration = (datetime.now() - submit_start).total_seconds()

        if task_id:
            mode = "异步"
            print(f"异步模式提交成功 ({submit_duration:.2f}s)，任务 ID: {task_id}，等待结果...")
            gen_start = datetime.now()
            result_url = cv.wait_for_result(task_id)
            generate_duration = (datetime.now() - gen_start).total_seconds()
        else:
            mode = "同步"
            print(f"异步模式不支持 ({submit_duration:.2f}s)，尝试同步直接生成...")
            gen_start = datetime.now()
            res = cv.generate_img2img_direct(model_id, prompt, image_url)
            generate_duration = (datetime.now() - gen_start).total_seconds()
            if "data" in res and len(res["data"]) > 0:
                result_url = res["data"][0].get("url")
            else:
                error_msg = res.get("error", {}).get("message", str(res))
                print(f"同步模式失败: {error_msg}")
    except Exception as e:
        print(f"执行出错: {e}")

    end = datetime.now()
    duration = (end - start).total_seconds()

    return {
        "model_name": model_name,
        "mode": mode,
        "duration": duration,
        "submit_duration": submit_duration,
        "generate_duration": generate_duration,
        "result_url": result_url,
        "success": result_url is not None,
        "start": start,
        "end": end,
    }


def print_comparison(results):
    print(f"\n{'='*70}")
    print("性能比对报告")
    print(f"{'='*70}")
    print(f"{'模型':<20} {'模式':<6} {'提交(s)':<10} {'生成(s)':<10} {'总计(s)':<10} {'状态':<6}")
    print(f"{'-'*20} {'-'*6} {'-'*10} {'-'*10} {'-'*10} {'-'*6}")

    for r in results:
        status = "成功" if r["success"] else "失败"
        print(f"{r['model_name']:<20} {r['mode'] or 'N/A':<6} {r['submit_duration']:<10.2f} {r['generate_duration']:<10.2f} {r['duration']:<10.2f} {status:<6}")
        if r["result_url"]:
            url = r["result_url"][:80] + "..." if len(r["result_url"]) > 80 else r["result_url"]
            print(f"  结果URL: {url}")

    successful = [r for r in results if r["success"]]
    if len(successful) >= 2:
        faster = min(successful, key=lambda x: x["generate_duration"])
        slower = max(successful, key=lambda x: x["generate_duration"])
        diff = slower["generate_duration"] - faster["generate_duration"]
        ratio = slower["generate_duration"] / faster["generate_duration"] if faster["generate_duration"] > 0 else 0
        print(f"\n⚡ {faster['model_name']} 生成速度比 {slower['model_name']} 快 {diff:.2f} 秒 ({ratio:.2f}x)")
    elif len(successful) == 1:
        print(f"\n仅 {successful[0]['model_name']} 成功完成，无法比较")

    print(f"{'='*70}")


def run_recolor():
    load_profile()
    
    overall_start = datetime.now()
    print(f"任务开始时间: {overall_start.strftime('%Y-%m-%d %H:%M:%S')}")

    ORIGINAL_IMAGE_URL = os.getenv("ORIGINAL_IMAGE_URL")
    if not ORIGINAL_IMAGE_URL:
        raise ValueError("请在 .env 中配置 ORIGINAL_IMAGE_URL")

    mini_id = os.getenv("SEED_2_0_MINI_ENDPOINT_ID")
    lite_id = os.getenv("SEADREAM_5_0_ENDPOINT_ID")
    v45_id = os.getenv("SEADREAM_4_5_ENDPOINT_ID")

    if not mini_id:
        raise ValueError("请在 .env 中配置 SEED_2_0_MINI_ENDPOINT_ID")
    if not lite_id and not v45_id:
        raise ValueError("请在 .env 中配置 SEADREAM_5_0_ENDPOINT_ID 和/或 SEADREAM_4_5_ENDPOINT_ID")

    models = []
    if lite_id:
        models.append(("SeaDream 5.0", lite_id))
    if v45_id:
        models.append(("SeaDream 4.5", v45_id))

    ark = ArkClient()
    new_color = "燕麦色 (Oatmeal)"
    print(f"\n--- 场景：保持版型，仅更换颜色：{new_color}")

    user_request = f"保持图片中模特的姿势、衬衫的版型和褶皱完全不变，仅将蓝色衬衫改为{new_color}。"

    system_instruction = (
        "你是一个图像重绘专家。请生成一段英文 Prompt，强调'保持原样'和'仅修改颜色'。"
        "必须包含词汇：keep the same style and wrinkles, change color only to deep red, maintaining original pose."
        "输出格式：EN_PROMPT: [仅英文内容]"
    )

    ai_res = ark.chat(mini_id, f"{system_instruction}\n需求：{user_request}")
    prompt = ai_res.split("EN_PROMPT:")[-1].strip()
    print(f"生成的重绘提示词: {prompt}")

    cv = CvClient()
    results = []

    for model_name, model_id in models:
        r = run_single_model(cv, model_id, model_name, prompt, ORIGINAL_IMAGE_URL)
        results.append(r)
        if r["success"]:
            print(f"✅ {model_name} 颜色更换成功！新图地址:\n{r['result_url']}")
        else:
            print(f"❌ {model_name} 颜色更换失败")

    print_comparison(results)

    overall_end = datetime.now()
    print(f"\n总耗时: {(overall_end - overall_start).total_seconds():.2f} 秒")


if __name__ == "__main__":
    run_recolor()
