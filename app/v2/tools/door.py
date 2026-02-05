"""
Door Tool - Place doors in walls

Creates door openings with proper door blocks.
"""
from typing import List, Dict, Any
from .base import BaseTool, Block


class PlaceDoorTool(BaseTool):
    """
    Places a door at a specified location.
    
    Doors can be:
    - Single or double width
    - Various wood types
    - With optional awning/porch roof above
    """
    
    name = "place_door"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": "place_door",
            "description": """Places a door at a specified position.

Example - oak double door with porch:
{
  "position": [8, 0, 0],
  "facing": "north",
  "door_type": "oak_door",
  "is_double": true,
  "has_porch": true,
  "porch_material": "oak_planks"
}

Example - simple single door:
{
  "position": [5, 0, 10],
  "facing": "west",
  "door_type": "dark_oak_door",
  "is_double": false
}""",
            "parameters": {
                "type": "object",
                "properties": {
                    "position": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "[x, y, z] - bottom of door"
                    },
                    "facing": {
                        "type": "string",
                        "enum": ["north", "south", "east", "west"],
                        "description": "Direction the door faces"
                    },
                    "door_type": {
                        "type": "string",
                        "enum": ["oak_door", "dark_oak_door", "spruce_door", "birch_door", "iron_door", "acacia_door"],
                        "description": "Type of door"
                    },
                    "is_double": {
                        "type": "boolean",
                        "description": "Whether it's a double door"
                    },
                    "has_porch": {
                        "type": "boolean",
                        "description": "Whether to add a small porch/awning above"
                    },
                    "porch_material": {
                        "type": "string",
                        "enum": ["oak_planks", "dark_oak_planks", "spruce_planks", "cobblestone", "stone_bricks"],
                        "description": "Material for porch roof"
                    }
                },
                "required": ["position", "facing", "door_type"]
            }
        }
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        required = ["position", "facing", "door_type"]
        return all(k in params for k in required)
    
    def execute(self, params: Dict[str, Any], origin: tuple = (0, 0, 0)) -> List[Block]:
        pos = params["position"]
        facing = params["facing"]
        door_type = params["door_type"]
        is_double = params.get("is_double", False)
        has_porch = params.get("has_porch", False)
        porch_material = params.get("porch_material", "oak_planks")
        
        x, y, z = pos[0] + origin[0], pos[1] + origin[1], pos[2] + origin[2]
        blocks = []
        
        # Determine direction offsets based on facing
        if facing in ["north", "south"]:
            dx, dz = 1, 0  # Door extends in X direction
            front_offset = (0, 0, -1 if facing == "north" else 1)
        else:  # east, west
            dx, dz = 0, 1  # Door extends in Z direction
            front_offset = (-1 if facing == "west" else 1, 0, 0)
        
        # Door height is 2 blocks
        door_width = 2 if is_double else 1
        
        # Place door blocks (bottom and top)
        for i in range(door_width):
            bx = x + i * dx
            bz = z + i * dz
            # Bottom half of door
            blocks.append(Block(bx, y, bz, door_type))
            # Top half of door
            blocks.append(Block(bx, y + 1, bz, door_type))
        
        # Add porch/awning if requested
        if has_porch:
            porch_depth = 2
            porch_width = door_width + 2
            
            # Porch roof (above door)
            for i in range(-1, door_width + 1):
                for d in range(porch_depth):
                    bx = x + i * dx + front_offset[0] * d
                    bz = z + i * dz + front_offset[2] * d
                    blocks.append(Block(bx, y + 3, bz, porch_material))
            
            # Porch supports
            # Left support
            blocks.append(Block(x - dx + front_offset[0], y, z - dz + front_offset[2], "oak_fence"))
            blocks.append(Block(x - dx + front_offset[0], y + 1, z - dz + front_offset[2], "oak_fence"))
            blocks.append(Block(x - dx + front_offset[0], y + 2, z - dz + front_offset[2], "oak_fence"))
            
            # Right support
            rx = x + (door_width - 1) * dx + dx + front_offset[0]
            rz = z + (door_width - 1) * dz + dz + front_offset[2]
            blocks.append(Block(rx, y, rz, "oak_fence"))
            blocks.append(Block(rx, y + 1, rz, "oak_fence"))
            blocks.append(Block(rx, y + 2, rz, "oak_fence"))
            
            # Lanterns on each side
            blocks.append(Block(x - dx, y + 2, z - dz, "lantern"))
            blocks.append(Block(x + door_width * dx, y + 2, z + door_width * dz, "lantern"))
        
        return blocks
