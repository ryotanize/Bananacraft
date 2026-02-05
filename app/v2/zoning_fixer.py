import math
from typing import Dict, List, Any

def rectangles_overlap(r1, r2, padding=1):
    """Check if two rectangles overlap."""
    return not (r1['x'] + r1['width'] + padding <= r2['x'] or
                r1['x'] >= r2['x'] + r2['width'] + padding or
                r1['z'] + r1['depth'] + padding <= r2['z'] or
                r1['z'] >= r2['z'] + r2['depth'] + padding)

def resolve_collisions(zoning_data: Dict[str, Any], map_width=200, map_depth=200) -> Dict[str, Any]:
    """
    Detects and resolves overlapping buildings in zoning_data.
    Also ensures buildings stay within map bounds.
    """
    buildings = zoning_data.get("buildings", [])
    if not buildings:
        return zoning_data

    # Simple Iterative Solver
    MAX_ITER = 50
    moved = True
    
    for _ in range(MAX_ITER):
        if not moved: break
        moved = False
        
        for i, b1 in enumerate(buildings):
            p1 = b1['position']
            # Bounds check
            if p1['x'] < 0: p1['x'] = 0; moved = True
            if p1['z'] < 0: p1['z'] = 0; moved = True
            if p1['x'] + p1['width'] > map_width: p1['x'] = map_width - p1['width']; moved = True
            if p1['z'] + p1['depth'] > map_depth: p1['z'] = map_depth - p1['depth']; moved = True
            
            for j, b2 in enumerate(buildings):
                if i == j: continue
                p2 = b2['position']
                
                if rectangles_overlap(p1, p2, padding=2): # 2 blocks padding for roads/buffer
                    # Move b1 away from b2
                    # Find overlap vector
                    cx1 = p1['x'] + p1['width']/2
                    cz1 = p1['z'] + p1['depth']/2
                    cx2 = p2['x'] + p2['width']/2
                    cz2 = p2['z'] + p2['depth']/2
                    
                    dx = cx1 - cx2
                    dz = cz1 - cz2
                    
                    # Normalize and push
                    dist = math.sqrt(dx*dx + dz*dz)
                    if dist == 0: dist = 0.1; dx = 1 # Overlapping centers
                    
                    push_dist = 5 # blocks
                    move_x = (dx / dist) * push_dist
                    move_z = (dz / dist) * push_dist
                    
                    p1['x'] = int(p1['x'] + move_x)
                    p1['z'] = int(p1['z'] + move_z)
                    moved = True
    
    zoning_data['buildings'] = buildings
    return zoning_data

def assign_orientation(zoning_data: Dict[str, Any], map_width=200, map_depth=200) -> Dict[str, Any]:
    """
    Assigns 'facing' property to each building.
    Heuristic: Face towards the map center or nearest large open space.
    For now, simply face map center (100, 100).
    """
    center_x = map_width / 2
    center_z = map_depth / 2
    
    for b in zoning_data.get("buildings", []):
        p = b['position']
        bx = p['x'] + p['width'] / 2
        bz = p['z'] + p['depth'] / 2
        
        dx = bx - center_x
        dz = bz - center_z
        
        # If building is at (150, 100), it's to the RIGHT of center. It should face LEFT (West) to look at center.
        # dx > 0 -> Face West
        # dx < 0 -> Face East
        # dz > 0 -> Face North
        # dz < 0 -> Face South
        
        if abs(dx) > abs(dz):
            b['facing'] = "west" if dx > 0 else "east"
        else:
            b['facing'] = "north" if dz > 0 else "south"
            
    return zoning_data

def fix_zoning(zoning_data: Dict[str, Any]) -> Dict[str, Any]:
    """Applies all fixes to zoning data."""
    if not zoning_data: return zoning_data
    
    # 1. Resolve Collisions
    zoning_data = resolve_collisions(zoning_data)
    
    # 2. Assign Orientation
    zoning_data = assign_orientation(zoning_data)
    
    return zoning_data
