"""
Infrastructure Tools - Roads, Zoning, and Public Works.
"""
from typing import List, Dict, Any
from .base import BaseTool, Block
import math

class DrawRoadTool(BaseTool):
    """
    Draws a road between two points with a specific width.
    """
    name = "draw_road"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": "draw_road",
            "description": "Draws a road/path between two points.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start": {"type": "array", "items": {"type": "integer"}},
                    "end": {"type": "array", "items": {"type": "integer"}},
                    "width": {"type": "integer"},
                    "material": {"type": "string"}
                },
                "required": ["start", "end", "width", "material"]
            }
        }
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        return all(k in params for k in ["start", "end", "width", "material"])
    
    def execute(self, params: Dict[str, Any], origin: tuple = (0, 0, 0)) -> List[Block]:
        start = params["start"] # [x, z]
        end = params["end"]
        width = int(params["width"])
        material = params["material"]
        
        # Determine relative coordinates
        # Assume Y=0 relative (ground level)
        x1, z1 = start
        x2, z2 = end
        
        # Vector along road
        dx = x2 - x1
        dz = z2 - z1
        length = math.sqrt(dx*dx + dz*dz)
        
        blocks = []
        if length == 0: return blocks
        
        # Normalize direction
        ux = dx / length
        uz = dz / length
        
        # Perpendicular vector (for width)
        px = -uz
        pz = ux
        
        # Draw roadway
        # Iterate along length
        step = 0.5 # Sampling step size
        w_step = 0.5
        
        curr_len = 0
        while curr_len <= length:
            # Center point on line
            cx = x1 + ux * curr_len
            cz = z1 + uz * curr_len
            
            # Iterate along width
            w_offset = -width / 2.0
            while w_offset <= width / 2.0:
                # Sample point
                sx = cx + px * w_offset
                sz = cz + pz * w_offset
                
                # Round to block coords
                bx = int(round(sx))
                bz = int(round(sz))
                
                # Add block (at relative Y=-1 to be flush with ground? Or Y=0?)
                # If foundation is at Y=64, and origin Y=64.
                # Usually we replace the floor block. relative Y=-1.
                # Let's assume Y=-1 is the "floor" layer.
                blocks.append(Block(bx + origin[0], origin[1] - 1, bz + origin[2], material))
                
                w_offset += w_step
            curr_len += step
            
        return blocks

class FillZoneTool(BaseTool):
    """
    Fills a rectangular zone.
    """
    name = "fill_zone"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": "fill_zone",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer"},
                    "z": {"type": "integer"},
                    "width": {"type": "integer"},
                    "depth": {"type": "integer"},
                    "material": {"type": "string"},
                    "decoration_type": {"type": "string"}
                },
                "required": ["x", "z", "width", "depth", "material"]
            }
        }
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        return all(k in params for k in ["x", "z", "width", "depth", "material"])

    def execute(self, params: Dict[str, Any], origin: tuple = (0, 0, 0)) -> List[Block]:
        x = params["x"]
        z = params["z"]
        w = params["width"]
        d = params["depth"]
        mat = params["material"]
        decor_type = params.get("decoration_type", "none")
        
        blocks = []
        for i in range(w):
            for j in range(d):
                # Floor layer (Y=-1)
                blocks.append(Block(x + i + origin[0], origin[1] - 1, z + j + origin[2], mat))
                
                # Simple random logic for decoration could go here (e.g. random flower)
                # But kept simple for now
                if decor_type == "park":
                    # Chance for tree handled by separate tool?
                    pass
                    
        return blocks

class PlaceStreetDecorTool(BaseTool):
    """
    Places predefined street furniture.
    """
    name = "place_street_decor"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": "place_street_decor",
            "parameters": {
                 "type": "object",
                 "properties": {
                     "x": {"type": "integer"},
                     "z": {"type": "integer"},
                     "type": {"type": "string"}
                 },
                 "required": ["x", "z", "type"]
            }
        }

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return all(k in params for k in ["x", "z", "type"])
        
    def execute(self, params: Dict[str, Any], origin: tuple = (0, 0, 0)) -> List[Block]:
        x = params["x"] + origin[0]
        z = params["z"] + origin[2]
        y = origin[1] # On top of ground
        t = params["type"]
        
        blocks = []
        
        if t == "lantern_post":
            # Simple lamp post
            # Fence x 3
            blocks.append(Block(x, y, z, "mossy_cobblestone_wall"))
            blocks.append(Block(x, y+1, z, "mossy_cobblestone_wall"))
            blocks.append(Block(x, y+2, z, "mossy_cobblestone_wall"))
            blocks.append(Block(x, y+3, z, "lantern"))
            
        elif t == "tree":
             # Extremely simple tree
             # Oak Log x 4
             blocks.append(Block(x, y, z, "oak_log"))
             blocks.append(Block(x, y+1, z, "oak_log"))
             blocks.append(Block(x, y+2, z, "oak_log"))
             blocks.append(Block(x, y+3, z, "oak_log"))
             # Leaves
             for lx in range(-1, 2):
                 for lz in range(-1, 2):
                     if lx == 0 and lz == 0: continue
                     blocks.append(Block(x+lx, y+2, z+lz, "oak_leaves"))
                     blocks.append(Block(x+lx, y+3, z+lz, "oak_leaves"))
             blocks.append(Block(x, y+4, z, "oak_leaves"))
             
        elif t == "bench":
             blocks.append(Block(x, y, z, "spruce_stairs[facing=east]"))
             
        elif t == "flower_bed":
             blocks.append(Block(x, y, z, "grass_block"))
             blocks.append(Block(x, y+1, z, "poppy"))
             
        return blocks
