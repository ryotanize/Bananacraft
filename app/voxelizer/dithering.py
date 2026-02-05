"""
Dithering - Ordered and random dithering for color quantization
"""
import numpy as np
from typing import Literal


# Bayer matrix for ordered dithering (8x8)
BAYER_MATRIX_8x8 = np.array([
    [ 0, 32,  8, 40,  2, 34, 10, 42],
    [48, 16, 56, 24, 50, 18, 58, 26],
    [12, 44,  4, 36, 14, 46,  6, 38],
    [60, 28, 52, 20, 62, 30, 54, 22],
    [ 3, 35, 11, 43,  1, 33,  9, 41],
    [51, 19, 59, 27, 49, 17, 57, 25],
    [15, 47,  7, 39, 13, 45,  5, 37],
    [63, 31, 55, 23, 61, 29, 53, 21]
], dtype=np.float32) / 64.0 - 0.5  # Normalize to [-0.5, 0.5)


def apply_ordered_dithering(
    color: np.ndarray,
    position: tuple[int, int, int],
    magnitude: float = 32.0
) -> np.ndarray:
    """
    Apply ordered dithering to a color based on position.
    
    Args:
        color: RGBA color as float array [0, 255]
        position: (x, y, z) voxel position
        magnitude: Dithering strength (default 32)
        
    Returns:
        Dithered color as RGBA [0, 255]
    """
    x, y, z = position
    
    # Use position to index into Bayer matrix
    bayer_x = (x + z) % 8
    bayer_y = y % 8
    threshold = BAYER_MATRIX_8x8[bayer_y, bayer_x]
    
    # Apply dithering to RGB channels
    dithered = color.copy()
    dithered[:3] = dithered[:3] + threshold * magnitude
    
    # Clamp to valid range
    return np.clip(dithered, 0, 255)


def apply_random_dithering(
    color: np.ndarray,
    magnitude: float = 32.0
) -> np.ndarray:
    """
    Apply random dithering to a color.
    
    Args:
        color: RGBA color as float array [0, 255]
        magnitude: Dithering strength (default 32)
        
    Returns:
        Dithered color as RGBA [0, 255]
    """
    # Random offset for RGB channels
    offset = (np.random.random(3) - 0.5) * magnitude
    
    dithered = color.copy()
    dithered[:3] = dithered[:3] + offset
    
    # Clamp to valid range
    return np.clip(dithered, 0, 255)


def bin_color(color: np.ndarray, resolution: int = 32) -> np.ndarray:
    """
    Bin a color to reduce precision (color quantization).
    
    Args:
        color: RGBA color as float array [0, 1]
        resolution: Number of bins per channel (default 32)
        
    Returns:
        Binned color as RGBA [0, 1]
    """
    # Convert to [0, resolution] range, floor, and convert back
    binned = np.floor(color * resolution) / resolution
    return np.clip(binned, 0.0, 1.0)


def apply_dithering(
    color_255: np.ndarray,
    position: tuple[int, int, int],
    dithering_type: Literal['off', 'ordered', 'random'] = 'ordered',
    magnitude: float = 32.0
) -> np.ndarray:
    """
    Apply dithering to a color.
    
    Args:
        color_255: RGBA color as [0, 255]
        position: Voxel position (used for ordered dithering)
        dithering_type: Type of dithering to apply
        magnitude: Dithering strength
        
    Returns:
        Dithered color as RGBA [0, 255]
    """
    if dithering_type == 'off':
        return color_255.copy()
    elif dithering_type == 'ordered':
        return apply_ordered_dithering(color_255, position, magnitude)
    elif dithering_type == 'random':
        return apply_random_dithering(color_255, magnitude)
    else:
        return color_255.copy()
