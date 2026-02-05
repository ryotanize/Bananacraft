"""
Window Tool - Place windows in walls

Creates window openings with glass panes and optional frames.
"""
from typing import List, Dict, Any
from .base import BaseTool, Block


class PlaceWindowTool(BaseTool):
    """
    Places a window at a specified location.
    
    Windows consist of:
    - Glass panes (or glass blocks)
    - Optional frame (wood or stone)
    - Optional flower boxes below
    """
    
    name = "place_window"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": "place_window",
            "description": """Places a window at a specified position on a wall.

Example - simple 2x2 window with oak frame:
{
  "position": [5, 3, 0],
  "width": 2,
  "height": 2,
  "facing": "north",
  "glass_type": "glass_pane",
  "frame_material": "oak_planks",
  "has_flower_box": true
}

Example - large 3x2 window without frame:
{
  "position": [10, 2, 5],
  "width": 3,
  "height": 2,
  "facing": "east",
  "glass_type": "glass"
}""",
            "parameters": {
                "type": "object",
                "properties": {
                    "position": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "[x, y, z] - bottom-left corner of window"
                    },
                    "width": {
                        "type": "integer",
                        "description": "Window width in blocks (1-5)"
                    },
                    "height": {
                        "type": "integer",
                        "description": "Window height in blocks (1-4)"
                    },
                    "facing": {
                        "type": "string",
                        "enum": ["north", "south", "east", "west"],
                        "description": "Direction the window faces"
                    },
                    "glass_type": {
                        "type": "string",
                        "enum": ["glass", "glass_pane", "white_stained_glass", "light_blue_stained_glass"],
                        "description": "Type of glass to use"
                    },
                    "frame_material": {
                        "type": "string",
                        "enum": ["none", "oak_planks", "dark_oak_planks", "spruce_planks", "stone_bricks", "stripped_oak_log"],
                        "description": "Material for window frame"
                    },
                    "has_flower_box": {
                        "type": "boolean",
                        "description": "Whether to add a flower box below the window"
                    }
                },
                "required": ["position", "width", "height", "facing", "glass_type"]
            }
        }
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        required = ["position", "width", "height", "facing", "glass_type"]
        return all(k in params for k in required)
    
    def execute(self, params: Dict[str, Any], origin: tuple = (0, 0, 0)) -> List[Block]:
        pos = params["position"]
        width = params["width"]
        height = params["height"]
        facing = params["facing"]
        glass_type = params["glass_type"]
        frame_material = params.get("frame_material", "none")
        has_flower_box = params.get("has_flower_box", False)
        
        x, y, z = pos[0] + origin[0], pos[1] + origin[1], pos[2] + origin[2]
        blocks = []
        
        # Determine direction offsets based on facing
        if facing in ["north", "south"]:
            dx, dz = 1, 0  # Window extends in X direction
        else:  # east, west
            dx, dz = 0, 1  # Window extends in Z direction
        
        # Place frame if specified
        if frame_material and frame_material != "none":
            # Top frame
            for i in range(-1, width + 1):
                bx = x + i * dx
                bz = z + i * dz
                blocks.append(Block(bx, y + height, bz, frame_material))
            
            # Bottom frame
            for i in range(-1, width + 1):
                bx = x + i * dx
                bz = z + i * dz
                blocks.append(Block(bx, y - 1, bz, frame_material))
            
            # Side frames
            for j in range(-1, height + 1):
                # Left side
                blocks.append(Block(x - dx, y + j, z - dz, frame_material))
                # Right side
                bx = x + (width - 1) * dx + dx
                bz = z + (width - 1) * dz + dz
                blocks.append(Block(bx, y + j, bz, frame_material))
        
        # Place glass
        for i in range(width):
            for j in range(height):
                bx = x + i * dx
                bz = z + i * dz
                blocks.append(Block(bx, y + j, bz, glass_type))
        
        # Place flower box if requested
        if has_flower_box:
            flower_box_material = "oak_trapdoor"  # Trapdoors make good flower boxes
            for i in range(width):
                bx = x + i * dx
                bz = z + i * dz
                blocks.append(Block(bx, y - 2, bz, flower_box_material))
                # Add flowers
                blocks.append(Block(bx, y - 1, bz, "potted_red_tulip"))
        
        return blocks
