"""
Bezier curve utilities for smooth architectural curves.

Supports quadratic and cubic Bezier curves with tangent calculation
for discrete smoothing (stairs/slabs placement).
"""
import math
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class Point3D:
    """A point in 3D space."""
    x: float
    y: float
    z: float
    
    def __add__(self, other: 'Point3D') -> 'Point3D':
        return Point3D(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: 'Point3D') -> 'Point3D':
        return Point3D(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar: float) -> 'Point3D':
        return Point3D(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def __rmul__(self, scalar: float) -> 'Point3D':
        return self.__mul__(scalar)
    
    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)
    
    def to_int_tuple(self) -> Tuple[int, int, int]:
        return (round(self.x), round(self.y), round(self.z))
    
    def distance_to(self, other: 'Point3D') -> float:
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2 +
            (self.z - other.z) ** 2
        )
    
    @staticmethod
    def from_list(coords: List[int]) -> 'Point3D':
        """Create Point3D from [x, y, z] list."""
        return Point3D(float(coords[0]), float(coords[1]), float(coords[2]))


class BezierCurve:
    """Base class for Bezier curves."""
    
    def point_at(self, t: float) -> Point3D:
        """Get point on curve at parameter t (0 to 1)."""
        raise NotImplementedError
    
    def tangent_at(self, t: float) -> Point3D:
        """Get tangent vector at parameter t."""
        raise NotImplementedError
    
    def sample_points(self, num_samples: int = 50) -> List[Point3D]:
        """Sample points along the curve."""
        return [self.point_at(t / (num_samples - 1)) for t in range(num_samples)]


class QuadraticBezier(BezierCurve):
    """
    Quadratic Bezier curve: B(t) = (1-t)²P₀ + 2(1-t)tP₁ + t²P₂
    
    Used for smooth arches and curves in architecture.
    """
    
    def __init__(self, p0: Point3D, p1: Point3D, p2: Point3D):
        """
        Args:
            p0: Start point
            p1: Control point (determines curve shape)
            p2: End point
        """
        self.p0 = p0
        self.p1 = p1
        self.p2 = p2
    
    @classmethod
    def from_arch(cls, start: List[int], end: List[int], control_height: int) -> 'QuadraticBezier':
        """
        Create an arch-shaped curve from start to end with given apex height.
        
        The control point is placed at the midpoint x/z with elevated y.
        
        Args:
            start: [x, y, z] start point
            end: [x, y, z] end point  
            control_height: Height of the control point above base
        """
        p0 = Point3D.from_list(start)
        p2 = Point3D.from_list(end)
        
        # Control point at midpoint with elevated Y
        mid_x = (p0.x + p2.x) / 2
        mid_z = (p0.z + p2.z) / 2
        base_y = (p0.y + p2.y) / 2
        
        p1 = Point3D(mid_x, base_y + control_height, mid_z)
        
        return cls(p0, p1, p2)
    
    def point_at(self, t: float) -> Point3D:
        """
        Calculate point at parameter t.
        
        B(t) = (1-t)²P₀ + 2(1-t)tP₁ + t²P₂
        """
        t = max(0.0, min(1.0, t))  # Clamp to [0, 1]
        
        mt = 1.0 - t  # (1 - t)
        mt2 = mt * mt  # (1 - t)²
        t2 = t * t     # t²
        
        # Weighted sum
        x = mt2 * self.p0.x + 2 * mt * t * self.p1.x + t2 * self.p2.x
        y = mt2 * self.p0.y + 2 * mt * t * self.p1.y + t2 * self.p2.y
        z = mt2 * self.p0.z + 2 * mt * t * self.p1.z + t2 * self.p2.z
        
        return Point3D(x, y, z)
    
    def tangent_at(self, t: float) -> Point3D:
        """
        Calculate tangent vector at parameter t.
        
        B'(t) = 2(1-t)(P₁-P₀) + 2t(P₂-P₁)
        
        Returns normalized tangent vector.
        """
        t = max(0.0, min(1.0, t))
        mt = 1.0 - t
        
        # Derivative
        dx = 2 * mt * (self.p1.x - self.p0.x) + 2 * t * (self.p2.x - self.p1.x)
        dy = 2 * mt * (self.p1.y - self.p0.y) + 2 * t * (self.p2.y - self.p1.y)
        dz = 2 * mt * (self.p1.z - self.p0.z) + 2 * t * (self.p2.z - self.p1.z)
        
        # Normalize
        length = math.sqrt(dx*dx + dy*dy + dz*dz)
        if length < 1e-6:
            return Point3D(0, 0, 0)
        
        return Point3D(dx / length, dy / length, dz / length)
    
    def slope_at(self, t: float) -> float:
        """
        Calculate the vertical slope (dy/dh where h is horizontal distance).
        Used for determining stair/slab placement.
        
        Returns: slope angle in degrees
        """
        tangent = self.tangent_at(t)
        horizontal = math.sqrt(tangent.x ** 2 + tangent.z ** 2)
        
        if horizontal < 1e-6:
            return 90.0 if tangent.y > 0 else -90.0
        
        return math.degrees(math.atan2(tangent.y, horizontal))
    
    def arc_length(self, num_samples: int = 100) -> float:
        """Approximate arc length by sampling."""
        total = 0.0
        prev = self.point_at(0)
        
        for i in range(1, num_samples + 1):
            t = i / num_samples
            curr = self.point_at(t)
            total += prev.distance_to(curr)
            prev = curr
        
        return total


class CubicBezier(BezierCurve):
    """
    Cubic Bezier curve: B(t) = (1-t)³P₀ + 3(1-t)²tP₁ + 3(1-t)t²P₂ + t³P₃
    
    More flexible than quadratic, allows S-curves and complex shapes.
    """
    
    def __init__(self, p0: Point3D, p1: Point3D, p2: Point3D, p3: Point3D):
        self.p0 = p0
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
    
    def point_at(self, t: float) -> Point3D:
        t = max(0.0, min(1.0, t))
        
        mt = 1.0 - t
        mt2 = mt * mt
        mt3 = mt2 * mt
        t2 = t * t
        t3 = t2 * t
        
        x = mt3 * self.p0.x + 3 * mt2 * t * self.p1.x + 3 * mt * t2 * self.p2.x + t3 * self.p3.x
        y = mt3 * self.p0.y + 3 * mt2 * t * self.p1.y + 3 * mt * t2 * self.p2.y + t3 * self.p3.y
        z = mt3 * self.p0.z + 3 * mt2 * t * self.p1.z + 3 * mt * t2 * self.p2.z + t3 * self.p3.z
        
        return Point3D(x, y, z)
    
    def tangent_at(self, t: float) -> Point3D:
        t = max(0.0, min(1.0, t))
        mt = 1.0 - t
        
        # B'(t) = 3(1-t)²(P₁-P₀) + 6(1-t)t(P₂-P₁) + 3t²(P₃-P₂)
        c0 = 3 * mt * mt
        c1 = 6 * mt * t
        c2 = 3 * t * t
        
        dx = c0 * (self.p1.x - self.p0.x) + c1 * (self.p2.x - self.p1.x) + c2 * (self.p3.x - self.p2.x)
        dy = c0 * (self.p1.y - self.p0.y) + c1 * (self.p2.y - self.p1.y) + c2 * (self.p3.y - self.p2.y)
        dz = c0 * (self.p1.z - self.p0.z) + c1 * (self.p2.z - self.p1.z) + c2 * (self.p3.z - self.p2.z)
        
        length = math.sqrt(dx*dx + dy*dy + dz*dz)
        if length < 1e-6:
            return Point3D(0, 0, 0)
        
        return Point3D(dx / length, dy / length, dz / length)


def lerp_point(a: Point3D, b: Point3D, t: float) -> Point3D:
    """Linear interpolation between two points."""
    return a * (1 - t) + b * t


def bilinear_interpolate(p00: Point3D, p10: Point3D, p01: Point3D, p11: Point3D, 
                         u: float, v: float) -> Point3D:
    """
    Bilinear interpolation on a surface patch.
    
    Args:
        p00, p10, p01, p11: Four corner points
        u, v: Parameters in [0, 1]
    """
    # Interpolate along u first
    p0 = lerp_point(p00, p10, u)
    p1 = lerp_point(p01, p11, u)
    
    # Then along v
    return lerp_point(p0, p1, v)
