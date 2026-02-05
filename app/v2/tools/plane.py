"""
Plane Tool - Draw arbitrary quadrilateral surfaces in Minecraft

Creates a filled surface between two lines (edges), enabling:
- Walls (vertical planes)
- Floors (horizontal planes)  
- Sloped roofs (angled planes)
- Any quadrilateral surface
"""
from typing import List, Dict, Any, Tuple
from .base import BaseTool, Block


class PlaneTool(BaseTool):
    """
    Draws a filled quadrilateral surface between two edges.
    
    Each edge is defined by two 3D points. The surface is filled
    by linearly interpolating between the edges.
    
    Examples:
        Vertical wall:
            edge_a: [[0,0,0], [10,0,0]]  (bottom edge)
            edge_b: [[0,5,0], [10,5,0]]  (top edge)
        
        Sloped roof:
            edge_a: [[0,5,0], [10,5,0]]    (eave)
            edge_b: [[5,10,0], [5,10,10]]  (ridge, higher)
        
        Floor:
            edge_a: [[0,0,0], [10,0,0]]
            edge_b: [[0,0,10], [10,0,10]]
    """
    
    name = "draw_plane"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": "draw_plane",
            "description": """Creates a filled quadrilateral surface between two edges.
Each edge is defined by 2 points [x,y,z]. The surface fills the area between them.

Use for: walls, floors, sloped roofs, any flat or angled surface.

Example - vertical wall:
{
  "edge_a": [[0, 0, 0], [20, 0, 0]],
  "edge_b": [[0, 8, 0], [20, 8, 0]],
  "material": "bricks",
  "window_pattern": "grid_2x2"
}

Example - sloped roof:
{
  "edge_a": [[0, 5, 0], [0, 5, 10]],
  "edge_b": [[5, 10, 0], [5, 10, 10]],
  "material": "dark_oak_planks"
}""",
            "parameters": {
                "type": "object",
                "properties": {
                    "edge_a": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "integer"}
                        },
                        "description": "First edge: [[x1,y1,z1], [x2,y2,z2]]"
                    },
                    "edge_b": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "integer"}
                        },
                        "description": "Second edge: [[x1,y1,z1], [x2,y2,z2]]"
                    },
                    "material": {
                        "type": "string",
                        "description": "Block type for the surface"
                    },
                    "window_pattern": {
                        "type": "string",
                        "enum": ["none", "grid_2x2", "grid_3x3"],
                        "description": "Optional window pattern (for walls)"
                    }
                },
                "required": ["edge_a", "edge_b", "material"]
            }
        }
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        required = ["edge_a", "edge_b", "material"]
        if not all(k in params for k in required):
            return False
        
        # Validate edges have 2 points each
        for edge_name in ["edge_a", "edge_b"]:
            edge = params.get(edge_name, [])
            if len(edge) != 2:
                return False
            for point in edge:
                if len(point) != 3:
                    return False
        
        return True
    
    def execute(self, params: Dict[str, Any], origin: tuple = (0, 0, 0)) -> List[Block]:
        """
        Generate blocks for the quadrilateral surface.
        
        Uses linear interpolation between edges to fill the surface.
        """
        edge_a = params["edge_a"]
        edge_b = params["edge_b"]
        material = params["material"]
        window_pattern = params.get("window_pattern", "none")
        
        # Convert edges to tuples with origin offset
        a1 = (edge_a[0][0] + origin[0], edge_a[0][1] + origin[1], edge_a[0][2] + origin[2])
        a2 = (edge_a[1][0] + origin[0], edge_a[1][1] + origin[1], edge_a[1][2] + origin[2])
        b1 = (edge_b[0][0] + origin[0], edge_b[0][1] + origin[1], edge_b[0][2] + origin[2])
        b2 = (edge_b[1][0] + origin[0], edge_b[1][1] + origin[1], edge_b[1][2] + origin[2])
        
        blocks = []
        placed = set()
        
        # Get window pattern function
        window_func = self._get_window_pattern(window_pattern)
        
        # Determine sampling resolution based on edge lengths
        len_a = self._line_length(a1, a2)
        len_b = self._line_length(b1, b2)
        max_edge_len = max(len_a, len_b, 1)
        
        # Cross-edge length (between edges)
        cross_len = max(self._line_length(a1, b1), self._line_length(a2, b2), 1)
        
        # Sample density (oversample for smooth voxelization)
        edge_samples = int(max_edge_len * 2) + 1
        cross_samples = int(cross_len * 2) + 1
        
        # Fill the quadrilateral surface
        for i in range(cross_samples):
            t = i / max(cross_samples - 1, 1)  # 0 to 1 across edges
            
            # Interpolate start and end points along each edge
            # Line from edge_a to edge_b at parameter t
            p1 = self._lerp_point(a1, b1, t)
            p2 = self._lerp_point(a2, b2, t)
            
            # Draw line from p1 to p2
            for j in range(edge_samples):
                s = j / max(edge_samples - 1, 1)  # 0 to 1 along the line
                
                px = int(round(p1[0] + s * (p2[0] - p1[0])))
                py = int(round(p1[1] + s * (p2[1] - p1[1])))
                pz = int(round(p1[2] + s * (p2[2] - p1[2])))
                
                pos = (px, py, pz)
                if pos in placed:
                    continue
                placed.add(pos)
                
                # Check window pattern
                if window_func and window_func(i, j, cross_samples, edge_samples):
                    blocks.append(Block(px, py, pz, "glass"))
                else:
                    blocks.append(Block(px, py, pz, material))
        
        return blocks
    
    def _lerp_point(self, p1: tuple, p2: tuple, t: float) -> tuple:
        """Linear interpolation between two points."""
        return (
            p1[0] + t * (p2[0] - p1[0]),
            p1[1] + t * (p2[1] - p1[1]),
            p1[2] + t * (p2[2] - p1[2])
        )
    
    def _line_length(self, p1: tuple, p2: tuple) -> float:
        """Calculate distance between two points."""
        return ((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2 + (p2[2]-p1[2])**2) ** 0.5
    
    def _get_window_pattern(self, pattern: str):
        """Get window pattern check function."""
        if pattern == "none" or not pattern:
            return None
        
        if pattern == "grid_2x2":
            def check(cross_idx, edge_idx, cross_total, edge_total):
                # Create 2x2 windows with spacing
                cross_mod = cross_idx % 4
                edge_mod = edge_idx % 4
                # Window in the middle area
                in_middle_cross = cross_idx > 2 and cross_idx < cross_total - 2
                in_middle_edge = edge_idx > 2 and edge_idx < edge_total - 2
                return cross_mod < 2 and edge_mod < 2 and in_middle_cross and in_middle_edge
            return check
        
        if pattern == "grid_3x3":
            def check(cross_idx, edge_idx, cross_total, edge_total):
                cross_mod = cross_idx % 5
                edge_mod = edge_idx % 5
                in_middle_cross = cross_idx > 2 and cross_idx < cross_total - 2
                in_middle_edge = edge_idx > 2 and edge_idx < edge_total - 2
                return cross_mod < 3 and edge_mod < 3 and in_middle_cross and in_middle_edge
            return check
        
        return None
