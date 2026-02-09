import json
import copy

class LayoutEngine:
    """
    Manages the zoning layout and handles dynamic adjustments based on actual building sizes.
    """
    def __init__(self, zoning_data):
        """
        zoning_data: List of zone dictionaries (from zoning.json) OR a Dict with "buildings" key.
        """
        self.metadata = {}
        if isinstance(zoning_data, dict):
            # Extract metadata and buildings
            self.metadata = copy.deepcopy(zoning_data)
            self.zones = self.metadata.pop("buildings", [])
        else:
            self.zones = copy.deepcopy(zoning_data)
        
    def get_zones(self):
        if self.metadata:
            # Reconstruct the full dict
            data = copy.deepcopy(self.metadata)
            data["buildings"] = self.zones
            return data
        return self.zones
        
    def update_zone_from_blocks(self, zone_id, blocks):
        """
        Updates the specified zone's dimensions based on the min/max of the provided blocks.
        blocks: List of block dicts {x, y, z, ...} relative to zone origin.
        """
        target_zone = next((z for z in self.zones if z['id'] == zone_id), None)
        if not target_zone:
            return False
            
        if not blocks:
            return False
            
        # Calculate bounds relative to (0,0,0) of the zone
        xs = [b['x'] for b in blocks]
        zs = [b['z'] for b in blocks]
        
        min_x, max_x = min(xs), max(xs)
        min_z, max_z = min(zs), max(zs)
        
        # Original dimensions
        # width (x size), depth (z size)
        
        # Calculate new size
        # We assume the origin (0,0,0) is kept, but the building might extend negatively or excessively positively.
        # If building extends to -5, that implies the "start" of the zone should effectively be shifted -5?
        # Or we just assume the Zone Rect is (x + min_x, z + min_z, width, depth) in world space?
        # Standard zoning usually implies: Zone X/Z is the anchor.
        # If blocks go negative, the effective "World X" of the leftmost block is ZoneX + min_x.
        
        # Let's adjust the Zone definition to encompass the blocks.
        # New World X = Old World X + min_x
        # New Width = max_x - min_x + 1
        
        # Wait, if we shift World X, we shift the blocks too (since they are relative)?
        # No, blocks are relative to the "Anchor".
        # If we move the Anchor (Zone X), the blocks move in world space.
        
        # User wants "zoning.json" updated.
        # If we update Zone X, we shift the instruction origin.
        # So we should be careful. 
        # Actually, the user wants to AVOID overlap.
        # If Gemini built -5 to +5, and original zone was 0 to 10.
        # If we implicitly say the "Occupied Area" is now ZoneX-5 to ZoneX+5.
        
        # Let's update the "Effective Bounds" in zoning.
        # But 'position' in zoning has 'x', 'z', 'width', 'depth'.
        # If we assume 'x', 'z' is the anchor point for the Carpenter.
        # Then the "Occupied Rect" is:
        #   RectX = Zone['position']['x'] + min_x
        #   RectZ = Zone['position']['z'] + min_z
        #   RectW = max_x - min_x + 1
        #   RectD = max_z - min_z + 1
        
        # We can update the zone's width/depth to match strict bounds, 
        # BUT we might need to introduce an 'offset' if min_x != 0 ?
        # Or just changing x/z to RectX/RectZ might break the relationship with the generated blocks?
        # If blocks are generated expecting (0,0) to be the user-defined anchor...
        # If we change the anchor in zoning, we effectively move the building.
        # WHICH IS WHAT WE WANT (to avoid collision).
        
        # So:
        # 1. Update Zone width/depth to strictly match the block bounding box size.
        # 2. Update Zone x/z to be the top-left of the bounding box.
        #    New_Zone_X = Old_Zone_X + min_x
        #    New_Zone_Z = Old_Zone_Z + min_z
        #    New_Width = max_x - min_x + 1
        #    New_Depth = max_z - min_z + 1
        
        # Wait, if we change Zone X, then next time we build, we place blocks relative to New Zone X.
        # But our blocks are relative to Old Zone X (implied 0,0).
        # We need to Shift the blocks too? 
        # The prompt implies: "Gemini created a model... update coordinates to avoid overlap".
        # If we just update zoning.json, Phase 3 reads zoning.json.
        # Phase 3: build_origin = current_origin + zone['position']['x']...
        # rcon.build_voxels(blocks, origin=build_origin).
        # If we change zone['x'], build_origin changes. The blocks will be placed at New X + relative_block_x.
        # If we set New X = Old X + min_x.
        # And blocks still have min_x (e.g. -5).
        # Then placed location = (Old X - 5) - 5 = Old X - 10.  Double shift!
        
        # CORRECT LOGIC:
        # We want to change Zone X such that the "Physical Space" is correct?
        # No, we want to shift the Whole Building to valid space.
        # We keep the blocks RELATIVE to the anchor as is.
        # We just move the ANCHOR (Zone X/Z) if there is a collision.
        # However, to check collision, we need the TRUE SIZE.
        
        # So first: Calculate True Width/Depth of the model.
        # If the model is 20 wide (but was zoning 10), we update width=20.
        # But does it expand centered? Or rightwards?
        # Depends on blocks min/max.
        # If blocks are 0 to 20. Width is 21.
        # If we update width=21 in zoning, that's fine.
        
        # PROBLEM: 'x' and 'z' in zoning usually denote the top-left corner of the allocated area.
        # If blocks go from -5 to +15.
        # The physical footprint is [Anchor-5, Anchor+15].
        # If we don't change 'x', our collision logic (which assumes X to X+W) will be wrong.
        # Collision logic usually assumes Rect(x, z, w, d).
        
        # So we should Normalize the Zone definition?
        # Or just store 'bounds_offset' in zoning?
        # The user said "update zoning.json". Stick to standard fields if possible.
        
        # Strategy:
        # 1. Calculate Occupied Rect relative to Current Anchor:
        #    ox = min_x, oz = min_z, w = ..., h = ...
        # 2. If ox != 0 or oz != 0, it means the building is not aligned with the anchor top-left.
        # 3. We *could* shift the blocks to 0,0 and move the anchor?
        #    But `blocks_v2.json` is saved on disk. We shouldn't modify it implicitly here.
        #    (The user didn't ask to rewrite blocks file, but to adjust zoning).
        
        # Let's assume we maintain:
        # Zone X/Z = Anchor Point.
        # Added Field: 'actual_bounds' = {min_x, min_z, max_x, max_z} relative to Anchor?
        # Or easier: Just update width/depth to be `max_x - min_x`.
        # And check collision using (Anchor + min_x, Anchor + min_z, width, depth).
        
        # But standard `zoning.json` might not support offsets. 
        # Let's hope the collision check is flexible enough.
        # Actually, let's keep it simple:
        # just treat zone['x'] as the left-most edge OF THE AREA.
        # If blocks start at -5, we should ideally shift Zone X by -5?
        # But then we must shift blocks by +5. Too complex.
        
        # Alternative: Just trust that Width/Deep update is enough for now?
        # If blocks are -5 to 5. Width 11.
        # If we say Width=11. And Anchor stays put.
        # Collision System assumes Anchor to Anchor+11.
        # Actual is Anchor-5 to Anchor+5.
        # It's misaligned.
        
        # Let's use `collision_bounds` if available, or fallback to x,z,w,d.
        # I'll calculate `actual_bounds` and store it in the zone data.
        
        target_zone['actual_bounds'] = {
            'min_x': min_x,
            'max_x': max_x,
            'min_z': min_z,
            'max_z': max_z,
            'width': max_x - min_x + 1,
            'depth': max_z - min_z + 1
        }
        
        # Update display width/depth for UI too
        target_zone['position']['width'] = target_zone['actual_bounds']['width']
        target_zone['position']['depth'] = target_zone['actual_bounds']['depth']
        
        return True

    def resolve_collisions(self, active_zone_id, buffer=4):
        """
        Checks if active_zone overlaps with any other zone.
        If so, finds the nearest non-overlapping position using a spiral search.
        Returns true if shifted.
        buffer: Minimum gap between buildings (blocks).
        """
        active = next((z for z in self.zones if z['id'] == active_zone_id), None)
        if not active:
            return False
            
        # Helper to get world rect
        def get_rect(z, current_pos=None):
            # Use current_pos if provided (for testing candidates), else z['position']
            px = current_pos['x'] if current_pos else z['position']['x']
            pz = current_pos['z'] if current_pos else z['position']['z']
            
            if 'actual_bounds' in z:
                b = z['actual_bounds']
                return (px + b['min_x'], pz + b['min_z'], b['width'], b['depth'])
            else:
                 return (px, pz, z['position']['width'], z['position']['depth'])

        # Check for collision with specific rect
        def is_colliding(candidate_rect, ignore_id):
            cx, cz, cw, cd = candidate_rect
            # Expand candidate by buffer for check
            cx -= buffer
            cz -= buffer
            cw += (buffer * 2)
            cd += (buffer * 2)
            
            for other in self.zones:
                if other['id'] == ignore_id:
                    continue
                
                ox, oz, ow, od = get_rect(other)
                
                # AABB Collision
                if (cx < ox + ow and
                    cx + cw > ox and
                    cz < oz + od and
                    cz + cd > oz):
                    return True
            return False

        # Initial check
        current_rect = get_rect(active)
        if not is_colliding(current_rect, active_zone_id):
            return False # No initial collision
            
        # Collision detected: Start Spiral Search
        # We search for a new (x, z) for the zone anchor
        original_x = active['position']['x']
        original_z = active['position']['z']
        
        step_size = 5 # efficiency
        max_steps = 100 
        
        # Simple spiral generator
        def spiral_search():
            x = y = 0
            dx = 0
            dy = -1
            for i in range(max_steps**2):
                if (-max_steps/2 < x <= max_steps/2) and (-max_steps/2 < y <= max_steps/2):
                    yield (x * step_size, y * step_size)
                if x == y or (x < 0 and x == -y) or (x > 0 and x == 1-y):
                    dx, dy = -dy, dx
                x, y = x+dx, y+dy

        for dx, dz in spiral_search():
            if dx == 0 and dz == 0: continue
            
            new_x = original_x + dx
            new_z = original_z + dz
            
            candidate_pos = {'x': new_x, 'z': new_z}
            candidate_rect = get_rect(active, current_pos=candidate_pos)
            
            if not is_colliding(candidate_rect, active_zone_id):
                # Found valid spot!
                active['position']['x'] = new_x
                active['position']['z'] = new_z
                return True
                
        return False # Could not resolve within limit
