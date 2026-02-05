"""
Wall Tool - Creates walls with optional window patterns.
"""
from typing import List, Dict, Any, Optional
from .base import BaseTool, Block


class DrawWallTool(BaseTool):
    """
    Creates a wall between two points.
    
    Supports:
    - Solid walls
    - Window patterns (grid-based)
    - Automatic orientation detection
    """
    
    name = "draw_wall"
    description = "Creates a wall between start and end coordinates with optional window pattern"
    
    def execute(self, params: Dict[str, Any], origin: tuple = (0, 0, 0)) -> List[Block]:
        """
        Execute wall creation.
        
        Args:
            params: {
                "start": [x, y, z],
                "end": [x, y, z],
                "material": str (e.g., "stone_bricks"),
                "window_pattern": Optional[str] ("none", "grid_2x2", "grid_3x3")
            }
            origin: World origin offset
        """
        start = params.get("start", [0, 0, 0])
        end = params.get("end", [0, 0, 0])
        material = params.get("material", "stone_bricks")
        window_pattern = params.get("window_pattern", "none")
        
        # Apply origin offset
        ox, oy, oz = origin
        x1, y1, z1 = start[0] + ox, start[1] + oy, start[2] + oz
        x2, y2, z2 = end[0] + ox, end[1] + oy, end[2] + oz
        
        # Normalize coordinates (ensure start <= end)
        x_min, x_max = min(x1, x2), max(x1, x2)
        y_min, y_max = min(y1, y2), max(y1, y2)
        z_min, z_max = min(z1, z2), max(z1, z2)
        
        blocks: List[Block] = []
        
        # Determine wall orientation
        # XY plane (Z constant) or YZ plane (X constant)
        is_x_wall = (x_max - x_min) > 0 and (z_max - z_min) == 0
        is_z_wall = (z_max - z_min) > 0 and (x_max - x_min) == 0
        
        # Get window pattern
        window_func = self._get_window_pattern(window_pattern)
        
        # Generate blocks
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                for z in range(z_min, z_max + 1):
                    # Calculate relative position for window pattern
                    if is_x_wall:
                        rel_h = x - x_min  # Horizontal position along wall
                        rel_v = y - y_min  # Vertical position
                        width = x_max - x_min + 1
                    elif is_z_wall:
                        rel_h = z - z_min
                        rel_v = y - y_min
                        width = z_max - z_min + 1
                    else:
                        # Thick wall or single column
                        rel_h, rel_v = 0, y - y_min
                        width = 1
                    
                    height = y_max - y_min + 1
                    
                    # Check if this position should be a window
                    if window_func(rel_h, rel_v, width, height):
                        block_type = "glass"
                    else:
                        block_type = material
                    
                    blocks.append(Block(x, y, z, block_type))
        
        return blocks
    
    def _get_window_pattern(self, pattern: str):
        """
        Returns a function that determines if a position should be a window.
        
        The function takes (h, v, width, height) and returns True for window positions.
        """
        if pattern == "none" or not pattern:
            return lambda h, v, w, ht: False
        
        elif pattern == "grid_2x2":
            # Windows every 4 blocks, 2x2 size, starting at offset 1
            def check(h, v, w, ht):
                # Skip edges (frame)
                if v == 0 or v == ht - 1:
                    return False
                if h == 0 or h == w - 1:
                    return False
                
                # 2x2 windows in 4x4 grid pattern
                h_mod = (h - 1) % 4
                v_mod = (v - 1) % 4
                return h_mod < 2 and v_mod < 2 and v > 1  # Not on bottom row
            
            return check
        
        elif pattern == "grid_3x3":
            # Larger windows, 3x3 size in 5x5 grid
            def check(h, v, w, ht):
                if v == 0 or v == ht - 1:
                    return False
                if h == 0 or h == w - 1:
                    return False
                
                h_mod = (h - 1) % 5
                v_mod = (v - 1) % 5
                return h_mod < 3 and v_mod < 3 and v > 1
            
            return check
        
        elif pattern == "arched":
            # Arched windows (taller than wide)
            def check(h, v, w, ht):
                if v == 0 or v == ht - 1 or v == 1:
                    return False
                if h == 0 or h == w - 1:
                    return False
                
                h_mod = (h - 1) % 4
                v_mod = (v - 2) % 6
                
                # Arch shape: wider at bottom, narrower at top
                if v_mod < 4:
                    return h_mod >= 1 and h_mod <= 2  # Center 2 blocks
                elif v_mod == 4:
                    return h_mod >= 1 and h_mod <= 2  # Arch top
                return False
            
            return check
        
        else:
            return lambda h, v, w, ht: False
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate wall parameters."""
        required = ["start", "end", "material"]
        for key in required:
            if key not in params:
                return False
        
        start = params.get("start", [])
        end = params.get("end", [])
        
        if len(start) != 3 or len(end) != 3:
            return False
        
        return True
