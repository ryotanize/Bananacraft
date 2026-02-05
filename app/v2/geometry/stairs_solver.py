"""
Stairs Solver - Discrete Smoothing for Minecraft Architecture

Determines optimal block types (full block, slab, stairs) and orientations
based on local curve geometry to create smooth-looking structures.
"""
import math
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum

from .bezier import BezierCurve, Point3D


class BlockType(Enum):
    """Types of blocks for smooth construction."""
    FULL = "full"           # Regular full block
    SLAB_BOTTOM = "bottom"  # Bottom slab (lower half)
    SLAB_TOP = "top"        # Top slab (upper half)
    STAIRS = "stairs"       # Stairs block with facing direction


class Facing(Enum):
    """Cardinal directions for stairs facing."""
    NORTH = "north"  # -Z
    SOUTH = "south"  # +Z
    EAST = "east"    # +X
    WEST = "west"    # -X


@dataclass
class SmartBlock:
    """
    A block with type and orientation information.
    
    For slabs: variant is 'top' or 'bottom'
    For stairs: variant is the facing direction
    """
    x: int
    y: int
    z: int
    base_material: str
    block_type: BlockType
    facing: Optional[Facing] = None
    
    def to_minecraft_id(self) -> str:
        """Convert to Minecraft block ID with properties."""
        prefix = f"minecraft:{self.base_material}"
        
        if self.block_type == BlockType.FULL:
            return prefix
        
        elif self.block_type == BlockType.SLAB_BOTTOM:
            return f"minecraft:{self.base_material}_slab[type=bottom]"
        
        elif self.block_type == BlockType.SLAB_TOP:
            return f"minecraft:{self.base_material}_slab[type=top]"
        
        elif self.block_type == BlockType.STAIRS:
            facing = self.facing.value if self.facing else "north"
            return f"minecraft:{self.base_material}_stairs[facing={facing}]"
        
        return prefix
    
    def to_dict(self) -> Dict:
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "type": self.to_minecraft_id()
        }


class StairsSolver:
    """
    Analyzes curve geometry and determines optimal block placement
    for smooth-looking discrete structures.
    """
    
    # Slope thresholds (in degrees)
    SLAB_THRESHOLD = 22.5      # Use slabs for gentler slopes
    STAIRS_THRESHOLD = 67.5    # Use stairs for steeper slopes
    
    def __init__(self, material: str = "stone_brick"):
        """
        Args:
            material: Base material (e.g., 'stone_brick', 'oak')
                     Will be converted to appropriate stair/slab variant
        """
        self.material = material
        
        # Map base materials to their stair/slab variants
        self.material_map = {
            # Stone variants
            "stone": "stone",
            "cobblestone": "cobblestone",
            "stone_brick": "stone_brick",
            "stone_bricks": "stone_brick",
            "mossy_stone_brick": "mossy_stone_brick",
            "brick": "brick",
            "nether_brick": "nether_brick",
            "quartz": "quartz",
            "smooth_quartz": "smooth_quartz",
            "sandstone": "sandstone",
            "red_sandstone": "red_sandstone",
            "prismarine": "prismarine",
            "dark_prismarine": "dark_prismarine",
            "purpur": "purpur",
            "end_stone_brick": "end_stone_brick",
            "blackstone": "blackstone",
            "polished_blackstone": "polished_blackstone",
            "deepslate_brick": "deepslate_brick",
            "deepslate_tile": "deepslate_tile",
            "mud_brick": "mud_brick",
            
            # Wood variants
            "oak": "oak",
            "spruce": "spruce",
            "birch": "birch",
            "jungle": "jungle",
            "acacia": "acacia",
            "dark_oak": "dark_oak",
            "mangrove": "mangrove",
            "cherry": "cherry",
            "bamboo": "bamboo",
            "crimson": "crimson",
            "warped": "warped",
            
            # Copper variants
            "cut_copper": "cut_copper",
            "exposed_cut_copper": "exposed_cut_copper",
            "weathered_cut_copper": "weathered_cut_copper",
            "oxidized_cut_copper": "oxidized_cut_copper",
        }
    
    def get_base_material(self) -> str:
        """Get the normalized base material name."""
        return self.material_map.get(self.material, self.material)
    
    def solve_curve(self, curve: BezierCurve, num_samples: int = 50) -> List[SmartBlock]:
        """
        Generate optimally-typed blocks along a curve.
        
        Analyzes the local slope at each point and chooses
        full blocks, slabs, or stairs accordingly.
        """
        blocks: List[SmartBlock] = []
        seen: set = set()
        
        base_mat = self.get_base_material()
        
        for i in range(num_samples + 1):
            t = i / num_samples
            
            # Get position and slope
            point = curve.point_at(t)
            slope = abs(curve.slope_at(t)) if hasattr(curve, 'slope_at') else 0
            tangent = curve.tangent_at(t)
            
            # Get voxel coordinates
            x, y, z = point.to_int_tuple()
            
            # Skip if already placed
            if (x, y, z) in seen:
                continue
            seen.add((x, y, z))
            
            # Determine block type based on slope
            block_type, facing = self._choose_block_type(slope, tangent)
            
            block = SmartBlock(
                x=x, y=y, z=z,
                base_material=base_mat,
                block_type=block_type,
                facing=facing
            )
            blocks.append(block)
        
        return blocks
    
    def _choose_block_type(self, slope: float, tangent: Point3D) -> Tuple[BlockType, Optional[Facing]]:
        """
        Choose appropriate block type based on local geometry.
        
        Args:
            slope: Absolute slope angle in degrees
            tangent: Tangent vector at this point
            
        Returns:
            (BlockType, optional Facing direction)
        """
        # Nearly horizontal - use full blocks
        if slope < self.SLAB_THRESHOLD:
            return BlockType.FULL, None
        
        # Medium slope - use slabs
        elif slope < self.STAIRS_THRESHOLD:
            # Determine top or bottom based on curve direction
            if tangent.y > 0:
                return BlockType.SLAB_TOP, None
            else:
                return BlockType.SLAB_BOTTOM, None
        
        # Steep slope - use stairs
        else:
            facing = self._tangent_to_facing(tangent)
            return BlockType.STAIRS, facing
    
    def _tangent_to_facing(self, tangent: Point3D) -> Facing:
        """
        Convert a tangent vector to the closest cardinal facing direction.
        
        Stairs face the direction they ascend towards.
        """
        # Determine primary horizontal direction
        if abs(tangent.x) > abs(tangent.z):
            # X is dominant
            if tangent.x > 0:
                return Facing.WEST if tangent.y > 0 else Facing.EAST
            else:
                return Facing.EAST if tangent.y > 0 else Facing.WEST
        else:
            # Z is dominant
            if tangent.z > 0:
                return Facing.NORTH if tangent.y > 0 else Facing.SOUTH
            else:
                return Facing.SOUTH if tangent.y > 0 else Facing.NORTH
    
    def solve_edge(self, start: Tuple[int, int, int], end: Tuple[int, int, int]) -> List[SmartBlock]:
        """
        Generate blocks along a straight edge with appropriate smoothing.
        
        For diagonal edges (like roof ridges), uses stairs for smooth appearance.
        """
        blocks: List[SmartBlock] = []
        base_mat = self.get_base_material()
        
        x0, y0, z0 = start
        x1, y1, z1 = end
        
        dx = x1 - x0
        dy = y1 - y0
        dz = z1 - z0
        
        # Calculate slope
        horizontal_dist = math.sqrt(dx * dx + dz * dz)
        if horizontal_dist < 0.001:
            slope = 90.0 if dy != 0 else 0.0
        else:
            slope = math.degrees(math.atan2(abs(dy), horizontal_dist))
        
        # Create tangent-like direction
        length = math.sqrt(dx*dx + dy*dy + dz*dz)
        if length < 0.001:
            return blocks
        
        tangent = Point3D(dx / length, dy / length, dz / length)
        
        # Number of steps
        steps = max(abs(dx), abs(dy), abs(dz), 1)
        
        for i in range(steps + 1):
            t = i / steps
            x = round(x0 + dx * t)
            y = round(y0 + dy * t)
            z = round(z0 + dz * t)
            
            block_type, facing = self._choose_block_type(slope, tangent)
            
            blocks.append(SmartBlock(
                x=x, y=y, z=z,
                base_material=base_mat,
                block_type=block_type,
                facing=facing
            ))
        
        return blocks
