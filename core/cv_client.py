import os
import requests
import time
from dotenv import load_dotenv

# 自动定位项目根目录下的 .env 文件
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

class CvClient:
    """处理 SeaDREAM (图像) 和 SeaDance (视频) 的 CV 类模型"""
    
    def __init__(self):
        api_key = os.getenv("ARK_API_KEY")
        if not api_key:
            raise ValueError(f"请在 {os.path.join(BASE_DIR, '.env')} 文件中配置 ARK_API_KEY")
        
        # 移除可能的引号
        self.api_key = api_key.strip('"').strip("'")
        self.base_url = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def submit_video_task(self, model_id, prompt, image_url=None):
        """提交 SeaDance 2.0 视频生成任务"""
        payload = {
            "model": model_id,
            "content": [
                {"type": "text", "text": prompt}
            ],
            "parameters": {
                "duration_seconds": 5,
                "fps": 24,
                "resolution": "1080p"
            }
        }
        
        if image_url:
            payload["content"].append({
                "type": "image_url",
                "image_url": {"url": image_url},
                "role": "first_frame"
            })

        response = requests.post(self.base_url, headers=self.headers, json=payload)
        return response.json()

    def submit_image_task(self, model_id, prompt):
        """提交 SeaDREAM 5.0 图像生成任务 (异步)"""
        payload = {
            "model": model_id,
            "content": [
                {"type": "text", "text": prompt}
            ]
        }
        response = requests.post(self.base_url, headers=self.headers, json=payload)
        return response.json()

    def _prepare_image(self, image_path_or_url):
        """处理图片：如果是本地路径则转为 Base64，如果是 URL 则直接返回"""
        if image_path_or_url.startswith(('http://', 'https://')):
            return image_path_or_url
        
        # 处理本地文件
        import base64
        import mimetypes
        try:
            with open(image_path_or_url, "rb") as image_file:
                base64_data = base64.b64encode(image_file.read()).decode('utf-8')
                mime_type, _ = mimetypes.guess_type(image_path_or_url)
                return f"data:{mime_type};base64,{base64_data}"
        except Exception as e:
            raise Exception(f"读取本地图片失败: {e}")

    def submit_img2img_task(self, model_id, prompt, image_url_or_path):
        """提交图生图任务 (异步方式，推荐 5.0 使用)"""
        final_image = self._prepare_image(image_url_or_path)
        payload = {
            "model": model_id,
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": final_image}, "role": "reference"}
            ],
            "parameters": {
                "denoising_strength": 0.35 
            }
        }
        response = requests.post(self.base_url, headers=self.headers, json=payload)
        return response.json()

    def generate_img2img_direct(self, model_id, prompt, image_url_or_path):
        """同步图生图生成 (兼容 4.5 版本)"""
        final_image = self._prepare_image(image_url_or_path)
        # 同步接口地址
        direct_url = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
        payload = {
            "model": model_id,
            "prompt": prompt,
            "image": final_image, # 同步接口通常直接传 image 字段
            "n": 1,
            "size": "1440x2560" # 保持 4.5 要求的超高清
        }
        response = requests.post(direct_url, headers=self.headers, json=payload)
        return response.json()

    def query_task(self, task_id):
        """轮询任务状态"""
        url = f"{self.base_url}/{task_id}"
        response = requests.get(url, headers=self.headers)
        return response.json()

    def wait_for_result(self, task_id, timeout=300):
        """循环等待结果"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            result = self.query_task(task_id)
            status = result.get("status")
            print(f"任务状态: {status}")
            
            if status == "succeeded":
                return result.get("output", {}).get("video_url")
            elif status == "failed":
                raise Exception(f"任务失败: {result.get('error')}")
            
            time.sleep(10)
        raise Exception("任务超时")
