"""
BVH Ray Voxelizer - Convert 3D meshes to voxels using ray casting
Based on ObjToSchematic's BVHRayVoxeliser algorithm with texture sampling support
"""
import numpy as np
import trimesh
from typing import Optional
from .mesh_loader import MeshData, load_mesh, scale_mesh_to_size, normalize_mesh_position
from .voxel_mesh import VoxelMesh


def voxelize_mesh(
    mesh: MeshData,
    target_size: int = 80,
    constraint_axis: str = 'y',
    overlap_rule: str = 'average',
    normalize_position: bool = True,
    progress_callback: Optional[callable] = None
) -> VoxelMesh:
    """
    Voxelize a mesh using BVH ray casting from 3 principal axes.
    
    Args:
        mesh: Input mesh data
        target_size: Size along the constraint axis
        constraint_axis: Which axis to constrain ('x', 'y', or 'z')
        overlap_rule: How to handle overlapping voxels ('first' or 'average')
        normalize_position: If True, move mesh to positive quadrant (like legacy)
        progress_callback: Optional callback(progress: float) for progress updates
        
    Returns:
        VoxelMesh containing all voxels
    """
    # Scale mesh to target size
    scaled_mesh, scale = scale_mesh_to_size(mesh, target_size, constraint_axis)
    
    # Add offset for even sizes (matching ObjToSchematic behavior)
    axis_index = {'x': 0, 'y': 1, 'z': 2}[constraint_axis.lower()]
    offset = np.zeros(3)
    if target_size % 2 == 0:
        offset[axis_index] = 0.5
    
    # Apply offset
    vertices = scaled_mesh.vertices + offset
    
    # Normalize position to positive quadrant (like legacy voxelizer)
    if normalize_position:
        min_bound = vertices.min(axis=0)
        vertices = vertices - min_bound
    
    # Create a new MeshData with transformed vertices
    transformed_mesh = MeshData(
        vertices=vertices,
        faces=scaled_mesh.faces,
        vertex_colors=scaled_mesh.vertex_colors,
        uv_coords=scaled_mesh.uv_coords,
        texture_image=scaled_mesh.texture_image,
        face_colors=scaled_mesh.face_colors
    )
    
    # Create trimesh for ray intersection
    tri_mesh = trimesh.Trimesh(vertices=vertices, faces=transformed_mesh.faces)
    
    # Get bounds for ray generation
    bounds_min = vertices.min(axis=0)
    bounds_max = vertices.max(axis=0)
    
    # Floor/ceil bounds to integer grid
    bounds_min = np.floor(bounds_min).astype(int)
    bounds_max = np.ceil(bounds_max).astype(int)
    
    # Create voxel mesh with specified overlap rule
    voxel_mesh = VoxelMesh(overlap_rule=overlap_rule)
    
    # --- Batch Ray Casting ---
    # Instead of casting one ray at a time, we generate all rays for an axis
    # and cast them in a single batch. This drastically reduces Python overhead.
    
    # X-axis rays
    ys = np.arange(bounds_min[1], bounds_max[1] + 1)
    zs = np.arange(bounds_min[2], bounds_max[2] + 1)
    yy, zz = np.meshgrid(ys, zs)
    ray_count = yy.size
    
    origins = np.zeros((ray_count, 3))
    origins[:, 0] = bounds_min[0] - 1
    origins[:, 1] = yy.flatten()
    origins[:, 2] = zz.flatten()
    
    directions = np.zeros((ray_count, 3))
    directions[:, 0] = 1
    
    _cast_rays_batch(tri_mesh, origins, directions, transformed_mesh, voxel_mesh)
    
    if progress_callback:
        progress_callback(0.33)

    # Y-axis rays
    xs = np.arange(bounds_min[0], bounds_max[0] + 1)
    zs = np.arange(bounds_min[2], bounds_max[2] + 1)
    xx, zz = np.meshgrid(xs, zs)
    ray_count = xx.size
    
    origins = np.zeros((ray_count, 3))
    origins[:, 0] = xx.flatten()
    origins[:, 1] = bounds_min[1] - 1
    origins[:, 2] = zz.flatten()
    
    directions = np.zeros((ray_count, 3))
    directions[:, 1] = 1
    
    _cast_rays_batch(tri_mesh, origins, directions, transformed_mesh, voxel_mesh)
    
    if progress_callback:
        progress_callback(0.66)

    # Z-axis rays
    xs = np.arange(bounds_min[0], bounds_max[0] + 1)
    ys = np.arange(bounds_min[1], bounds_max[1] + 1)
    xx, yy = np.meshgrid(xs, ys)
    ray_count = xx.size
    
    origins = np.zeros((ray_count, 3))
    origins[:, 0] = xx.flatten()
    origins[:, 1] = yy.flatten()
    origins[:, 2] = bounds_min[2] - 1
    
    directions = np.zeros((ray_count, 3))
    directions[:, 2] = 1
    
    _cast_rays_batch(tri_mesh, origins, directions, transformed_mesh, voxel_mesh)
    
    if progress_callback:
        progress_callback(1.0)
    
    return voxel_mesh


def _count_rays(bounds_min: np.ndarray, bounds_max: np.ndarray) -> int:
    """Count the total number of rays to be cast"""
    dims = bounds_max - bounds_min + 1
    return (dims[1] * dims[2]) + (dims[0] * dims[2]) + (dims[0] * dims[1])



def _cast_rays_batch(
    tri_mesh: trimesh.Trimesh,
    origins: np.ndarray,
    directions: np.ndarray,
    mesh_data: MeshData,
    voxel_mesh: VoxelMesh
) -> None:
    """
    Cast a batch of rays and add voxels at intersection points with proper color sampling.
    """
    if len(origins) == 0:
        return

    import time
    t0 = time.time()
    
    # Use trimesh ray casting (batch processing)
    locations, index_ray, index_tri = tri_mesh.ray.intersects_location(
        ray_origins=origins,
        ray_directions=directions
    )
    
    t1 = time.time()
    num_hits = len(locations)
    print(f"[DEBUG] Ray cast finished: {num_hits} hits from {len(origins)} rays in {t1 - t0:.4f}s")
    
    if num_hits == 0:
        return

    # Process hits
    print(f"[DEBUG] Processing {num_hits} hits...")
    
    for i, location in enumerate(locations):
        tri_index = index_tri[i]
        
        # Get color for this voxel using texture or vertex colors
        color = _get_voxel_color(mesh_data, tri_index, location)
        
        # Add voxel at the intersection point (no normal calculation for performance)
        voxel_mesh.add_voxel(location, color)
        
        if i % 10000 == 0 and i > 0:
            print(f"[DEBUG] Processed {i}/{num_hits} hits ({i/num_hits*100:.1f}%)")
            
    t2 = time.time()
    print(f"[DEBUG] Hit processing finished in {t2 - t1:.4f}s")


def _get_triangle_normal(
    mesh_data: MeshData,
    triangle_index: int,
    ray_direction: np.ndarray
) -> np.ndarray:
    """
    Calculate the surface normal for a triangle.
    Ensures the normal faces towards the ray origin (outward).
    """
    face = mesh_data.faces[triangle_index]
    v0, v1, v2 = mesh_data.vertices[face]
    
    # Calculate face normal using cross product
    edge1 = v1 - v0
    edge2 = v2 - v0
    normal = np.cross(edge1, edge2)
    
    # Normalize
    norm_magnitude = np.linalg.norm(normal)
    if norm_magnitude < 1e-10:
        return np.array([0.0, 1.0, 0.0], dtype=np.float32)  # Default up
    
    normal = normal / norm_magnitude
    
    # Make sure normal faces outward (opposite to ray direction)
    if np.dot(normal, ray_direction) > 0:
        normal = -normal
    
    return normal.astype(np.float32)


def _get_voxel_color(
    mesh_data: MeshData,
    triangle_index: int,
    position: np.ndarray
) -> np.ndarray:
    """
    Get the color for a voxel at the given position.
    Uses texture sampling with UV coordinates if available,
    otherwise falls back to vertex colors or face colors.
    """
    # Get triangle vertices
    face = mesh_data.faces[triangle_index]
    v0, v1, v2 = mesh_data.vertices[face]
    
    # Calculate barycentric coordinates using area-based method
    def triangle_area(a, b, c):
        ab = b - a
        ac = c - a
        return 0.5 * np.linalg.norm(np.cross(ab, ac))
    
    total_area = triangle_area(v0, v1, v2)
    if total_area < 1e-10:
        return np.array([0.5, 0.5, 0.5, 1.0], dtype=np.float32)
    
    w0 = triangle_area(v1, v2, position) / total_area
    w1 = triangle_area(v2, v0, position) / total_area
    w2 = triangle_area(v0, v1, position) / total_area
    
    # Priority 1: Texture sampling with UV coordinates
    if mesh_data.has_texture() and mesh_data.uv_coords is not None:
        uv0 = mesh_data.uv_coords[face[0]]
        uv1 = mesh_data.uv_coords[face[1]]
        uv2 = mesh_data.uv_coords[face[2]]
        
        # Interpolate UV coordinates using barycentric weights
        uv = uv0 * w0 + uv1 * w1 + uv2 * w2
        
        # Sample texture at interpolated UV
        color = mesh_data.sample_texture(uv)
        return color
    
    # Priority 2: Vertex colors
    if mesh_data.vertex_colors is not None:
        c0 = mesh_data.vertex_colors[face[0]]
        c1 = mesh_data.vertex_colors[face[1]]
        c2 = mesh_data.vertex_colors[face[2]]
        
        # Interpolate vertex colors
        color = c0 * w0 + c1 * w1 + c2 * w2
        return np.clip(color, 0.0, 1.0).astype(np.float32)
    
    # Priority 3: Face colors
    if mesh_data.face_colors is not None and triangle_index < len(mesh_data.face_colors):
        return mesh_data.face_colors[triangle_index].astype(np.float32)
    
    # Fallback: Gray color
    return np.array([0.5, 0.5, 0.5, 1.0], dtype=np.float32)


def voxelize_file(
    file_path: str,
    target_size: int = 80,
    constraint_axis: str = 'y',
    overlap_rule: str = 'average',
    normalize_position: bool = True,
    progress_callback: Optional[callable] = None
) -> VoxelMesh:
    """
    Convenience function to voxelize a mesh file directly.
    
    Args:
        file_path: Path to the 3D model file
        target_size: Size along the constraint axis
        constraint_axis: Which axis to constrain ('x', 'y', or 'z')
        overlap_rule: How to handle overlapping voxels
        normalize_position: If True, move mesh to positive quadrant
        progress_callback: Optional progress callback
        
    Returns:
        VoxelMesh containing all voxels
    """
    mesh = load_mesh(file_path)
    return voxelize_mesh(
        mesh,
        target_size=target_size,
        constraint_axis=constraint_axis,
        overlap_rule=overlap_rule,
        normalize_position=normalize_position,
        progress_callback=progress_callback
    )
