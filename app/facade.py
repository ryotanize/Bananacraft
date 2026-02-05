
import collections

class FacadeExtraction:
    def __init__(self, blocks):
        self.blocks = blocks
        self.block_map = {(b['x'], b['y'], b['z']): b for b in blocks}
        
        if not blocks:
            self.min_x = self.max_x = 0
            self.min_y = self.max_y = 0
            self.min_z = self.max_z = 0
        else:
            self.min_x = min(b['x'] for b in blocks)
            self.max_x = max(b['x'] for b in blocks)
            self.min_y = min(b['y'] for b in blocks)
            self.max_y = max(b['y'] for b in blocks)
            self.min_z = min(b['z'] for b in blocks)
            self.max_z = max(b['z'] for b in blocks)

    def extract_front_view(self, direction='south'):
        """
        Extracts the visible surface blocks from a given direction.
        
        Directions (Minecraft standard):
        - south: +Z direction (Looking from -Z to +Z?) 
                 Wait, Minecraft South is +Z. So looking AT South face means looking from South (-Z direction)?
                 Let's stick to axis names for clarity.
        
        Args:
            direction: 'z_plus', 'z_minus', 'x_plus', 'x_minus'
                       'z_plus' means looking towards +Z (i.e. camera is at -inf).
                       'z_minus' means looking towards -Z (i.e. camera is at +inf).
        
        Returns:
            grid: 2D list of block types (row=y, col=x/z). Origin at top-left or bottom-left?
                  Let's use Bottom-Left logic (y increases upwards), mapped to 2D array.
            depth_map: 2D list of depth coordinates (the axis perpendicular to view).
            mapping: dict correlating 2D grid (row, col) back to 3D coordinate (x,y,z).
        """
        
        # Determine Scan Ranges
        # We need to iterate over the viewing plane (e.g. XY)
        # And find the "first" block in the depth axis (e.g. Z)
        
        view_plane = [] # List of (u, v) coordinates
        
        u_min, u_max = 0, 0
        v_min, v_max = self.min_y, self.max_y # V is always Y (Height) for building facades
        
        depth_axis_range = range(0, 0)
        
        if direction == 'z_plus': # Camera at -Z, looking +Z. Visible face is "North" face (if Z+ is South)
            u_min, u_max = self.min_x, self.max_x
            depth_axis_range = range(self.min_z, self.max_z + 1) # Scan from min to max
        elif direction == 'z_minus': # Camera at +Z, looking -Z. Visible face is "South" face
            u_min, u_max = self.min_x, self.max_x
            depth_axis_range = range(self.max_z, self.min_z - 1, -1) # Scan from max to min
        elif direction == 'x_plus': # Camera at -X, looking +X. Visible face is "West" face
            u_min, u_max = self.min_z, self.max_z
            depth_axis_range = range(self.min_x, self.max_x + 1)
        elif direction == 'x_minus': # Camera at +X, looking -X. Visible face is "East" face
            u_min, u_max = self.min_z, self.max_z
            depth_axis_range = range(self.max_x, self.min_x - 1, -1)
            
        width = u_max - u_min + 1
        height = v_max - v_min + 1
        
        grid = [[None for _ in range(width)] for _ in range(height)]
        depth_map = [[None for _ in range(width)] for _ in range(height)]
        mapping = {} # (row, col) -> (x, y, z)
        
        # Iterate over the projection plane (U, V)
        # V is Y (height), U is X or Z
        for v_idx, y in enumerate(range(v_min, v_max + 1)):
            for u_idx, u in enumerate(range(u_min, u_max + 1)):
                # Scan depth
                found_block = None
                found_depth = None
                found_coord = None
                
                for d in depth_axis_range:
                    # Construct 3D coord based on direction
                    x, z = 0, 0
                    if 'z' in direction:
                        x = u
                        z = d
                    else: # 'x' in direction
                        x = d
                        z = u
                        
                    if (x, y, z) in self.block_map:
                        found_block = self.block_map[(x, y, z)]['type']
                        found_depth = d
                        found_coord = (x, y, z)
                        break # Found visible block
                
                # Use standard image coordinates: Row 0 is Top (Max Y)
                # Minecraft Y increases upwards.
                # Let's map Y=Min to Grid Row=Height-1
                # Y=Max to Grid Row=0
                row = height - 1 - v_idx
                col = u_idx
                
                if found_block:
                    grid[row][col] = found_block
                    depth_map[row][col] = found_depth
                    mapping[(row, col)] = found_coord
                    
        return {
            "grid": grid,
            "depth_map": depth_map,
            "mapping": mapping,
            "dimensions": {"width": width, "height": height},
            "ranges": {"u_min": u_min, "v_min": v_min}
        }

    def apply_updates(self, original_blocks, grid_data, updates):
        """
        Applies a list of updates from Gemini to the original blocks.
        
        Args:
            original_blocks: List of block dicts.
            grid_data: The dict returned by extract_front_view (contains mapping).
            updates: List of dicts {'row': int, 'col': int, 'type': str}
            
        Returns:
            List of updated block dicts.
        """
        mapping = grid_data["mapping"]
        
        # Create a dict for fast lookup/update
        # Key: (x,y,z), Value: block dict
        block_dict = {(b['x'], b['y'], b['z']): b.copy() for b in original_blocks}
        
        count = 0
        for up in updates:
            row = up['row']
            col = up['col']
            new_type = up['type']
            
            if (row, col) in mapping:
                coord = mapping[(row, col)]
                
                # Check if block exists at that coord
                if coord in block_dict:
                    block_dict[coord]['type'] = new_type
                    count += 1
                else:
                    # If Gemini wants to ADD a block where there was air (gap),
                    # we need to create it.
                    # Coordinates are in mapping because we scanned range?
                    # Ah, extract_front_view mapping only includes FOUND blocks.
                    # If mapping has it, block_dict should have it.
                    pass 
            else:
                # Gemini tried to update a non-mapped cell (maybe empty space in grid)
                # To support adding blocks, we need mapping to include empty cells' theoretical coords?
                # For now, ignore.
                pass
                
        print(f"Applied {count} updates from Gemini.")
        return list(block_dict.values())
