"""
Decoration Tool - Place decorative elements

Creates various decorations like lanterns, flower pots, fences, etc.
"""
from typing import List, Dict, Any
from .base import BaseTool, Block


class PlaceDecorationTool(BaseTool):
    """
    Places decorative elements at specified locations.
    
    Supports:
    - Lanterns and lights
    - Flower pots and plants
    - Fences and railings
    - Banners and flags
    """
    
    name = "place_decoration"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": "place_decoration",
            "description": """Places decorative elements at specified positions.

Example - lantern on wall:
{
  "positions": [[5, 3, 0], [10, 3, 0]],
  "decoration_type": "lantern"
}

Example - fence line:
{
  "positions": [[0, 1, 5], [1, 1, 5], [2, 1, 5], [3, 1, 5]],
  "decoration_type": "oak_fence"
}

Example - flower pots:
{
  "positions": [[3, 2, 0], [7, 2, 0]],
  "decoration_type": "potted_red_tulip"
}""",
            "parameters": {
                "type": "object",
                "properties": {
                    "positions": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "integer"}
                        },
                        "description": "List of [x, y, z] positions"
                    },
                    "decoration_type": {
                        "type": "string",
                        "enum": [
                            # Lights
                            "lantern", "soul_lantern", "torch", "wall_torch",
                            # Fences
                            "oak_fence", "dark_oak_fence", "spruce_fence", "cobblestone_wall",
                            # Plants
                            "potted_red_tulip", "potted_orange_tulip", "potted_white_tulip",
                            "potted_oak_sapling", "flower_pot", "rose_bush", "lilac",
                            # Other
                            "barrel", "chest", "crafting_table", "anvil",
                            "white_banner", "red_banner", "blue_banner"
                        ],
                        "description": "Type of decoration"
                    }
                },
                "required": ["positions", "decoration_type"]
            }
        }
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        return "positions" in params and "decoration_type" in params
    
    def execute(self, params: Dict[str, Any], origin: tuple = (0, 0, 0)) -> List[Block]:
        positions = params["positions"]
        decoration_type = params["decoration_type"]
        
        blocks = []
        for pos in positions:
            x = pos[0] + origin[0]
            y = pos[1] + origin[1]
            z = pos[2] + origin[2]
            blocks.append(Block(x, y, z, decoration_type))
        
        return blocks
