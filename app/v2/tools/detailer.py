"""
Detailer Tool - The "Set Generation" Engine.
Allows Gemini to paint structures onto specific architectural elements 
without worrying about absolute coordinates.
"""
from typing import List, Dict, Any
from .base import BaseTool, Block

class DecorateElementTool(BaseTool):
    """
    Attaches a structure of blocks to a target element ID.
    Handles coordinate transformation (Rotation/Translation) automatically.
    """
    name = "decorate_element"
    
    def __init__(self, analyzer=None):
        self.analyzer = analyzer

    def set_analyzer(self, analyzer):
        self.analyzer = analyzer

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return "target_id" in params and "structures" in params

    def execute(self, params: Dict[str, Any], origin: tuple = (0, 0, 0)) -> List[Block]:
        if not self.analyzer:
            # Fallback or empty if no context
            print("Warning: DecorateElementTool executed without Analyzer context.")
            return []

        target_id = params["target_id"]
        pos_mode = params.get("position", "bottom_left")
        offset = params.get("offset", [0, 0, 0]) # [dx, dy, dz]
        structures = params["structures"] # List of {x,y,z,type}
        
        # 1. Get Anchor Point & Facing from Analyzer
        anchor_x, anchor_y, anchor_z, facing = self.analyzer.calculate_anchor(target_id, pos_mode)
        
        blocks = []
        ox, oy, oz = origin

        # 2. Get Dimensions for Bounds Checking
        width, height = self.analyzer.get_element_dimensions(target_id)
        
        # 3. Calculate Valid Local Ranges (Relative to Anchor)
        # Anchor depends on pos_mode.
        # We need to define min_x, max_x, min_y, max_y relative to that anchor.
        
        # Default Full Ranges (0 to width, 0 to height)
        # But if pos_mode moves the origin, we shift these.
        
        min_lx, max_lx = 0, width
        min_ly, max_ly = 0, height
        
        if pos_mode == "bottom_left":
            # Anchor is at (0,0) of the element
            min_lx, max_lx = 0, width
            min_ly, max_ly = 0, height
            
        elif pos_mode == "bottom_center":
            # Anchor is at (width/2, 0)
            min_lx, max_lx = -width/2, width/2
            min_ly, max_ly = 0, height
            
        elif pos_mode == "center":
            # Anchor is at (width/2, height/2)
            min_lx, max_lx = -width/2, width/2
            min_ly, max_ly = -height/2, height/2
            
        elif pos_mode == "top_center":
            # Anchor is at (width/2, height)
            min_lx, max_lx = -width/2, width/2
            min_ly, max_ly = -height, 0

        # Buffer allows small overhangs (e.g. leaves, frames)
        BUFFER = 1 
        min_lx -= BUFFER
        max_lx += BUFFER
        min_ly -= BUFFER
        max_ly += BUFFER
        
        def transform(lx, ly, lz, face):
            # Returns (world_dx, world_dy, world_dz)
            
            # Case North (-Z)
            # If looking AT North face (from South), Right is West (-X). Out is North (-Z).
            if face == "north":
                return -lx, ly, -lz 
            
            # Case South (+Z)
            # If looking AT South face (from North), Right is East (+X). Out is South (+Z).
            elif face == "south":
                return lx, ly, lz
                
            # Case East (+X)
            # If looking AT East face (from West), Right is North (-Z). Out is East (+X).
            elif face == "east":
                return -lz, ly, lx
            
            # Case West (-X)
            # If looking AT West face (from East), Right is South (+Z). Out is West (-X).
            elif face == "west":
                return lz, ly, -lx
                
            # Case Up (+Y) - Roof
            # Right +X, Up -Z (depth), Out +Y
            elif face == "up":
                return lx, lz, ly 
                
            return lx, ly, lz

        for b in structures:
            lx, ly, lz = b.get("x", 0), b.get("y", 0), b.get("z", 0)
            
            # --- BOUNDS CHECK ---
            # Check if block is within valid local range + buffer
            # We only check X and Y (Surface dimensions). Z is depth (out/in), usually fine.
            if not (min_lx <= lx <= max_lx and min_ly <= ly <= max_ly):
                # Out of bounds -> Skip
                continue
            
            b_type = b.get("type", "stone")
            
            # A. Transform the block position
            tx, ty, tz = transform(lx, ly, lz, facing)
            
            # B. Transform the offset
            off_x, off_y, off_z = transform(offset[0], offset[1], offset[2], facing)
            
            # C. Transform block metadata if needed (stairs facing etc)
            # (Simple heuristic: replace 'facing=north' based on rotation)
            # This is complex, so for now we assume Gemini outputs correct relative facings 
            # OR we rely on generic blocks. 
            # Ideally, we should rotate the 'facing=' string in b_type too.
            # For this version, we keep b_type as is.
            
            # Calculate Final World Coord
            final_x = int(anchor_x + off_x + tx + ox)
            final_y = int(anchor_y + off_y + ty + oy)
            final_z = int(anchor_z + off_z + tz + oz)
            
            blocks.append(Block(final_x, final_y, final_z, b_type))
            
        return blocks