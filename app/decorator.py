import json
import os
try:
    from app.api_client import GeminiClient
except ImportError:
    from api_client import GeminiClient

class Decorator:
    def __init__(self, gemini_client):
        self.client = gemini_client

    def generate_decoration_plan(self, structure_json_path, concept_text, image_path=None):
        """
        Analyzes structure, concept, AND visual reference to generate decoration instructions.
        Returns a list of decoration actions.
        """
        # Load structure
        with open(structure_json_path, 'r') as f:
            blocks = json.load(f)
            
        # Summary & Bounds (Reusable logic)
        xs = [b['x'] for b in blocks]
        ys = [b['y'] for b in blocks]
        zs = [b['z'] for b in blocks]
        bounds = {
            "min_x": min(xs), "max_x": max(xs),
            "min_y": min(ys), "max_y": max(ys),
            "min_z": min(zs), "max_z": max(zs)
        }
        
        # Load Image if provided
        image_bytes = None
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as img_f:
                image_bytes = img_f.read()
        
        prompt = f"""
        # Mission
        The attached image is the "Concept Design" for a building.
        The JSON data provided below represents the "Voxel Structure" of this building in Minecraft.

        Your goal is to decorate this structure to match the Concept Image as closely as possible using Minecraft blocks.

        # Context
        - Theme: {concept_text}
        - Building Bounds: {bounds}

        # Instructions
        1. **Analyze the Image**: Look at the lighting (lanterns, glowstone), furniture, plants (leaves, pots), and surface details (trapdoors, buttons, signs) in the Concept Image.
        2. **Apply to Structure**: identifying the corresponding coordinates in the Voxel Structure.
        3. **Generate Actions**: Create a list of `setblock` instructions to place these decoration blocks.

        # Rules
        - **Do NOT destroy** the main walls/floors unless necessary for replacing with a decoration block (e.g., changing a wall block to a window or light).
        - **Focus on Details**: Add things that were lost during voxelization, such as:
            - Lanterns hanging from ceilings or sitting on fences.
            - Flower pots and leaves for greenery.
            - Trapdoors used as shutters or texture.
            - Stairs/Slabs for furniture (tables, chairs).
        - **Lighting is Critical**: Ensure the building is lit according to the image mood.

        # Output Format
        Return ONLY a valid JSON object with the following structure:
        {{
          "instructions": [
            {{ "x": 10, "y": 65, "z": 10, "action": "setblock", "block": "minecraft:lantern" }},
            {{ "x": 11, "y": 64, "z": 10, "action": "place", "block": "minecraft:oak_stairs[facing=north]" }}
          ]
        }}

        # Structure Data (Sample - First 2000 blocks)
        {json.dumps(blocks[:2000])}
        """
        
        response_text = self.client.generate_text(prompt, image_bytes=image_bytes)
        print(f"DEBUG: Raw Response from Gemini:\n{response_text[:500]}...")
        
        # Extract JSON (same as before) # Print first 500 chars
        
        # Extract JSON
        try:
            # Simple heuristic to find JSON start/end if wrapper text exists
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = response_text[start:end]
                data = json.loads(json_str)
                return data.get("instructions", [])
            else:
                print("Failed to parse Decoration JSON")
                return []
        except Exception as e:
            print(f"Decoration Parsing Error: {e}")
            return []
