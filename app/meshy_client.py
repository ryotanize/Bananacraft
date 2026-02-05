import os
import requests
import base64
import time
import json

class MeshyClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.image_to_3d_url = "https://api.meshy.ai/openapi/v1/image-to-3d"
        self.text_to_3d_url = "https://api.meshy.ai/openapi/v2/text-to-3d"
        # Keep legacy base_url for backward compatibility
        self.base_url = self.image_to_3d_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def _image_to_data_uri(self, image_path: str) -> str:
        """Converts local image file to Data URI."""
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            ext = os.path.splitext(image_path)[1].lower().replace('.', '')
            if ext == 'jpg': ext = 'jpeg'
            return f"data:image/{ext};base64,{encoded_string}"

    def generate_model(self, image_path: str) -> str:
        """
        Starts an Image-to-3D task.
        Returns the Task ID.
        """
        print(f"Uploading image to Meshy: {image_path}...")
        data_uri = self._image_to_data_uri(image_path)
        
        payload = {
            "image_url": data_uri,
            "enable_pbr": True,
            "should_remesh": True, # Optimized topology
            "should_texture": True,
            "ai_model": "latest",
            "topology": "quad", # Better for voxelization logic potentially
            "target_polycount": 30000 
        }

        try:
            response = requests.post(self.image_to_3d_url, headers=self.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            task_id = result.get("result")
            print(f"Task created successfully. ID: {task_id}")
            return task_id
        except requests.exceptions.HTTPError as e:
            print(f"Meshy API Error: {e.response.text}")
            return None
        except Exception as e:
            print(f"Unexpected Error: {e}")
            return None

    # ==================== Text-to-3D Methods ====================
    
    def generate_text_to_3d_preview(self, prompt: str, ai_model: str = "meshy-5") -> str:
        """
        Starts a Text-to-3D Preview task.
        
        Args:
            prompt: Description of the 3D model (max 600 chars)
            ai_model: "meshy-5", "meshy-6", or "latest" (default: meshy-5 for lower cost)
        
        Returns the Task ID.
        """
        print(f"Starting Text-to-3D Preview task...")
        print(f"Prompt: {prompt[:100]}...")
        
        payload = {
            "mode": "preview",
            "prompt": prompt[:600],  # Ensure max 600 chars
            "ai_model": ai_model,
            "topology": "quad",  # Better for voxelization
            "target_polycount": 10000,  # Lower poly for voxel style
            "should_remesh": True
        }

        try:
            response = requests.post(self.text_to_3d_url, headers=self.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            task_id = result.get("result")
            print(f"Text-to-3D Preview task created. ID: {task_id}")
            return task_id
        except requests.exceptions.HTTPError as e:
            print(f"Meshy API Error: {e.response.text}")
            return None
        except Exception as e:
            print(f"Unexpected Error: {e}")
            return None

    def generate_text_to_3d_refine(self, preview_task_id: str) -> str:
        """
        Starts a Text-to-3D Refine task based on a completed preview.
        
        Args:
            preview_task_id: The task ID of a completed preview task
        
        Returns the new Refine Task ID.
        """
        print(f"Starting Text-to-3D Refine task for preview: {preview_task_id}...")
        
        payload = {
            "mode": "refine",
            "preview_task_id": preview_task_id,
            "enable_pbr": True
        }

        try:
            response = requests.post(self.text_to_3d_url, headers=self.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            task_id = result.get("result")
            print(f"Text-to-3D Refine task created. ID: {task_id}")
            return task_id
        except requests.exceptions.HTTPError as e:
            print(f"Meshy API Error: {e.response.text}")
            return None
        except Exception as e:
            print(f"Unexpected Error: {e}")
            return None

    def get_text_to_3d_task(self, task_id: str):
        """
        Retrieves Text-to-3D task status.
        """
        url = f"{self.text_to_3d_url}/{task_id}"
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Polling Warning (Retrying): {e}")
            return None

    def wait_for_text_to_3d_completion(self, task_id: str, poll_interval: int = 10):
        """
        Polls until the Text-to-3D task is SUCCEEDED or FAILED.
        Returns the full task object.
        """
        print(f"Waiting for Text-to-3D task {task_id} to complete...")
        while True:
            task = self.get_text_to_3d_task(task_id)
            if not task:
                print("Failed to get task status, retrying...")
                time.sleep(poll_interval)
                continue
            
            status = task.get("status")
            progress = task.get("progress", 0)
            
            if status == "SUCCEEDED":
                print(f"Task Completed! 100%")
                return task
            elif status == "FAILED":
                print(f"Task Failed: {task.get('task_error')}")
                return task
            elif status in ["IN_PROGRESS", "PENDING"]:
                print(f"Status: {status} (Progress: {progress}%)")
                time.sleep(poll_interval)
            else:
                print(f"Unknown status: {status}")
                return task

    # ==================== Legacy Image-to-3D Methods ====================

    def get_task(self, task_id: str):
        """
        Retrieves Image-to-3D task status.
        """
        url = f"{self.image_to_3d_url}/{task_id}"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Polling Warning (Retrying): {e}")
            return None

    def wait_for_completion(self, task_id: str, poll_interval: int = 5):
        """
        Polls until the Image-to-3D task is SUCCEEDED or FAILED.
        Returns the full task object.
        """
        print(f"Waiting for task {task_id} to complete...")
        while True:
            task = self.get_task(task_id)
            if not task:
                print("Failed to get task status, retrying...")
                time.sleep(poll_interval)
                continue
            
            status = task.get("status")
            progress = task.get("progress", 0)
            
            if status == "SUCCEEDED":
                print(f"Task Completed! 100%")
                return task
            elif status == "FAILED":
                print(f"Task Failed: {task.get('task_error')}")
                return task
            elif status in ["IN_PROGRESS", "PENDING"]:
                print(f"Status: {status} (Progress: {progress}%)")
                time.sleep(poll_interval)
            else:
                print(f"Unknown status: {status}")
                return task

