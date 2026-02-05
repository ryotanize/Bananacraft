"""
Geometry utilities for Bananacraft 2.0

Handles Bezier curves, voxelization, and discrete smoothing.
"""
from .bezier import BezierCurve, QuadraticBezier
from .voxelize import voxelize_curve, voxelize_surface
from .stairs_solver import StairsSolver

__all__ = [
    "BezierCurve", "QuadraticBezier",
    "voxelize_curve", "voxelize_surface",
    "StairsSolver"
]
