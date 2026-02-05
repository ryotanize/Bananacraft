"""
Curve Loft Tool - Creates curved surfaces (roofs, domes, arches).

Uses Bezier curves and lofting between them to create smooth architectural features.
"""
from typing import List, Dict, Any, Optional, Set, Tuple
from .base import BaseTool, Block
from ..geometry.bezier import QuadraticBezier, Point3D
from ..geometry.voxelize import voxelize_surface, fill_between_curves


class CurveLoftTool(BaseTool):
    """
    Creates a lofted surface between two Bezier curves.
    
    Perfect for:
    - Arched roofs (station canopies)
    - Barrel vaults
    - Curved walls
    - Domes (when combined)
    """
    
    name = "draw_curve_loft"
    description = "Creates a curved surface between two guide curves"
    
    def execute(self, params: Dict[str, Any], origin: tuple = (0, 0, 0)) -> List[Block]:
        """
        Execute curve loft creation.
        
        Args:
            params: {
                "curve_a": {
                    "start": [x, y, z],
                    "end": [x, y, z],
                    "control_height": int
                },
                "curve_b": {
                    "start": [x, y, z],
                    "end": [x, y, z],
                    "control_height": int
                },
                "frame_material": Optional[str],
                "fill_material": str,
                "pattern": Optional[str] ("solid", "grid_4x4", "grid_8x8")
            }
            origin: World origin offset
        """
        curve_a_params = params.get("curve_a", {})
        curve_b_params = params.get("curve_b", {})
        frame_material = params.get("frame_material")
        fill_material = params.get("fill_material", "glass")
        pattern = params.get("pattern", "solid")
        
        ox, oy, oz = origin
        
        # Create curve A
        curve_a = self._create_curve(curve_a_params, origin)
        
        # Create curve B
        curve_b = self._create_curve(curve_b_params, origin)
        
        # Generate surface voxels
        blocks: List[Block] = []
        
        if pattern == "solid":
            blocks.extend(self._create_solid_surface(curve_a, curve_b, fill_material))
        else:
            # Patterned surface (frame + fill)
            blocks.extend(self._create_patterned_surface(
                curve_a, curve_b, 
                frame_material or fill_material, 
                fill_material,
                pattern
            ))
        
        return blocks
    
    def _create_curve(self, params: Dict, origin: tuple) -> QuadraticBezier:
        """Create a Bezier curve from parameters."""
        ox, oy, oz = origin
        
        start = params.get("start", [0, 0, 0])
        end = params.get("end", [10, 0, 0])
        control_height = params.get("control_height", 5)
        
        # Apply origin offset
        start_offset = [start[0] + ox, start[1] + oy, start[2] + oz]
        end_offset = [end[0] + ox, end[1] + oy, end[2] + oz]
        
        return QuadraticBezier.from_arch(start_offset, end_offset, control_height)
    
    def _create_solid_surface(self, curve_a: QuadraticBezier, curve_b: QuadraticBezier, 
                               material: str) -> List[Block]:
        """Create a solid surface between two curves."""
        blocks = []
        
        # Get voxel coordinates for the surface
        voxels = fill_between_curves(curve_a, curve_b, resolution=40)
        
        # Convert to blocks
        seen: Set[Tuple[int, int, int]] = set()
        for (x, y, z) in voxels:
            if (x, y, z) not in seen:
                seen.add((x, y, z))
                blocks.append(Block(x, y, z, material))
        
        return blocks
    
    def _create_patterned_surface(self, curve_a: QuadraticBezier, curve_b: QuadraticBezier,
                                   frame_material: str, fill_material: str,
                                   pattern: str) -> List[Block]:
        """
        Create a surface with a grid pattern (like industrial glass roofs).
        
        Frame material forms the grid lines, fill material fills the cells.
        """
        blocks = []
        seen: Set[Tuple[int, int, int]] = set()
        
        # Parse pattern grid size
        if pattern == "grid_4x4":
            grid_size = 4
        elif pattern == "grid_8x8":
            grid_size = 8
        else:
            grid_size = 4
        
        # Sample the surface at high resolution
        resolution_u = 40  # Along the curves
        resolution_v = 20   # Between the curves
        
        for u in range(resolution_u + 1):
            for v in range(resolution_v + 1):
                # Get parameter values
                t_u = u / resolution_u
                t_v = v / resolution_v
                
                # Interpolate position between curves
                pa = curve_a.point_at(t_u)
                pb = curve_b.point_at(t_u)
                
                # Linear interpolation between curves
                x = int(pa.x + (pb.x - pa.x) * t_v)
                y = int(pa.y + (pb.y - pa.y) * t_v)
                z = int(pa.z + (pb.z - pa.z) * t_v)
                
                if (x, y, z) in seen:
                    continue
                seen.add((x, y, z))
                
                # Determine if this is frame or fill
                # Frame: at grid intervals or edges
                is_frame = (
                    u % grid_size == 0 or 
                    v % grid_size == 0 or
                    u == resolution_u or
                    v == resolution_v
                )
                
                material = frame_material if is_frame else fill_material
                blocks.append(Block(x, y, z, material))
        
        return blocks
    
    def _create_frame_ribs(self, curve_a: QuadraticBezier, curve_b: QuadraticBezier,
                           frame_material: str, num_ribs: int = 5) -> List[Block]:
        """
        Create structural ribs (arches) between the curves.
        
        Used for more visible frame structures.
        """
        blocks = []
        seen: Set[Tuple[int, int, int]] = set()
        
        for i in range(num_ribs + 1):
            t_v = i / num_ribs
            
            # Create an interpolated curve at this v position
            # Sample along this rib
            for j in range(50):
                t_u = j / 49
                
                pa = curve_a.point_at(t_u)
                pb = curve_b.point_at(t_u)
                
                x = int(pa.x + (pb.x - pa.x) * t_v)
                y = int(pa.y + (pb.y - pa.y) * t_v)
                z = int(pa.z + (pb.z - pa.z) * t_v)
                
                if (x, y, z) not in seen:
                    seen.add((x, y, z))
                    blocks.append(Block(x, y, z, frame_material))
        
        # Also add longitudinal ribs (along the curves)
        for curve in [curve_a, curve_b]:
            for j in range(50):
                t = j / 49
                point = curve.point_at(t)
                x, y, z = point.to_int_tuple()
                
                if (x, y, z) not in seen:
                    seen.add((x, y, z))
                    blocks.append(Block(x, y, z, frame_material))
        
        return blocks
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate curve loft parameters."""
        required = ["curve_a", "curve_b", "fill_material"]
        for key in required:
            if key not in params:
                return False
        
        for curve_key in ["curve_a", "curve_b"]:
            curve = params.get(curve_key, {})
            if "start" not in curve or "end" not in curve:
                return False
            if len(curve.get("start", [])) != 3 or len(curve.get("end", [])) != 3:
                return False
        
        return True
