"""
Postprocessing - Quality improvement for voxelized blocks
"""
from collections import Counter
from typing import Optional


def denoise_blocks(
    blocks: list[dict],
    radius: int = 1,
    threshold: int = 3,
    iterations: int = 1
) -> list[dict]:
    """
    Remove noise by replacing isolated blocks with the majority block type in their neighborhood.
    
    Args:
        blocks: List of blocks [{'x': int, 'y': int, 'z': int, 'type': str}, ...]
        radius: Search radius (1 = 3x3x3 = 26 neighbors)
        threshold: If fewer than this many neighbors share the same type, replace
        iterations: Number of passes to run (more = smoother, but may lose detail)
        
    Returns:
        Denoised block list
    """
    if not blocks:
        return blocks
    
    # Create position -> block mapping for O(1) lookup
    pos_to_block = {(b['x'], b['y'], b['z']): b for b in blocks}
    pos_to_type = {(b['x'], b['y'], b['z']): b['type'] for b in blocks}
    
    result = list(blocks)  # Copy
    
    for iteration in range(iterations):
        changes = 0
        new_types = {}
        
        for pos, block_type in pos_to_type.items():
            x, y, z = pos
            
            # Count neighbor types
            neighbor_types = []
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    for dz in range(-radius, radius + 1):
                        if dx == 0 and dy == 0 and dz == 0:
                            continue  # Skip self
                        
                        neighbor_pos = (x + dx, y + dy, z + dz)
                        if neighbor_pos in pos_to_type:
                            neighbor_types.append(pos_to_type[neighbor_pos])
            
            if not neighbor_types:
                continue  # No neighbors, keep as is
            
            # Count same-type neighbors
            same_type_count = sum(1 for t in neighbor_types if t == block_type)
            
            # If isolated (too few same-type neighbors), replace with majority
            if same_type_count < threshold:
                type_counts = Counter(neighbor_types)
                majority_type = type_counts.most_common(1)[0][0]
                
                if majority_type != block_type:
                    new_types[pos] = majority_type
                    changes += 1
        
        # Apply changes
        for pos, new_type in new_types.items():
            pos_to_type[pos] = new_type
        
        if changes == 0:
            break  # No more changes needed
    
    # Build result
    result = []
    for pos, block_type in pos_to_type.items():
        result.append({
            'x': pos[0],
            'y': pos[1],
            'z': pos[2],
            'type': block_type
        })
    
    return result


def remove_isolated_blocks(
    blocks: list[dict],
    radius: int = 1,
    min_neighbors: int = 3
) -> list[dict]:
    """
    Remove spatially isolated blocks (noise/outliers) that have too few neighbors.
    
    Args:
        blocks: List of blocks [{'x': int, 'y': int, 'z': int, 'type': str}, ...]
        radius: Search radius for counting neighbors (1 = 3x3x3 = 26 possible neighbors)
        min_neighbors: Minimum number of neighbors required to keep a block
        
    Returns:
        Filtered block list with isolated blocks removed
    """
    if not blocks:
        return blocks
    
    # Create position set for O(1) lookup
    positions = {(b['x'], b['y'], b['z']) for b in blocks}
    
    result = []
    removed_count = 0
    
    for b in blocks:
        x, y, z = b['x'], b['y'], b['z']
        
        # Count neighbors
        neighbor_count = 0
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                for dz in range(-radius, radius + 1):
                    if dx == 0 and dy == 0 and dz == 0:
                        continue  # Skip self
                    
                    if (x + dx, y + dy, z + dz) in positions:
                        neighbor_count += 1
        
        # Keep only if has enough neighbors
        if neighbor_count >= min_neighbors:
            result.append(b)
        else:
            removed_count += 1
    
    if removed_count > 0:
        print(f"[Postprocess] Removed {removed_count} isolated blocks (min_neighbors={min_neighbors})")
    
    return result


def segment_by_clustering(
    blocks: list[dict],
    block_colors: dict[str, tuple[float, float, float]],
    eps: float = 3.0,
    min_samples: int = 5,
    coord_weight: float = 1.0,
    color_weight: float = 10.0
) -> list[dict]:
    """
    Segment blocks using DBSCAN clustering based on position and color.
    Each cluster's blocks are unified to the most common block type in that cluster.
    
    Args:
        blocks: List of blocks [{'x': int, 'y': int, 'z': int, 'type': str}, ...]
        block_colors: Dict mapping block name to RGB color (0-1 range)
        eps: DBSCAN epsilon (maximum distance between samples in a cluster)
        min_samples: Minimum samples required to form a cluster
        coord_weight: Weight for spatial coordinates in feature vector
        color_weight: Weight for color in feature vector
        
    Returns:
        Segmented block list with unified block types per cluster
    """
    import numpy as np
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler
    
    if len(blocks) < min_samples:
        return blocks
    
    print(f"[Segmentation] Starting DBSCAN clustering on {len(blocks)} blocks...")
    
    # Build feature vectors: [x, y, z, r, g, b]
    features = []
    for b in blocks:
        block_type = b['type']
        # Get color for this block type, default to gray
        color = block_colors.get(block_type, (0.5, 0.5, 0.5))
        
        features.append([
            b['x'] * coord_weight,
            b['y'] * coord_weight,
            b['z'] * coord_weight,
            color[0] * color_weight,
            color[1] * color_weight,
            color[2] * color_weight,
        ])
    
    features = np.array(features)
    
    # Normalize features
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)
    
    # Run DBSCAN
    print(f"[Segmentation] Running DBSCAN (eps={eps}, min_samples={min_samples})...")
    db = DBSCAN(eps=eps, min_samples=min_samples, n_jobs=-1)
    labels = db.fit_predict(features_scaled)
    
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    print(f"[Segmentation] Found {n_clusters} clusters, {n_noise} noise points")
    
    # For each cluster, find the most common block type and unify
    result = []
    cluster_types = {}
    
    for cluster_id in set(labels):
        if cluster_id == -1:
            continue  # Skip noise points for now
        
        # Get blocks in this cluster
        cluster_blocks = [blocks[i] for i in range(len(blocks)) if labels[i] == cluster_id]
        
        # Find most common type
        type_counts = Counter(b['type'] for b in cluster_blocks)
        dominant_type = type_counts.most_common(1)[0][0]
        cluster_types[cluster_id] = dominant_type
        
        # Unify all blocks to dominant type
        for b in cluster_blocks:
            result.append({
                'x': b['x'],
                'y': b['y'],
                'z': b['z'],
                'type': dominant_type
            })
    
    # Handle noise points (-1 label) - keep their original type
    for i, b in enumerate(blocks):
        if labels[i] == -1:
            result.append(b.copy())
    
    print(f"[Segmentation] Segmentation complete. Clusters: {len(cluster_types)}")
    
    return result


def get_block_colors_from_atlas(atlas_path: str = None) -> dict[str, tuple[float, float, float]]:
    """
    Load block colors from atlas file.
    Returns dict mapping block name to RGB color (0-1 range).
    """
    import json
    import os
    
    if atlas_path is None:
        # Default path relative to this file
        atlas_path = os.path.join(os.path.dirname(__file__), 'vanilla.atlas')
    
    if not os.path.exists(atlas_path):
        print(f"[Warning] Atlas not found at {atlas_path}, using empty colors")
        return {}
    
    with open(atlas_path, 'r') as f:
        atlas = json.load(f)
    
    colors = {}
    for block in atlas.get('blocks', []):
        name = block.get('name', '')
        color = block.get('colour', {})
        r = color.get('r', 0.5)
        g = color.get('g', 0.5)
        b = color.get('b', 0.5)
        colors[name] = (r, g, b)
    
    return colors


def fill_cluster_holes(
    blocks: list[dict],
    block_colors: dict[str, tuple[float, float, float]],
    eps: float = 0.7,
    min_samples: int = 5
) -> list[dict]:
    """
    Segment blocks into clusters and fill holes within each cluster.
    A "hole" is an empty voxel surrounded by cluster blocks on the same Y layer.
    
    Args:
        blocks: List of blocks [{'x': int, 'y': int, 'z': int, 'type': str}, ...]
        block_colors: Dict mapping block name to RGB color
        eps: DBSCAN epsilon
        min_samples: DBSCAN min_samples
        
    Returns:
        Block list with holes filled
    """
    import numpy as np
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler
    
    if len(blocks) < min_samples:
        return blocks
    
    print(f"[HoleFill] Starting hole filling on {len(blocks)} blocks...")
    
    # Build feature vectors: [x, y, z, r, g, b]
    features = []
    for b in blocks:
        block_type = b['type']
        color = block_colors.get(block_type, (0.5, 0.5, 0.5))
        features.append([
            b['x'], b['y'], b['z'],
            color[0] * 10, color[1] * 10, color[2] * 10,
        ])
    
    features = np.array(features)
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)
    
    # Run DBSCAN
    db = DBSCAN(eps=eps, min_samples=min_samples, n_jobs=-1)
    labels = db.fit_predict(features_scaled)
    
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    print(f"[HoleFill] Found {n_clusters} clusters")
    
    # Process each cluster
    result = []
    total_filled = 0
    existing_positions = {(b['x'], b['y'], b['z']) for b in blocks}
    
    for cluster_id in set(labels):
        if cluster_id == -1:
            # Keep noise as is
            for i, b in enumerate(blocks):
                if labels[i] == -1:
                    result.append(b.copy())
            continue
        
        # Get blocks in this cluster
        cluster_blocks = [blocks[i] for i in range(len(blocks)) if labels[i] == cluster_id]
        
        # Find dominant type
        type_counts = Counter(b['type'] for b in cluster_blocks)
        dominant_type = type_counts.most_common(1)[0][0]
        
        # Add existing blocks (unified to dominant type)
        cluster_positions = set()
        for b in cluster_blocks:
            pos = (b['x'], b['y'], b['z'])
            cluster_positions.add(pos)
            result.append({
                'x': b['x'], 'y': b['y'], 'z': b['z'],
                'type': dominant_type
            })
        
        # Fill holes per Y layer using morphological closing
        filled_this_cluster = _fill_holes_per_layer(
            cluster_positions, dominant_type, existing_positions, result
        )
        total_filled += filled_this_cluster
    
    print(f"[HoleFill] Filled {total_filled} holes")
    return result


def _fill_holes_per_layer(
    cluster_positions: set,
    block_type: str,
    existing_positions: set,
    result: list
) -> int:
    """
    Fill holes in a cluster by examining each Y layer.
    Uses flood fill from edges to find internal holes.
    """
    if not cluster_positions:
        return 0
    
    # Get bounds
    xs = [p[0] for p in cluster_positions]
    ys = [p[1] for p in cluster_positions]
    zs = [p[2] for p in cluster_positions]
    
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)
    
    filled_count = 0
    
    # Process each Y layer
    for y in range(min_y, max_y + 1):
        # Get XZ positions at this Y level
        layer_positions = {(p[0], p[2]) for p in cluster_positions if p[1] == y}
        
        if len(layer_positions) < 4:
            continue  # Too few blocks to have holes
        
        layer_xs = [p[0] for p in layer_positions]
        layer_zs = [p[1] for p in layer_positions]
        layer_min_x, layer_max_x = min(layer_xs), max(layer_xs)
        layer_min_z, layer_max_z = min(layer_zs), max(layer_zs)
        
        # Find holes: empty cells that are enclosed by cluster blocks
        # Use simple approach: check if empty cell has neighbors on all 4 sides
        for x in range(layer_min_x, layer_max_x + 1):
            for z in range(layer_min_z, layer_max_z + 1):
                if (x, z) in layer_positions:
                    continue  # Already has a block
                
                # Check if enclosed (has cluster blocks in all 4 cardinal directions)
                has_left = any((nx, z) in layer_positions for nx in range(layer_min_x, x))
                has_right = any((nx, z) in layer_positions for nx in range(x + 1, layer_max_x + 1))
                has_front = any((x, nz) in layer_positions for nz in range(layer_min_z, z))
                has_back = any((x, nz) in layer_positions for nz in range(z + 1, layer_max_z + 1))
                
                if has_left and has_right and has_front and has_back:
                    # This is a hole - fill it
                    pos = (x, y, z)
                    if pos not in existing_positions:
                        result.append({
                            'x': x, 'y': y, 'z': z,
                            'type': block_type
                        })
                        existing_positions.add(pos)
                        filled_count += 1
    
    return filled_count
