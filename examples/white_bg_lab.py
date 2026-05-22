import os
import sys
import requests
import cv2
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import load_profile
from core.ark_client import ArkClient
from core.cv_client import CvClient
from datetime import datetime
from PIL import Image


def download_image(url, save_path):
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(resp.content)
        return True
    except Exception as e:
        print(f"  下载失败: {e}")
        return False


def step1_generate_white_bg(cv, model_id, prompt, image_path):
    print(f"\n{'='*60}")
    print("步骤1: SeaDream 5.0 生成白底图（不含Logo文字）")
    print(f"{'='*60}")

    start = datetime.now()
    result_url = None
    mode = None

    try:
        task = cv.submit_img2img_task(model_id, prompt, image_path)
        task_id = task.get("id")

        if task_id:
            mode = "异步"
            print(f"异步模式提交成功，任务 ID: {task_id}，等待结果...")
            result_url = cv.wait_for_result(task_id)
        else:
            mode = "同步"
            print("异步模式不支持，尝试同步直接生成...")
            res = cv.generate_img2img_direct(model_id, prompt, image_path)
            if "data" in res and len(res["data"]) > 0:
                result_url = res["data"][0].get("url")
            else:
                error_msg = res.get("error", {}).get("message", str(res))
                print(f"同步模式失败: {error_msg}")
    except Exception as e:
        print(f"执行出错: {e}")

    duration = (datetime.now() - start).total_seconds()
    print(f"生成耗时: {duration:.2f}s, 模式: {mode}")

    return result_url


def step2_detect_logos(ark, mini_id, image_path):
    print(f"\n{'='*60}")
    print("步骤2: Mini 多模态识别原图Logo位置")
    print(f"{'='*60}")

    abs_path = os.path.abspath(image_path)

    prompt = (
        "请分析这张裤子图片中所有品牌Logo的位置。"
        "我需要你返回JSON格式的结果，每个Logo包含："
        "1. name: Logo名称"
        "2. x: 左上角x坐标（像素）"
        "3. y: 左上角y坐标（像素）"
        "4. width: Logo宽度（像素）"
        "5. height: Logo高度（像素）"
        "6. description: Logo描述"
        "请只返回JSON数组，不要其他内容。格式示例："
        '[{"name":"BIEMLFDLKK","x":100,"y":200,"width":300,"height":50,"description":"正面主体刺绣Logo"}]'
    )

    try:
        result = ark.multimodal_chat(mini_id, prompt, abs_path)
        print(f"Mini返回: {result}")

        import json
        json_str = result.strip()
        if "```" in json_str:
            json_str = json_str.split("```")[1]
            if json_str.startswith("json"):
                json_str = json_str[4:]
            json_str = json_str.strip()

        logos = json.loads(json_str)
        for logo in logos:
            print(f"  检测到Logo: {logo['name']} @ ({logo['x']},{logo['y']}) {logo['width']}x{logo['height']}")
        return logos
    except Exception as e:
        print(f"Logo检测失败: {e}")
        print("将使用默认Logo位置")
        return None


def step3_paste_logos(original_path, generated_path, logos, output_path):
    print(f"\n{'='*60}")
    print("步骤3: 从原图裁切Logo贴回生成图")
    print(f"{'='*60}")

    orig = cv2.imread(original_path)
    gen = cv2.imread(generated_path)

    if orig is None:
        print(f"无法读取原图: {original_path}")
        return False
    if gen is None:
        print(f"无法读取生成图: {generated_path}")
        return False

    orig_h, orig_w = orig.shape[:2]
    gen_h, gen_w = gen.shape[:2]
    scale_x = gen_w / orig_w
    scale_y = gen_h / orig_h
    print(f"原图尺寸: {orig_w}x{orig_h}, 生成图尺寸: {gen_w}x{gen_h}, 缩放比: {scale_x:.2f}x{scale_y:.2f}")

    if logos:
        for logo in logos:
            x = int(logo["x"] * scale_x)
            y = int(logo["y"] * scale_y)
            w = int(logo["width"] * scale_x)
            h = int(logo["height"] * scale_y)

            x = max(0, x)
            y = max(0, y)
            w = min(w, gen_w - x)
            h = min(h, gen_h - y)

            if w <= 0 or h <= 0:
                print(f"  Logo {logo['name']} 区域无效，跳过")
                continue

            margin = int(max(w, h) * 0.15)
            src_x = max(0, int(logo["x"]) - margin)
            src_y = max(0, int(logo["y"]) - margin)
            src_w = min(int(logo["width"]) + margin * 2, orig_w - src_x)
            src_h = min(int(logo["height"]) + margin * 2, orig_h - src_y)

            logo_crop = orig[src_y:src_y+src_h, src_x:src_x+src_w]

            dst_x = int(src_x * scale_x)
            dst_y = int(src_y * scale_y)
            dst_w = int(src_w * scale_x)
            dst_h = int(src_h * scale_y)

            dst_w = min(dst_w, gen_w - dst_x)
            dst_h = min(dst_h, gen_h - dst_y)

            if dst_w <= 0 or dst_h <= 0:
                continue

            logo_resized = cv2.resize(logo_crop, (dst_w, dst_h))

            mask = np.zeros(logo_resized.shape[:2], dtype=np.float32)
            feather = max(5, int(min(dst_w, dst_h) * 0.1))
            mask[feather:-feather, feather:-feather] = 1.0
            mask = cv2.GaussianBlur(mask, (0, 0), feather / 2)
            mask = mask[:, :, np.newaxis]

            roi = gen[dst_y:dst_y+dst_h, dst_x:dst_x+dst_w]
            blended = (logo_resized * mask + roi * (1 - mask)).astype(np.uint8)
            gen[dst_y:dst_y+dst_h, dst_x:dst_x+dst_w] = blended

            print(f"  已贴回Logo: {logo['name']} -> ({dst_x},{dst_y}) {dst_w}x{dst_h}")
    else:
        print("  未检测到Logo位置，跳过贴回步骤")

    cv2.imwrite(output_path, gen)
    print(f"  Logo贴回完成: {output_path}")
    return True


def step4_color_correction(original_path, generated_path, output_path):
    print(f"\n{'='*60}")
    print("步骤4: 色彩校正（LAB直方图匹配）")
    print(f"{'='*60}")

    orig = cv2.imread(original_path)
    gen = cv2.imread(generated_path)

    if orig is None or gen is None:
        print("无法读取图片，跳过色彩校正")
        return False

    lower_white = np.array([0, 0, 200], dtype=np.uint8)
    upper_white = np.array([180, 30, 255], dtype=np.uint8)
    hsv = cv2.cvtColor(gen, cv2.COLOR_BGR2HSV)
    white_mask = cv2.inRange(hsv, lower_white, upper_white)
    fabric_mask = cv2.bitwise_not(white_mask)

    fabric_pixels = cv2.findNonZero(fabric_mask)
    if fabric_pixels is None:
        print("未检测到面料区域，跳过色彩校正")
        return False

    x, y, w, h = cv2.boundingRect(fabric_pixels)
    padding = 5
    x = max(0, x - padding)
    y = max(0, y - padding)
    w = min(w + padding * 2, gen.shape[1] - x)
    h = min(h + padding * 2, gen.shape[0] - y)

    orig_roi = orig[y:y+h, x:x+w]
    gen_roi = gen[y:y+h, x:x+w]
    mask_roi = fabric_mask[y:y+h, x:x+w]

    orig_lab = cv2.cvtColor(orig_roi, cv2.COLOR_BGR2LAB)
    gen_lab = cv2.cvtColor(gen_roi, cv2.COLOR_BGR2LAB)

    for i in range(3):
        orig_channel = orig_lab[:, :, i][mask_roi > 0]
        gen_channel = gen_lab[:, :, i][mask_roi > 0]

        if len(orig_channel) == 0 or len(gen_channel) == 0:
            continue

        orig_mean, orig_std = orig_channel.mean(), orig_channel.std()
        gen_mean, gen_std = gen_channel.mean(), gen_channel.std()

        if gen_std < 1:
            gen_std = 1

        gen_lab[:, :, i] = np.where(
            mask_roi > 0,
            np.clip((gen_lab[:, :, i].astype(np.float32) - gen_mean) * (orig_std / gen_std) + orig_mean, 0, 255),
            gen_lab[:, :, i]
        ).astype(np.uint8)

    corrected_roi = cv2.cvtColor(gen_lab, cv2.COLOR_LAB2BGR)
    result = gen.copy()
    result[y:y+h, x:x+w] = np.where(mask_roi[:, :, np.newaxis] > 0, corrected_roi, gen_roi)

    cv2.imwrite(output_path, result)
    print(f"  色彩校正完成: {output_path}")
    return True


def run_white_bg():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(BASE_DIR, ".env"))

    overall_start = datetime.now()
    print(f"任务开始时间: {overall_start.strftime('%Y-%m-%d %H:%M:%S')}")

    image_path = "/Users/bytedance/Downloads/微信图片_20260521160214.png"
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图片不存在: {image_path}")

    prompt_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "white_bg_prompt.txt")
    if not os.path.exists(prompt_file):
        raise FileNotFoundError(f"提示词文件不存在: {prompt_file}")

    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt = f.read().strip()

    mini_id = os.getenv("SEED_2_0_MINI_ENDPOINT_ID")
    dream5_id = os.getenv("SEADREAM_5_0_ENDPOINT_ID")

    if not mini_id:
        raise ValueError("请在 .env 中配置 SEED_2_0_MINI_ENDPOINT_ID")
    if not dream5_id:
        raise ValueError("请在 .env 中配置 SEADREAM_5_0_ENDPOINT_ID")

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    cv = CvClient()
    ark = ArkClient()

    result_url = step1_generate_white_bg(cv, dream5_id, prompt, image_path)
    if not result_url:
        print("❌ 白底图生成失败，终止流程")
        return

    gen_raw_path = os.path.join(output_dir, f"step1_raw_{timestamp}.png")
    if not download_image(result_url, gen_raw_path):
        print("❌ 白底图下载失败，终止流程")
        return
    print(f"✅ 白底图已下载: {gen_raw_path}")

    logos = step2_detect_logos(ark, mini_id, image_path)

    gen_logo_path = os.path.join(output_dir, f"step2_logo_pasted_{timestamp}.png")
    if logos:
        step3_paste_logos(image_path, gen_raw_path, logos, gen_logo_path)
    else:
        gen_logo_path = gen_raw_path
        print("跳过Logo贴回步骤")

    gen_final_path = os.path.join(output_dir, f"final_white_bg_{timestamp}.png")
    step4_color_correction(image_path, gen_logo_path, gen_final_path)

    print(f"\n{'='*60}")
    print("处理完成！生成文件：")
    print(f"  步骤1 - 原始白底图: {gen_raw_path}")
    if logos:
        print(f"  步骤2 - Logo贴回图: {gen_logo_path}")
    print(f"  步骤3 - 最终校正图: {gen_final_path}")
    print(f"{'='*60}")

    overall_end = datetime.now()
    print(f"总耗时: {(overall_end - overall_start).total_seconds():.2f} 秒")


if __name__ == "__main__":
    run_white_bg()
