"""
VoxelMesh - Data structure for storing voxels with colors
"""
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from enum import IntFlag


class FaceVisibility(IntFlag):
    """Bit flags for which faces of a voxel are visible"""
    NONE = 0
    UP = 1 << 0
    DOWN = 1 << 1
    NORTH = 1 << 2  # +X
    EAST = 1 << 3   # +Z
    SOUTH = 1 << 4  # -X
    WEST = 1 << 5   # -Z
    ALL = UP | DOWN | NORTH | EAST | SOUTH | WEST


@dataclass
class Voxel:
    """A single voxel with position, color, and surface normal"""
    position: tuple[int, int, int]
    color: np.ndarray  # RGBA float [0, 1]
    collisions: int = 1  # Number of ray hits (for averaging)
    normal: Optional[np.ndarray] = None  # Surface normal vector


@dataclass
class VoxelMesh:
    """
    Container for a collection of voxels.
    Uses a dictionary for O(1) lookup by position.
    """
    voxels: dict[tuple[int, int, int], Voxel] = field(default_factory=dict)
    overlap_rule: str = 'average'  # 'first' or 'average'
    
    def add_voxel(self, position: np.ndarray, color: np.ndarray, normal: Optional[np.ndarray] = None) -> None:
        """
        Add a voxel at the given position with the given color.
        Handles overlap according to overlap_rule.
        
        Args:
            position: (x, y, z) position in voxel space
            color: RGBA color as float array [0, 1]
            normal: Optional surface normal vector (currently unused for performance)
        """
        # Skip fully transparent voxels
        if color[3] <= 0:
            return
        
        # Round position to integer voxel coordinates
        pos = tuple(int(round(p)) for p in position)
        
        if pos in self.voxels:
            if self.overlap_rule == 'average':
                existing = self.voxels[pos]
                n = existing.collisions
                # Rolling average for color
                existing.color = (existing.color * n + color) / (n + 1)
                existing.collisions = n + 1
            # 'first' rule: keep existing voxel
        else:
            self.voxels[pos] = Voxel(
                position=pos,
                color=color.copy(),
                collisions=1
            )
    
    def is_voxel_at(self, position: tuple[int, int, int]) -> bool:
        """Check if a voxel exists at the given position"""
        return position in self.voxels
    
    def is_opaque_voxel_at(self, position: tuple[int, int, int]) -> bool:
        """Check if an opaque voxel exists at the given position"""
        voxel = self.voxels.get(position)
        return voxel is not None and voxel.color[3] >= 1.0
    
    def get_face_visibility(self, position: tuple[int, int, int]) -> FaceVisibility:
        """
        Calculate which faces of a voxel are visible (not blocked by opaque neighbors).
        """
        x, y, z = position
        visibility = FaceVisibility.NONE
        
        if not self.is_opaque_voxel_at((x, y + 1, z)):
            visibility |= FaceVisibility.UP
        if not self.is_opaque_voxel_at((x, y - 1, z)):
            visibility |= FaceVisibility.DOWN
        if not self.is_opaque_voxel_at((x + 1, y, z)):
            visibility |= FaceVisibility.NORTH
        if not self.is_opaque_voxel_at((x - 1, y, z)):
            visibility |= FaceVisibility.SOUTH
        if not self.is_opaque_voxel_at((x, y, z + 1)):
            visibility |= FaceVisibility.EAST
        if not self.is_opaque_voxel_at((x, y, z - 1)):
            visibility |= FaceVisibility.WEST
        
        return visibility
    
    @property
    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        """Return (min, max) bounds of all voxels"""
        if not self.voxels:
            return np.array([0, 0, 0]), np.array([0, 0, 0])
        
        positions = np.array([v.position for v in self.voxels.values()])
        return positions.min(axis=0), positions.max(axis=0)
    
    @property
    def dimensions(self) -> np.ndarray:
        """Return dimensions of the voxel bounds"""
        min_b, max_b = self.bounds
        return max_b - min_b + 1  # +1 because voxels are discrete
    
    def get_voxel_count(self) -> int:
        """Return the number of voxels"""
        return len(self.voxels)
    
    def get_all_voxels(self) -> list[Voxel]:
        """Return all voxels as a list"""
        return list(self.voxels.values())
