"""
Voxelizer Comparison Tool
Compare the legacy surface-sampling voxelizer with the new BVH ray-cast voxelizer.
Generates visualizations and statistics for comparison.
"""
import json
import time
import numpy as np
from pathlib import Path
from collections import Counter
from typing import Optional
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D


def compare_voxelizers(
    model_path: str,
    target_size: int = 40,
    output_dir: Optional[str] = None
) -> dict:
    """
    Run both voxelizers on the same model and compare results.
    
    Args:
        model_path: Path to 3D model file
        target_size: Target voxel size
        output_dir: Directory to save comparison outputs
        
    Returns:
        Dictionary with comparison statistics
    """
    # Import both voxelizers
    # Legacy voxelizer is in voxelizer.py (module), new one is in voxelizer/ (package)
    import importlib.util
    spec = importlib.util.spec_from_file_location("legacy_voxelizer", 
                                                    Path(__file__).parent / "voxelizer.py")
    legacy_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy_module)
    LegacyVoxelizer = legacy_module.Voxelizer
    
    from app.voxelizer.mesh_loader import load_mesh
    from app.voxelizer.bvh_ray_voxelizer import voxelize_mesh
    from app.voxelizer.block_assigner import BlockAssigner
    
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    results = {}
    
    # ========== Legacy Voxelizer ==========
    print("=" * 60)
    print("Running LEGACY Voxelizer (Surface Point Sampling)...")
    print("=" * 60)
    
    start = time.time()
    legacy = LegacyVoxelizer()
    legacy_blocks = legacy.voxelize(model_path, target_size, target_size)
    legacy_time = time.time() - start
    
    # Convert to position: block format
    legacy_positions = {(b['x'], b['y'], b['z']): b['type'] for b in legacy_blocks}
    
    results['legacy'] = {
        'time': legacy_time,
        'block_count': len(legacy_blocks),
        'positions': legacy_positions,
        'block_distribution': dict(Counter(b['type'] for b in legacy_blocks))
    }
    print(f"Legacy: {len(legacy_blocks)} blocks in {legacy_time:.2f}s")
    
    # ========== New BVH Voxelizer ==========
    print("\n" + "=" * 60)
    print("Running NEW Voxelizer (BVH Ray Casting)...")
    print("=" * 60)
    
    start = time.time()
    mesh = load_mesh(model_path)
    voxel_mesh = voxelize_mesh(mesh, target_size=target_size, constraint_axis='y')
    assigner = BlockAssigner()
    new_blocks = assigner.assign_blocks(voxel_mesh, dithering='ordered')
    new_time = time.time() - start
    
    # Convert to position: block format
    new_positions = {b.position: b.block_name for b in new_blocks}
    
    results['new'] = {
        'time': new_time,
        'block_count': len(new_blocks),
        'positions': new_positions,
        'block_distribution': dict(Counter(b.block_name for b in new_blocks))
    }
    print(f"New: {len(new_blocks)} blocks in {new_time:.2f}s")
    
    # ========== Comparison Statistics ==========
    print("\n" + "=" * 60)
    print("COMPARISON STATISTICS")
    print("=" * 60)
    
    # Positions comparison
    legacy_pos_set = set(legacy_positions.keys())
    new_pos_set = set(new_positions.keys())
    
    shared_positions = legacy_pos_set & new_pos_set
    only_legacy = legacy_pos_set - new_pos_set
    only_new = new_pos_set - legacy_pos_set
    
    # Block type matches at shared positions
    matching_blocks = sum(1 for pos in shared_positions 
                         if legacy_positions[pos] == new_positions[pos])
    
    results['comparison'] = {
        'shared_voxels': len(shared_positions),
        'only_in_legacy': len(only_legacy),
        'only_in_new': len(only_new),
        'matching_block_types': matching_blocks,
        'match_rate': matching_blocks / len(shared_positions) if shared_positions else 0,
        'overlap_jaccard': len(shared_positions) / len(legacy_pos_set | new_pos_set)
    }
    
    print(f"\nVoxel Coverage:")
    print(f"  Legacy-only voxels: {len(only_legacy)}")
    print(f"  New-only voxels: {len(only_new)}")
    print(f"  Shared voxels: {len(shared_positions)}")
    print(f"  Jaccard similarity: {results['comparison']['overlap_jaccard']:.2%}")
    
    print(f"\nBlock Type Matching (at shared positions):")
    print(f"  Matching blocks: {matching_blocks}/{len(shared_positions)}")
    print(f"  Match rate: {results['comparison']['match_rate']:.2%}")
    
    print(f"\nPerformance:")
    print(f"  Legacy time: {legacy_time:.2f}s")
    print(f"  New time: {new_time:.2f}s")
    print(f"  Speedup: {legacy_time/new_time:.1f}x" if new_time > 0 else "N/A")
    
    # ========== Generate Visualizations ==========
    if output_dir:
        print("\nGenerating visualizations...")
        
        # 3D scatter plot comparison
        fig = plt.figure(figsize=(16, 6))
        
        # Legacy voxels
        ax1 = fig.add_subplot(131, projection='3d')
        if legacy_positions:
            legacy_arr = np.array(list(legacy_positions.keys()))
            ax1.scatter(legacy_arr[:, 0], legacy_arr[:, 2], legacy_arr[:, 1], 
                       c='blue', alpha=0.3, s=1)
        ax1.set_title(f'Legacy ({len(legacy_positions)} voxels)')
        ax1.set_xlabel('X')
        ax1.set_ylabel('Z')
        ax1.set_zlabel('Y')
        
        # New voxels
        ax2 = fig.add_subplot(132, projection='3d')
        if new_positions:
            new_arr = np.array(list(new_positions.keys()))
            ax2.scatter(new_arr[:, 0], new_arr[:, 2], new_arr[:, 1], 
                       c='red', alpha=0.3, s=1)
        ax2.set_title(f'New BVH ({len(new_positions)} voxels)')
        ax2.set_xlabel('X')
        ax2.set_ylabel('Z')
        ax2.set_zlabel('Y')
        
        # Difference visualization
        ax3 = fig.add_subplot(133, projection='3d')
        if only_legacy:
            only_legacy_arr = np.array(list(only_legacy))
            ax3.scatter(only_legacy_arr[:, 0], only_legacy_arr[:, 2], only_legacy_arr[:, 1], 
                       c='blue', alpha=0.5, s=2, label='Legacy only')
        if only_new:
            only_new_arr = np.array(list(only_new))
            ax3.scatter(only_new_arr[:, 0], only_new_arr[:, 2], only_new_arr[:, 1], 
                       c='red', alpha=0.5, s=2, label='New only')
        ax3.set_title('Differences')
        ax3.set_xlabel('X')
        ax3.set_ylabel('Z')
        ax3.set_zlabel('Y')
        ax3.legend()
        
        plt.tight_layout()
        plt.savefig(output_dir / 'voxel_comparison_3d.png', dpi=150)
        print(f"  Saved: {output_dir / 'voxel_comparison_3d.png'}")
        
        # Block distribution comparison
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Top 10 blocks for each
        legacy_dist = results['legacy']['block_distribution']
        new_dist = results['new']['block_distribution']
        
        top_legacy = sorted(legacy_dist.items(), key=lambda x: -x[1])[:10]
        top_new = sorted(new_dist.items(), key=lambda x: -x[1])[:10]
        
        if top_legacy:
            blocks, counts = zip(*top_legacy)
            short_names = [b.replace('minecraft:', '') for b in blocks]
            ax1.barh(short_names, counts, color='blue', alpha=0.7)
            ax1.set_title('Legacy: Top 10 Blocks')
            ax1.set_xlabel('Count')
            ax1.invert_yaxis()
        
        if top_new:
            blocks, counts = zip(*top_new)
            short_names = [b.replace('minecraft:', '') for b in blocks]
            ax2.barh(short_names, counts, color='red', alpha=0.7)
            ax2.set_title('New BVH: Top 10 Blocks')
            ax2.set_xlabel('Count')
            ax2.invert_yaxis()
        
        plt.tight_layout()
        plt.savefig(output_dir / 'block_distribution.png', dpi=150)
        print(f"  Saved: {output_dir / 'block_distribution.png'}")
        
        # Y-slice comparison (bird's eye views at different heights)
        fig, axes = plt.subplots(2, 5, figsize=(20, 8))
        
        if legacy_positions and new_positions:
            legacy_arr = np.array(list(legacy_positions.keys()))
            new_arr = np.array(list(new_positions.keys()))
            
            # Get Y range
            min_y = min(legacy_arr[:, 1].min() if len(legacy_arr) else 0, 
                       new_arr[:, 1].min() if len(new_arr) else 0)
            max_y = max(legacy_arr[:, 1].max() if len(legacy_arr) else 0, 
                       new_arr[:, 1].max() if len(new_arr) else 0)
            
            y_slices = np.linspace(min_y, max_y, 5).astype(int)
            
            for i, y in enumerate(y_slices):
                # Legacy slice
                mask_l = legacy_arr[:, 1] == y
                if mask_l.any():
                    axes[0, i].scatter(legacy_arr[mask_l, 0], legacy_arr[mask_l, 2], 
                                       s=10, c='blue', alpha=0.7)
                axes[0, i].set_title(f'Legacy Y={y}')
                axes[0, i].set_aspect('equal')
                
                # New slice
                mask_n = new_arr[:, 1] == y
                if mask_n.any():
                    axes[1, i].scatter(new_arr[mask_n, 0], new_arr[mask_n, 2], 
                                       s=10, c='red', alpha=0.7)
                axes[1, i].set_title(f'New Y={y}')
                axes[1, i].set_aspect('equal')
        
        plt.suptitle('Y-Slice Comparison (Bird\'s Eye View)', fontsize=14)
        plt.tight_layout()
        plt.savefig(output_dir / 'y_slice_comparison.png', dpi=150)
        print(f"  Saved: {output_dir / 'y_slice_comparison.png'}")
        
        # Save JSON results
        # Convert sets to lists for JSON serialization
        json_results = {
            'legacy': {
                'time': results['legacy']['time'],
                'block_count': results['legacy']['block_count'],
                'block_distribution': results['legacy']['block_distribution']
            },
            'new': {
                'time': results['new']['time'],
                'block_count': results['new']['block_count'],
                'block_distribution': results['new']['block_distribution']
            },
            'comparison': results['comparison']
        }
        with open(output_dir / 'comparison_stats.json', 'w') as f:
            json.dump(json_results, f, indent=2)
        print(f"  Saved: {output_dir / 'comparison_stats.json'}")
        
        plt.close('all')
    
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m app.compare_voxelizers <model_path> [target_size] [output_dir]")
        print("\nExample:")
        print("  python -m app.compare_voxelizers model.glb 40 ./comparison_output")
        sys.exit(1)
    
    model_path = sys.argv[1]
    target_size = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "./voxelizer_comparison"
    
    print(f"Comparing voxelizers on: {model_path}")
    print(f"Target size: {target_size}")
    print(f"Output directory: {output_dir}")
    print()
    
    results = compare_voxelizers(model_path, target_size, output_dir)
    
    print("\n" + "=" * 60)
    print("Comparison complete! Check the output directory for visualizations.")
    print("=" * 60)
