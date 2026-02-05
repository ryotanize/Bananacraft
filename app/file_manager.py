import os
import json
import base64
from datetime import datetime

class FileManager:
    def __init__(self, project_name: str, base_dir: str = "projects"):
        self.project_name = project_name
        self.project_dir = os.path.join(base_dir, project_name)
        self._ensure_project_dir()

    def _ensure_project_dir(self):
        """Creates the project directory if it doesn't exist."""
        if not os.path.exists(self.project_dir):
            os.makedirs(self.project_dir)
            
    def _get_timestamp(self):
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def save_text(self, filename: str, content: str):
        """Saves text content to a file."""
        filepath = os.path.join(self.project_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath

    def save_json(self, filename: str, data: dict):
        """Saves dictionary as JSON file."""
        filepath = os.path.join(self.project_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return filepath

    def save_image(self, filename: str, image_bytes: bytes):
        """Saves bytes as an image file."""
        filepath = os.path.join(self.project_dir, filename)
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        return filepath
    
    def exists(self, filename: str) -> bool:
        """Checks if a file exists in the project directory."""
        filepath = os.path.join(self.project_dir, filename)
        return os.path.exists(filepath)

    def load_text(self, filename: str) -> str:
        """Loads text content from a file."""
        filepath = os.path.join(self.project_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def load_json(self, filename: str):
        """Loads JSON data from a file."""
        filepath = os.path.join(self.project_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def get_path(self, filename: str) -> str:
        """Returns the absolute path to a file in the project directory."""
        return os.path.join(self.project_dir, filename)
