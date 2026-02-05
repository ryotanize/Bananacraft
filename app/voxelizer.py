import trimesh
import numpy as np
from skimage import color
import collections
import requests
import io

class Voxelizer:
    def __init__(self):
        # Default Palette: RGB -> Block ID
        # Expanded palette for better matching
        self.block_palette_rgb = {
            # Stone & Ores
            (128, 128, 128): "stone",
            (112, 112, 112): "cobblestone",
            (100, 100, 100): "stone_bricks",
            (160, 160, 160): "andesite",
            (130, 130, 130): "tuff",
            (50, 50, 50): "deepslate",
            
            # Dirt & Ground
            (139, 69, 19): "dirt",
            (101, 67, 33): "coarse_dirt",
            (124, 252, 0): "grass_block",
            (85, 107, 47): "moss_block",
            (210, 180, 140): "sand",
            (238, 197, 145): "red_sand",
            (128, 64, 0): "podzol",

            # Wood (Planks & Logs) & Misc
           (150, 110, 70): "oak_planks",
            (102, 73, 44): "oak_log",
            (110, 80, 50): "spruce_planks",
            (56, 40, 26): "spruce_log",
            (197, 168, 108): "birch_planks",
            (217, 215, 203): "birch_log",
            (165, 119, 90): "jungle_planks",
            (83, 59, 45): "jungle_log",
            (173, 115, 62): "acacia_planks",
            (99, 87, 82): "acacia_log",
            (63, 48, 38): "dark_oak_planks",
            (37, 26, 20): "dark_oak_log",
            (145, 68, 68): "mangrove_planks",
            (220, 120, 140): "cherry_planks",
            (217, 137, 155): "crimson_planks",
            (68, 132, 133): "warped_planks",
            
            # Construction
            (178, 34, 34): "bricks",
            (255, 255, 255): "quartz_block",
            (230, 230, 230): "smooth_quartz",
            
            # Wools
            (233, 236, 236): "white_wool",
            (240, 118, 19): "orange_wool",
            (189, 68, 179): "magenta_wool",
            (58, 175, 217): "light_blue_wool",
            (248, 198, 39): "yellow_wool",
            (112, 185, 25): "lime_wool",
            (237, 113, 163): "pink_wool",
            (62, 68, 71): "gray_wool",
            (142, 142, 134): "light_gray_wool",
            (21, 119, 136): "cyan_wool",
            (121, 56, 178): "purple_wool",
            (46, 56, 141): "blue_wool",
            (96, 59, 31): "brown_wool",
            (94, 124, 22): "green_wool",
            (160, 39, 34): "red_wool",
            (20, 21, 25): "black_wool",
            
            # Concrete
            (207, 213, 214): "white_concrete",
            (224, 97, 1): "orange_concrete",
            (169, 48, 159): "magenta_concrete",
            (35, 137, 199): "light_blue_concrete",
            (241, 175, 21): "yellow_concrete",
            (94, 169, 24): "lime_concrete",
            (213, 101, 142): "pink_concrete",
            (54, 57, 61): "gray_concrete",
            (125, 125, 115): "light_gray_concrete",
            (21, 119, 136): "cyan_concrete",
            (100, 31, 156): "purple_concrete",
            (44, 46, 143): "blue_concrete",
            (96, 59, 31): "brown_concrete",
            (73, 91, 36): "green_concrete",
            (142, 32, 32): "red_concrete",
            (8, 10, 15): "black_concrete",
            
            # Leaves
            (34, 139, 34): "oak_leaves",
            (50, 205, 50): "jungle_leaves",
            (0, 100, 0): "spruce_leaves",
            
            # Decoration
            (255, 215, 0): "gold_block",
            (192, 192, 192): "iron_block",
            (0, 255, 255): "diamond_block",
            (64, 224, 208): "prismarine",
            (70, 70, 120): "dark_prismarine",
            (89, 35, 25): "nether_bricks",
            (20, 10, 20): "obsidian",
            
            # Glass
             (255, 255, 255, 100): "glass"
        }
        
        # Pre-compute LAB palette for faster/better color matching
        self.block_palette_lab = {} # block_id -> lab_color
        self._init_lab_palette()
        
        # Reverse map for quick lookup if needed elsewhere (not critical for logic)
        self.block_palette = self.block_palette_rgb

    def _init_lab_palette(self):
        """Convert RGB palette to CIELAB for perceptual color matching."""
        for rgb, block_id in self.block_palette_rgb.items():
            # Handle RGBA (ignore Alpha for color matching for now, or assume white background)
            if len(rgb) == 4:
                rgb = rgb[:3]
                
            # Normalize 0-255 to 0.0-1.0 for skimage
            rgb_norm = np.array([[rgb]]) / 255.0 
            lab = color.rgb2lab(rgb_norm)[0][0]
            self.block_palette_lab[block_id] = lab

    def _map_color_to_block_lab(self, target_rgb, palette_filter=None):
        """Map a target RGB color to the nearest block using CIELAB distance."""
        # Convert target RGB to LAB
        target_rgb_norm = np.array([[target_rgb]]) / 255.0
        target_lab = color.rgb2lab(target_rgb_norm)[0][0]
        
        min_dist = float('inf')
        best_block = "cobblestone" # Fallback
        
        for block_id, palette_lab in self.block_palette_lab.items():
            # Check filter
            if palette_filter and block_id not in palette_filter:
                continue
                
            # Calculate Delta E (Euclidean distance in Lab space is simple approximation)
            dist = np.linalg.norm(target_lab - palette_lab)
            if dist < min_dist:
                min_dist = dist
                best_block = block_id
                
        return best_block

    def apply_directional_filter(self, blocks, iterations=1):
        """Applies multi-directional scanline smoothing (XYZ + Diagonals)."""
        print(f"Applying Multi-Directional Filter ({iterations} iterations)...")
        if not blocks:
            return []
            
        # Build spatial map
        block_map = {}
        for b in blocks:
            block_map[(b['x'], b['y'], b['z'])] = b.copy() # Work on copies
            
        min_x = min(b['x'] for b in blocks)
        max_x = max(b['x'] for b in blocks)
        min_y = min(b['y'] for b in blocks)
        max_y = max(b['y'] for b in blocks)
        min_z = min(b['z'] for b in blocks)
        max_z = max(b['z'] for b in blocks)

        from collections import Counter

        def filter_line(line_coords):
            # line_coords: list of (x,y,z) sorted by sequence
            # Extract types
            types = []
            valid_indices = []
            for i, c in enumerate(line_coords):
                if c in block_map:
                    types.append(block_map[c]['type'])
                    valid_indices.append(i)
                else:
                    types.append(None)
            
            if not valid_indices:
                return {}

            updates = {}
            window_size = 5
            half = window_size // 2
            
            for i in valid_indices:
                t = types[i]
                start = max(0, i - half)
                end = min(len(types), i + half + 1)
                
                window = [x for x in types[start:end] if x is not None]
                if not window:
                    continue
                    
                most_common = Counter(window).most_common(1)[0][0]
                
                if most_common != t:
                    updates[line_coords[i]] = most_common
            return updates

        for it in range(iterations):
            all_updates = {}
            
            # --- 1. Axis-Aligned Scans ---
            # X-Axis (iterate Y, Z)
            for y in range(min_y, max_y + 1):
                for z in range(min_z, max_z + 1):
                    line = [(x, y, z) for x in range(min_x, max_x + 1)]
                    all_updates.update(filter_line(line))
            
            # Y-Axis (iterate X, Z)
            for x in range(min_x, max_x + 1):
                for z in range(min_z, max_z + 1):
                    line = [(x, y, z) for y in range(min_y, max_y + 1)]
                    all_updates.update(filter_line(line))
                    
            # Z-Axis (iterate X, Y)
            for x in range(min_x, max_x + 1):
                for y in range(min_y, max_y + 1):
                    line = [(x, y, z) for z in range(min_z, max_z + 1)]
                    all_updates.update(filter_line(line))

            # --- 2. Diagonal Scans (DISABLED per user request) ---
            # Planar Diagonals were causing noise patterns. Reverting to Axis-Aligned only.
            
            # Apply Updates
            update_count = 0
            for coord, new_type in all_updates.items():
                if block_map[coord]['type'] != new_type:
                    block_map[coord]['type'] = new_type
                    update_count += 1
            
            print(f"Iteration {it+1}: Updated {update_count} blocks.")
            
        return list(block_map.values())

    def _get_texture_color(self, mesh, face_idx, barycentric):
        """Sample texture color using barycentric coordinates."""
        try:
            # 1. Get UV coordinates for the face vertices
            # mesh.visual.uv contains UVs matching mesh.vertices
            # We need to find which UVs correspond to the face's vertices
            
            # mesh.faces[face_idx] gives indices of vertices
            vertex_indices = mesh.faces[face_idx]
            uvs = mesh.visual.uv[vertex_indices] # (3, 2) array of UVs
            
            # 2. Interpolate UV using barycentric coordinates
            # uv = u*A + v*B + w*C
            # shape: (3, 2) * (3,) -> (2,)
            interpolated_uv = np.dot(barycentric, uvs)
            
            # 3. Sample image at UV
            material = mesh.visual.material
            if hasattr(material, 'baseColorTexture') and material.baseColorTexture:
                 img = material.baseColorTexture
            elif hasattr(material, 'image') and material.image:
                img = material.image
            else:
                return None

            # Handle PIL vs other image types
            if img:
                 width, height = img.size
                 u, v = interpolated_uv
                 # Wrap UVs
                 u = u % 1.0
                 v = v % 1.0
                 # Flip V if necessary (GLTF usually (0,0) is top-left, but texture coords might be bottom-left. Trimesh usually handles this but sometimes V needs flip)
                 # img pixel access
                 x = int(u * (width - 1))
                 y = int(v * (height - 1)) # No Flip for GLTF standard (Top-Left)
                 
                 pixel = img.getpixel((x, y))
                 if len(pixel) >= 3:
                     return pixel[:3]
            
            return None
        except Exception as e:
            # print(f"Texture sampling error: {e}")
            return None

    def voxelize(self, model_url_or_path, target_width, target_depth, palette_filter=None, use_majority_filter=False):
        """
        Voxelize utilizing 6-Directional Ray Casting for solid shell generation.
        1. Load & Scale Mesh
        2. Cast rays from 6 directions (X±, Y±, Z±) to find surface voxels.
        3. Texture mapping using barycentric coordinates of hit points.
        4. Optional: Palette filtering and Majority Voting.
        """
        print(f"Loading mesh from {model_url_or_path}...")
        
        # Load Mesh (omitted common loading logic for brevity, assuming standard flow follows)
        if model_url_or_path.startswith("http"):
            try:
                r = requests.get(model_url_or_path)
                file_obj = io.BytesIO(r.content)
                scene = trimesh.load(file_obj, file_type='glb')
            except Exception as e:
                print(f"Failed to load form URL: {e}")
                return []
        else:
            scene = trimesh.load(model_url_or_path)
        
        # Handle Scene vs Mesh
        if isinstance(scene, trimesh.Scene):
            if len(scene.geometry) == 0:
                print("Empty scene.")
                return []
            try:
                mesh = scene.dump(concatenate=True)
            except Exception as e:
                print(f"Error dumping scene: {e}. Falling back to geometry concatenation.")
                mesh = trimesh.util.concatenate(tuple(scene.geometry.values()))
        else:
            mesh = scene

        # --- 1. Rescaling ---
        extents = mesh.extents
        scale_x = target_width / extents[0]
        scale_z = target_depth / extents[2]
        
        # Uniform scaling to fit within target dimensions
        scale_factor = min(scale_x, scale_z)
        
        transform = trimesh.transformations.scale_matrix(scale_factor)
        mesh.apply_transform(transform)
        
        # Move to positive quadrant
        mesh.apply_translation(-mesh.bounds[0])
        
        print(f"Scaled mesh extents: {mesh.extents}")

        # --- 2. Ray Casting Setup ---
        # Define grid bounds from mesh bounds
        # Add slight padding to ensure we capture edges
        bounds = mesh.bounds
        min_bound = np.floor(bounds[0]).astype(int)
        max_bound = np.ceil(bounds[1]).astype(int)
        
        # Dimensions including padding
        size = max_bound - min_bound
        # Ensure we have some space
        size = np.maximum(size, [1, 1, 1])
        
        print(f"Voxel Grid Size: {size}")

        # Initialize Voxel Data: (x,y,z) -> list of colors
        voxel_data = collections.defaultdict(list)

        # Helper to process hits
        def process_hits(origins, directions):
            # Use ray.intersects_location
            # It returns (locations, index_ray, index_tri)
            try:
                locations, index_ray, index_tri = mesh.ray.intersects_location(
                    ray_origins=origins,
                    ray_directions=directions,
                    multiple_hits=False # We only want the first hit (surface)
                )
            except Exception as e:
                print(f"Ray casting error: {e}")
                return

            if len(locations) == 0:
                return

            # Prepare for color extraction
            # Get triangles for barycentric calc
            triangles = mesh.vertices[mesh.faces[index_tri]]
            barycentric = trimesh.triangles.points_to_barycentric(triangles, locations)
            
            # Process each hit
            for i, loc in enumerate(locations):
                # Voxel Coordinate
                vx = int(round(loc[0]))
                vy = int(round(loc[1]))
                vz = int(round(loc[2]))
                
                # Fetch color
                color_val = None
                
                # UV Texture Sampling
                idx_tri = index_tri[i]
                bary = barycentric[i]
                
                color_val = self._get_texture_color(mesh, idx_tri, bary)
                
                # Fallback Color
                if color_val is None:
                     # Face Color
                    if hasattr(mesh.visual, 'face_colors') and len(mesh.visual.face_colors) > 0:
                        if idx_tri < len(mesh.visual.face_colors):
                             color_val = mesh.visual.face_colors[idx_tri][:3]
                
                if color_val is None:
                    color_val = (128, 128, 128) # Gray fallback

                voxel_data[(vx, vy, vz)].append(color_val)

        # --- 3. Execute Ray Casting (6 Directions) ---
        print("Casting rays from 6 directions...")
        
        # Ranges
        x_range = range(min_bound[0], max_bound[0] + 1)
        y_range = range(min_bound[1], max_bound[1] + 1)
        z_range = range(min_bound[2], max_bound[2] + 1)
        
        margin = 10.0 # Start rays from outside
        
        # 3.1 X-Axis Scans (YZ Plane)
        origins = []
        directions = []
        # Positive Direction (+X)
        for y in y_range:
            for z in z_range:
                origins.append([min_bound[0] - margin, y, z])
                directions.append([1, 0, 0])
        # Negative Direction (-X)
        for y in y_range:
            for z in z_range:
                origins.append([max_bound[0] + margin, y, z])
                directions.append([-1, 0, 0])
        
        if origins:
            process_hits(np.array(origins), np.array(directions))
            
        # 3.2 Y-Axis Scans (XZ Plane)
        origins = []
        directions = []
        # +Y
        for x in x_range:
            for z in z_range:
                origins.append([x, min_bound[1] - margin, z])
                directions.append([0, 1, 0])
        # -Y
        for x in x_range:
            for z in z_range:
                origins.append([x, max_bound[1] + margin, z])
                directions.append([0, -1, 0])

        if origins:
            process_hits(np.array(origins), np.array(directions))

        # 3.3 Z-Axis Scans (XY Plane)
        origins = []
        directions = []
        # +Z
        for x in x_range:
            for y in y_range:
                origins.append([x, y, min_bound[2] - margin])
                directions.append([0, 0, 1])
        # -Z
        for x in x_range:
            for y in y_range:
                origins.append([x, y, max_bound[2] + margin])
                directions.append([0, 0, -1])

        if origins:
            process_hits(np.array(origins), np.array(directions))


        # --- 4. Aggregation and Mapping ---
        blocks = []
        print(f"Aggregating {len(voxel_data)} active voxels...")
        
        for (vx, vy, vz), colors in voxel_data.items():
            if not colors:
                continue
            
            # Average Color
            avg_rgb = np.mean(colors, axis=0).astype(int)
            
            # Map to Block ID (Pass filter)
            block_type = self._map_color_to_block_lab(avg_rgb, palette_filter=palette_filter)
            
            blocks.append({
                "x": vx,
                "y": vy,
                "z": vz,
                "type": block_type
            })

        print(f"Initial voxel count: {len(blocks)}")

        # --- 5. Post-Processing: Directional Scanline Voting ---
        if use_majority_filter:
            blocks = self.apply_directional_filter(blocks, iterations=2) # 2 iterations for stability

        print(f"Voxelization complete. Generated {len(blocks)} blocks.")
        return blocks
