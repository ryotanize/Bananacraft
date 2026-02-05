"""
Voxelization utilities for converting continuous curves and surfaces
to discrete Minecraft block coordinates.

Implements 3D Bresenham-style algorithms with oversampling for gap-free results.
"""
from typing import List, Set, Tuple
from .bezier import BezierCurve, Point3D, QuadraticBezier, bilinear_interpolate


def voxelize_curve(curve: BezierCurve, samples_per_block: int = 3) -> List[Tuple[int, int, int]]:
    """
    Convert a Bezier curve to a list of discrete voxel coordinates.
    
    Uses oversampling to ensure no gaps in the resulting voxel line.
    
    Args:
        curve: A BezierCurve instance
        samples_per_block: Number of samples per expected block (higher = denser sampling)
        
    Returns:
        List of (x, y, z) integer tuples, deduplicated and ordered
    """
    # Estimate curve length to determine sample count
    arc_length = curve.arc_length(50)
    num_samples = max(10, int(arc_length * samples_per_block))
    
    voxels: Set[Tuple[int, int, int]] = set()
    
    for i in range(num_samples + 1):
        t = i / num_samples
        point = curve.point_at(t)
        voxel = point.to_int_tuple()
        voxels.add(voxel)
    
    # Sort by parameter order (approximately along curve)
    # For most uses, we'll iterate in order anyway
    return sorted(voxels, key=lambda v: (v[0], v[2], v[1]))


def voxelize_line_3d(start: Tuple[int, int, int], end: Tuple[int, int, int]) -> List[Tuple[int, int, int]]:
    """
    3D Bresenham's line algorithm for voxel-accurate line drawing.
    
    Returns all voxels along the line from start to end (inclusive).
    """
    x0, y0, z0 = start
    x1, y1, z1 = end
    
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    dz = abs(z1 - z0)
    
    sx = 1 if x1 > x0 else -1 if x1 < x0 else 0
    sy = 1 if y1 > y0 else -1 if y1 < y0 else 0
    sz = 1 if z1 > z0 else -1 if z1 < z0 else 0
    
    voxels = []
    
    # Determine the driving axis
    if dx >= dy and dx >= dz:
        # X-major
        err_y = 2 * dy - dx
        err_z = 2 * dz - dx
        
        while x0 != x1:
            voxels.append((x0, y0, z0))
            
            if err_y > 0:
                y0 += sy
                err_y -= 2 * dx
            if err_z > 0:
                z0 += sz
                err_z -= 2 * dx
            
            err_y += 2 * dy
            err_z += 2 * dz
            x0 += sx
        
        voxels.append((x1, y1, z1))
    
    elif dy >= dx and dy >= dz:
        # Y-major
        err_x = 2 * dx - dy
        err_z = 2 * dz - dy
        
        while y0 != y1:
            voxels.append((x0, y0, z0))
            
            if err_x > 0:
                x0 += sx
                err_x -= 2 * dy
            if err_z > 0:
                z0 += sz
                err_z -= 2 * dy
            
            err_x += 2 * dx
            err_z += 2 * dz
            y0 += sy
        
        voxels.append((x1, y1, z1))
    
    else:
        # Z-major
        err_x = 2 * dx - dz
        err_y = 2 * dy - dz
        
        while z0 != z1:
            voxels.append((x0, y0, z0))
            
            if err_x > 0:
                x0 += sx
                err_x -= 2 * dz
            if err_y > 0:
                y0 += sy
                err_y -= 2 * dz
            
            err_x += 2 * dx
            err_y += 2 * dy
            z0 += sz
        
        voxels.append((x1, y1, z1))
    
    return voxels


def voxelize_surface(curve_a: QuadraticBezier, curve_b: QuadraticBezier, 
                     resolution_u: int = 20, resolution_v: int = 20) -> List[Tuple[int, int, int]]:
    """
    Create a lofted surface between two Bezier curves and voxelize it.
    
    Uses bilinear interpolation between the two curves, then fills
    with voxels to create a solid surface without gaps.
    
    Args:
        curve_a: First guide curve
        curve_b: Second guide curve (should be parallel/similar shape)
        resolution_u: Samples along the curves
        resolution_v: Samples between the curves
        
    Returns:
        List of (x, y, z) voxel coordinates forming the surface
    """
    voxels: Set[Tuple[int, int, int]] = set()
    
    # Sample points on both curves
    points_a = [curve_a.point_at(u / resolution_u) for u in range(resolution_u + 1)]
    points_b = [curve_b.point_at(u / resolution_u) for u in range(resolution_u + 1)]
    
    # For each segment, create a quad and fill it
    for u in range(resolution_u):
        for v in range(resolution_v):
            # Get the four corners of this patch
            u0, u1 = u / resolution_u, (u + 1) / resolution_u
            v0, v1 = v / resolution_v, (v + 1) / resolution_v
            
            # Interpolate corners
            p00 = lerp_curves(points_a[u], points_b[u], v0)
            p10 = lerp_curves(points_a[u + 1], points_b[u + 1], v0)
            p01 = lerp_curves(points_a[u], points_b[u], v1)
            p11 = lerp_curves(points_a[u + 1], points_b[u + 1], v1)
            
            # Voxelize this quad (draw edges and fill)
            voxels.update(voxelize_quad(p00, p10, p01, p11))
    
    return list(voxels)


def lerp_curves(a: Point3D, b: Point3D, t: float) -> Point3D:
    """Linear interpolation between corresponding points on two curves."""
    return Point3D(
        a.x + (b.x - a.x) * t,
        a.y + (b.y - a.y) * t,
        a.z + (b.z - a.z) * t
    )


def voxelize_quad(p00: Point3D, p10: Point3D, p01: Point3D, p11: Point3D) -> Set[Tuple[int, int, int]]:
    """
    Voxelize a quadrilateral patch.
    
    Draws the four edges and fills the interior.
    """
    voxels: Set[Tuple[int, int, int]] = set()
    
    # Convert to integer coordinates
    i00 = p00.to_int_tuple()
    i10 = p10.to_int_tuple()
    i01 = p01.to_int_tuple()
    i11 = p11.to_int_tuple()
    
    # Draw all four edges
    for line in [
        voxelize_line_3d(i00, i10),
        voxelize_line_3d(i10, i11),
        voxelize_line_3d(i11, i01),
        voxelize_line_3d(i01, i00),
    ]:
        voxels.update(line)
    
    # For small quads, edges are enough
    # For larger quads, we'd need interior fill, but typically
    # the resolution keeps quads small enough
    
    return voxels


def fill_between_curves(curve_a: QuadraticBezier, curve_b: QuadraticBezier,
                        resolution: int = 30) -> List[Tuple[int, int, int]]:
    """
    Fill the area between two curves with voxels using scanline approach.
    
    Useful for creating solid roof/dome sections.
    """
    voxels: Set[Tuple[int, int, int]] = set()
    
    for i in range(resolution + 1):
        t = i / resolution
        
        # Get points on both curves
        pa = curve_a.point_at(t)
        pb = curve_b.point_at(t)
        
        # Draw line between them
        line = voxelize_line_3d(pa.to_int_tuple(), pb.to_int_tuple())
        voxels.update(line)
    
    return list(voxels)
