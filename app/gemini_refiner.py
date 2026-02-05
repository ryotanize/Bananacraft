
import os
import json
import base64
import requests
from io import BytesIO
from PIL import Image
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Define Response Schema
class BlockUpdate(BaseModel):
    row: int = Field(description="Row index in the grid (Y coordinate in grid)")
    col: int = Field(description="Column index in the grid (X/Z coordinate in grid)")
    type: str = Field(description="New Minecraft block type (e.g. glass, oak_door, stone_stairs)")

class FacadeRefinementResult(BaseModel):
    updates: list[BlockUpdate] = Field(description="List of blocks to update")

class GeminiRefiner:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            # Try loading dot env here too if not loaded?
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.environ.get("GEMINI_API_KEY")
            
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
        
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-3-pro-preview" # User requested specifically

    def refine_facade(self, image_input, facade_data):
        """
        Refines the facade grid based on the reference image using Gemini.
        
        Args:
            image_input: URL string or local path string to the reference image.
            facade_data: Dictionary containing 'grid' (2D list of block types).
        
        Returns:
            List of dictionaries [{'row': r, 'col': c, 'type': new_type}]
        """
        
        # 1. Prepare Image
        img_pil = None
        if image_input.startswith("http"):
            response = requests.get(image_input)
            img_pil = Image.open(BytesIO(response.content))
        else:
            img_pil = Image.open(image_input)
            
        # 2. Prepare JSON Context
        # Flatten grid for prompt context to save tokens/make it rigorous?
        # Or just pass the grid structure.
        # Let's pass dimensions and the grid. 
        # To save tokens, we might optimize representation, but for V2, raw JSON is fine.
        grid_json = json.dumps(facade_data["grid"])
        
        # 3. Build Prompt
        prompt = """
        You are an expert Minecraft Architect.
        Your task is to refine the voxel conversion of a building facade to match the reference image.
        
        Input Data:
        1. Reference Image: The appearance we want to achieve.
        2. Current Block Grid (JSON): A 2D array representing the current front view of the model.
           - Top-Left is (0,0).
           - Block types are strings like 'stone', 'oak_planks', 'air'.
        
        Instructions:
        - Identify architectural features in the image such as Windows, Doors, Roof Edges, and Patterns.
        - Correct the block types in the Grid to represent these features.
        - Example: If you see a window in the image but the grid has 'stone', change it to 'glass' or 'glass_pane'.
        - Example: If there is a door, use 'oak_door' (or appropriate wood).
        - Example: For roof edges, consider using stair blocks if appropriate (though standard voxelizer uses full blocks, you can suggest full blocks that look better, e.g. different material).
        - IMPORTANT: Do not change the overall shape too much, focus on MATERIALS and DETAILS (Windows/Doors).
        - Return ONLY the blocks that need to be changed.
        
        Output Format:
        JSON matching the schema: { "updates": [ { "row": int, "col": int, "type": "block_id" }, ... ] }
        """
        
        # 4. Call Gemini
        print("Sending request to Gemini...")
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    prompt,
                    img_pil,
                    grid_json
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=FacadeRefinementResult
                )
            )
            
            # 5. Parse Response
            result = response.parsed
            if not result:
                print("No result parsed from Gemini.")
                return []
                
            updates = []
            for update in result.updates:
                updates.append(update.model_dump())
                
            print(f"Gemini suggested {len(updates)} updates.")
            return updates
            
        except Exception as e:
            print(f"Gemini Error: {e}")
            return []
