"""
Smooth Block Placer - Analyze surface normals and select stairs/slabs for smoother voxelization
"""
import numpy as np
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional


class BlockShape(Enum):
    """Types of block shapes for smooth placement"""
    FULL = auto()           # Regular full block
    SLAB_BOTTOM = auto()    # Half slab on bottom
    SLAB_TOP = auto()       # Half slab on top
    STAIR = auto()          # Stair block


@dataclass
class SmoothBlockInfo:
    """Information about a smooth block placement"""
    shape: BlockShape
    facing: Optional[str] = None  # For stairs: north, south, east, west
    half: Optional[str] = None    # For stairs: bottom, top
    
    def get_block_suffix(self) -> str:
        """Get the block state suffix for Minecraft commands"""
        if self.shape == BlockShape.FULL:
            return ""
        elif self.shape == BlockShape.SLAB_BOTTOM:
            return "[type=bottom]"
        elif self.shape == BlockShape.SLAB_TOP:
            return "[type=top]"
        elif self.shape == BlockShape.STAIR:
            half = self.half or "bottom"
            facing = self.facing or "north"
            return f"[facing={facing},half={half}]"
        return ""


# Block mapping: base block -> (stair variant, slab variant)
SMOOTH_BLOCK_VARIANTS = {
    # Wood planks
    'minecraft:oak_planks': ('minecraft:oak_stairs', 'minecraft:oak_slab'),
    'minecraft:spruce_planks': ('minecraft:spruce_stairs', 'minecraft:spruce_slab'),
    'minecraft:birch_planks': ('minecraft:birch_stairs', 'minecraft:birch_slab'),
    'minecraft:jungle_planks': ('minecraft:jungle_stairs', 'minecraft:jungle_slab'),
    'minecraft:acacia_planks': ('minecraft:acacia_stairs', 'minecraft:acacia_slab'),
    'minecraft:dark_oak_planks': ('minecraft:dark_oak_stairs', 'minecraft:dark_oak_slab'),
    'minecraft:mangrove_planks': ('minecraft:mangrove_stairs', 'minecraft:mangrove_slab'),
    'minecraft:cherry_planks': ('minecraft:cherry_stairs', 'minecraft:cherry_slab'),
    'minecraft:bamboo_planks': ('minecraft:bamboo_stairs', 'minecraft:bamboo_slab'),
    'minecraft:crimson_planks': ('minecraft:crimson_stairs', 'minecraft:crimson_slab'),
    'minecraft:warped_planks': ('minecraft:warped_stairs', 'minecraft:warped_slab'),
    
    # Stone variants
    'minecraft:stone': ('minecraft:stone_stairs', 'minecraft:stone_slab'),
    'minecraft:cobblestone': ('minecraft:cobblestone_stairs', 'minecraft:cobblestone_slab'),
    'minecraft:stone_bricks': ('minecraft:stone_brick_stairs', 'minecraft:stone_brick_slab'),
    'minecraft:mossy_stone_bricks': ('minecraft:mossy_stone_brick_stairs', 'minecraft:mossy_stone_brick_slab'),
    'minecraft:granite': ('minecraft:granite_stairs', 'minecraft:granite_slab'),
    'minecraft:polished_granite': ('minecraft:polished_granite_stairs', 'minecraft:polished_granite_slab'),
    'minecraft:diorite': ('minecraft:diorite_stairs', 'minecraft:diorite_slab'),
    'minecraft:polished_diorite': ('minecraft:polished_diorite_stairs', 'minecraft:polished_diorite_slab'),
    'minecraft:andesite': ('minecraft:andesite_stairs', 'minecraft:andesite_slab'),
    'minecraft:polished_andesite': ('minecraft:polished_andesite_stairs', 'minecraft:polished_andesite_slab'),
    'minecraft:deepslate': ('minecraft:cobbled_deepslate_stairs', 'minecraft:cobbled_deepslate_slab'),
    'minecraft:deepslate_bricks': ('minecraft:deepslate_brick_stairs', 'minecraft:deepslate_brick_slab'),
    'minecraft:deepslate_tiles': ('minecraft:deepslate_tile_stairs', 'minecraft:deepslate_tile_slab'),
    
    # Sandstone
    'minecraft:sandstone': ('minecraft:sandstone_stairs', 'minecraft:sandstone_slab'),
    'minecraft:smooth_sandstone': ('minecraft:smooth_sandstone_stairs', 'minecraft:smooth_sandstone_slab'),
    'minecraft:red_sandstone': ('minecraft:red_sandstone_stairs', 'minecraft:red_sandstone_slab'),
    'minecraft:smooth_red_sandstone': ('minecraft:smooth_red_sandstone_stairs', 'minecraft:smooth_red_sandstone_slab'),
    
    # Bricks and terracotta
    'minecraft:bricks': ('minecraft:brick_stairs', 'minecraft:brick_slab'),
    'minecraft:mud_bricks': ('minecraft:mud_brick_stairs', 'minecraft:mud_brick_slab'),
    
    # Nether
    'minecraft:nether_bricks': ('minecraft:nether_brick_stairs', 'minecraft:nether_brick_slab'),
    'minecraft:red_nether_bricks': ('minecraft:red_nether_brick_stairs', 'minecraft:red_nether_brick_slab'),
    'minecraft:blackstone': ('minecraft:blackstone_stairs', 'minecraft:blackstone_slab'),
    'minecraft:polished_blackstone': ('minecraft:polished_blackstone_stairs', 'minecraft:polished_blackstone_slab'),
    'minecraft:polished_blackstone_bricks': ('minecraft:polished_blackstone_brick_stairs', 'minecraft:polished_blackstone_brick_slab'),
    
    # Quartz
    'minecraft:quartz_block': ('minecraft:quartz_stairs', 'minecraft:quartz_slab'),
    'minecraft:smooth_quartz': ('minecraft:smooth_quartz_stairs', 'minecraft:smooth_quartz_slab'),
    
    # Prismarine
    'minecraft:prismarine': ('minecraft:prismarine_stairs', 'minecraft:prismarine_slab'),
    'minecraft:prismarine_bricks': ('minecraft:prismarine_brick_stairs', 'minecraft:prismarine_brick_slab'),
    'minecraft:dark_prismarine': ('minecraft:dark_prismarine_stairs', 'minecraft:dark_prismarine_slab'),
    
    # Purpur
    'minecraft:purpur_block': ('minecraft:purpur_stairs', 'minecraft:purpur_slab'),
    
    # End stone
    'minecraft:end_stone_bricks': ('minecraft:end_stone_brick_stairs', 'minecraft:end_stone_brick_slab'),
    
    # Copper (oxidation states)
    'minecraft:cut_copper': ('minecraft:cut_copper_stairs', 'minecraft:cut_copper_slab'),
    'minecraft:exposed_cut_copper': ('minecraft:exposed_cut_copper_stairs', 'minecraft:exposed_cut_copper_slab'),
    'minecraft:weathered_cut_copper': ('minecraft:weathered_cut_copper_stairs', 'minecraft:weathered_cut_copper_slab'),
    'minecraft:oxidized_cut_copper': ('minecraft:oxidized_cut_copper_stairs', 'minecraft:oxidized_cut_copper_slab'),
}


def analyze_surface_normal(
    position: tuple[int, int, int],
    mesh_vertices: np.ndarray,
    mesh_faces: np.ndarray,
    ray_intersector = None
) -> Optional[np.ndarray]:
    """
    Analyze the surface normal at a voxel position.
    
    Args:
        position: Voxel position (x, y, z)
        mesh_vertices: Mesh vertices array
        mesh_faces: Mesh faces array
        ray_intersector: Optional trimesh ray intersector for faster lookups
        
    Returns:
        Normal vector as numpy array, or None if no surface found
    """
    import trimesh
    
    # Create mesh if we don't have a ray intersector
    if ray_intersector is None:
        mesh = trimesh.Trimesh(vertices=mesh_vertices, faces=mesh_faces)
        ray_intersector = mesh.ray
    
    # Cast rays from the voxel center in 6 directions
    voxel_center = np.array(position, dtype=np.float64) + 0.5
    
    directions = np.array([
        [1, 0, 0], [-1, 0, 0],
        [0, 1, 0], [0, -1, 0],
        [0, 0, 1], [0, 0, -1]
    ], dtype=np.float64)
    
    # Find closest intersection
    closest_normal = None
    closest_distance = float('inf')
    
    for direction in directions:
        origin = voxel_center - direction * 0.6  # Start slightly inside
        
        try:
            locations, index_ray, index_tri = ray_intersector.intersects_location(
                ray_origins=origin.reshape(1, 3),
                ray_directions=direction.reshape(1, 3)
            )
            
            if len(locations) > 0:
                # Get the first intersection
                hit_point = locations[0]
                distance = np.linalg.norm(hit_point - voxel_center)
                
                if distance < closest_distance and distance < 1.5:
                    closest_distance = distance
                    tri_idx = index_tri[0]
                    
                    # Calculate face normal
                    face = mesh_faces[tri_idx]
                    v0, v1, v2 = mesh_vertices[face]
                    edge1 = v1 - v0
                    edge2 = v2 - v0
                    normal = np.cross(edge1, edge2)
                    norm = np.linalg.norm(normal)
                    if norm > 1e-10:
                        closest_normal = normal / norm
        except Exception:
            continue
    
    return closest_normal


def determine_block_shape(
    normal: np.ndarray,
    threshold_slab: float = 22.5,
    threshold_stair: float = 67.5
) -> SmoothBlockInfo:
    """
    Determine the appropriate block shape based on surface normal.
    
    Args:
        normal: Surface normal vector (normalized)
        threshold_slab: Angle threshold for slab selection (degrees)
        threshold_stair: Angle threshold for stair selection (degrees)
        
    Returns:
        SmoothBlockInfo with shape and orientation
    """
    if normal is None:
        return SmoothBlockInfo(shape=BlockShape.FULL)
    
    # Calculate angle from vertical (Y-axis)
    # normal.y = cos(angle), where angle is from vertical
    y_component = normal[1]  # Y is up in Minecraft
    
    # Angle from vertical in degrees
    angle_from_vertical = np.degrees(np.arccos(np.clip(abs(y_component), 0, 1)))
    
    # Determine if surface is facing up or down
    is_facing_up = y_component > 0
    
    # Determine horizontal direction for stairs
    xz_component = np.array([normal[0], 0, normal[2]])
    xz_magnitude = np.linalg.norm(xz_component)
    
    if xz_magnitude > 0.01:
        xz_normalized = xz_component / xz_magnitude
        
        # Determine facing direction (opposite to where the slope goes down)
        if abs(xz_normalized[0]) > abs(xz_normalized[2]):
            # More X than Z
            facing = "east" if xz_normalized[0] > 0 else "west"
        else:
            # More Z than X
            facing = "south" if xz_normalized[2] > 0 else "north"
    else:
        facing = "north"  # Default
    
    # Classify based on angle
    if angle_from_vertical < threshold_slab:
        # Nearly horizontal - consider slab
        if is_facing_up:
            return SmoothBlockInfo(shape=BlockShape.SLAB_TOP)
        else:
            return SmoothBlockInfo(shape=BlockShape.SLAB_BOTTOM)
    
    elif angle_from_vertical < threshold_stair:
        # Diagonal - use stairs
        half = "bottom" if is_facing_up else "top"
        return SmoothBlockInfo(
            shape=BlockShape.STAIR,
            facing=facing,
            half=half
        )
    
    else:
        # Nearly vertical or very steep - use full block
        return SmoothBlockInfo(shape=BlockShape.FULL)


def get_smooth_block_name(
    base_block: str,
    smooth_info: SmoothBlockInfo
) -> tuple[str, str]:
    """
    Get the appropriate block name for smooth placement.
    
    Args:
        base_block: The base block name (e.g., 'minecraft:oak_planks')
        smooth_info: SmoothBlockInfo with shape and orientation
        
    Returns:
        Tuple of (block_name, block_state_suffix)
    """
    if smooth_info.shape == BlockShape.FULL:
        return base_block, ""
    
    # Check if we have variants for this block
    if base_block not in SMOOTH_BLOCK_VARIANTS:
        return base_block, ""
    
    stair_variant, slab_variant = SMOOTH_BLOCK_VARIANTS[base_block]
    
    if smooth_info.shape in (BlockShape.SLAB_BOTTOM, BlockShape.SLAB_TOP):
        return slab_variant, smooth_info.get_block_suffix()
    
    elif smooth_info.shape == BlockShape.STAIR:
        return stair_variant, smooth_info.get_block_suffix()
    
    return base_block, ""


def can_smooth_block(block_name: str) -> bool:
    """Check if a block has stair/slab variants available"""
    return block_name in SMOOTH_BLOCK_VARIANTS
