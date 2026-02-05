"""
Advanced Voxelizer - High-fidelity mesh to Minecraft block conversion
Based on ObjToSchematic algorithms, implemented in pure Python
"""
import json
import time
from pathlib import Path
from typing import Optional, Literal
from dataclasses import dataclass, asdict

from .voxelizer.mesh_loader import load_mesh
from .voxelizer.bvh_ray_voxelizer import voxelize_mesh, voxelize_file
from .voxelizer.block_assigner import BlockAssigner, BlockAtlas, AssignedBlock
from .voxelizer.voxel_mesh import VoxelMesh


@dataclass
class VoxelizerConfig:
    """Configuration for the voxelizer"""
    # Voxelization settings
    target_size: int = 80
    constraint_axis: str = 'y'
    overlap_rule: str = 'average'
    
    # Block assignment settings
    dithering: Literal['off', 'ordered', 'random'] = 'ordered'
    dithering_magnitude: float = 32.0
    resolution: int = 32
    use_contextual: bool = True
    error_weight: float = 0.0
    
    # Palette
    palette: Optional[list[str]] = None


def voxelize_and_assign(
    input_path: str | Path,
    config: Optional[VoxelizerConfig] = None,
    progress_callback: Optional[callable] = None
) -> list[AssignedBlock]:
    """
    Voxelize a 3D model and assign Minecraft blocks to each voxel.
    
    Args:
        input_path: Path to 3D model file (GLB, OBJ, etc.)
        config: Voxelization configuration, or None for defaults
        progress_callback: Optional callback(stage: str, progress: float)
        
    Returns:
        List of AssignedBlock objects with position and block name
    """
    config = config or VoxelizerConfig()
    
    def report_progress(stage: str):
        def inner(progress: float):
            if progress_callback:
                progress_callback(stage, progress)
        return inner
    
    # Load mesh
    print(f"Loading mesh from {input_path}...")
    start = time.time()
    mesh = load_mesh(input_path)
    print(f"  Loaded {len(mesh.vertices)} vertices, {len(mesh.faces)} faces in {time.time()-start:.2f}s")
    
    # Voxelize
    print(f"Voxelizing (target size: {config.target_size})...")
    start = time.time()
    voxel_mesh = voxelize_mesh(
        mesh,
        target_size=config.target_size,
        constraint_axis=config.constraint_axis,
        overlap_rule=config.overlap_rule,
        progress_callback=report_progress("voxelizing")
    )
    print(f"  Created {voxel_mesh.get_voxel_count()} voxels in {time.time()-start:.2f}s")
    
    # Assign blocks
    print(f"Assigning blocks (dithering: {config.dithering})...")
    start = time.time()
    assigner = BlockAssigner(palette=config.palette)
    blocks = assigner.assign_blocks(
        voxel_mesh,
        dithering=config.dithering,
        dithering_magnitude=config.dithering_magnitude,
        resolution=config.resolution,
        use_contextual=config.use_contextual,
        error_weight=config.error_weight,
        progress_callback=report_progress("assigning")
    )
    print(f"  Assigned {len(blocks)} blocks in {time.time()-start:.2f}s")
    
    return blocks


def export_to_json(
    blocks: list[AssignedBlock],
    output_path: str | Path
) -> None:
    """
    Export assigned blocks to JSON format.
    
    Args:
        blocks: List of AssignedBlock objects
        output_path: Path to output JSON file
    """
    output_path = Path(output_path)
    
    # Create structure similar to ObjToSchematic output
    data = {
        "blocks": [
            {
                "position": {"x": b.position[0], "y": b.position[1], "z": b.position[2]},
                "block": b.block_name
            }
            for b in blocks
        ]
    }
    
    with open(output_path, 'w') as f:
        json.dump(data, f)
    
    print(f"Exported {len(blocks)} blocks to {output_path}")


def export_to_rcon_commands(
    blocks: list[AssignedBlock],
    offset: tuple[int, int, int] = (0, 0, 0)
) -> list[str]:
    """
    Generate RCON setblock commands for each block.
    
    Args:
        blocks: List of AssignedBlock objects
        offset: World offset (x, y, z) to add to each position
        
    Returns:
        List of setblock command strings
    """
    ox, oy, oz = offset
    commands = []
    
    for block in blocks:
        x = block.position[0] + ox
        y = block.position[1] + oy
        z = block.position[2] + oz
        commands.append(f"setblock {x} {y} {z} {block.block_name}")
    
    return commands


def get_block_palette_stats(blocks: list[AssignedBlock]) -> dict[str, int]:
    """
    Get statistics on which blocks were used.
    
    Args:
        blocks: List of AssignedBlock objects
        
    Returns:
        Dictionary of block name -> count
    """
    stats = {}
    for block in blocks:
        stats[block.block_name] = stats.get(block.block_name, 0) + 1
    return dict(sorted(stats.items(), key=lambda x: -x[1]))


# Main entry point for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m app.advanced_voxelizer <input_file> [target_size]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    target_size = int(sys.argv[2]) if len(sys.argv) > 2 else 80
    
    config = VoxelizerConfig(target_size=target_size)
    blocks = voxelize_and_assign(input_file, config)
    
    # Print stats
    print("\nBlock palette usage:")
    stats = get_block_palette_stats(blocks)
    for block, count in list(stats.items())[:10]:
        print(f"  {block}: {count}")
    if len(stats) > 10:
        print(f"  ... and {len(stats) - 10} more block types")
    
    # Export to JSON
    output_path = Path(input_file).with_suffix('.voxels.json')
    export_to_json(blocks, output_path)
