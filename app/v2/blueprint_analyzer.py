"""
Blueprint Analyzer for Bananacraft 2.0

Parses the Architect's instructions to create a semantic map of the building.
Calculates precise anchor points and surface normals for the Decorator,
ensuring decorations attach correctly to walls and roofs.
"""
from typing import List, Dict, Any, Tuple, Optional

class BlueprintAnalyzer:
    def __init__(self, instructions: List[Dict[str, Any]]):
        self.instructions = instructions
        self.elements = []
        self._parse_structure()

    def _calculate_centroid(self) -> Tuple[float, float]:
        """Calculates the geometric center (X, Z) of the structure."""
        total_x, total_z, count = 0, 0, 0
        for inst in self.instructions:
            tool = inst.get("tool_name")
            params = inst.get("parameters", {})
            if tool == "draw_plane":
                # Use midpoint of the plane
                ea = params["edge_a"]
                eb = params["edge_b"]
                mid_x = (ea[0][0] + eb[1][0]) / 2
                mid_z = (ea[0][2] + eb[1][2]) / 2
                total_x += mid_x
                total_z += mid_z
                count += 1
            elif tool in ["place_window", "place_door"]:
                pos = params["position"]
                total_x += pos[0]
                total_z += pos[2]
                count += 1
        
        if count == 0: return 25, 25 # Fallback
        return total_x / count, total_z / count

    def _parse_structure(self):
        """Parse instructions into targetable elements."""
        cx, cz = self._calculate_centroid()
        
        for i, inst in enumerate(self.instructions):
            tool = inst.get("tool_name")
            params = inst.get("parameters", {})
            
            # Base element structure
            element = {
                "id": i,
                "tool": tool,
                "params": params,
                "target_info": None 
            }

            # 1. Walls & Planes (draw_plane)
            if tool == "draw_plane":
                edge_a = params["edge_a"]
                edge_b = params["edge_b"]
                
                # Check orientation
                # Vertical Wall Z-aligned (Normal along X) -> Constant X
                if edge_a[0][0] == edge_a[1][0] == edge_b[0][0]: 
                    x = edge_a[0][0]
                    # Determine facing relative to centroid
                    # If Wall X < Centroid X, Normal should point West (-X) (Outwards)
                    # If Wall X > Centroid X, Normal should point East (+X) (Outwards)
                    # Note: "Facing" usually means the direction the OUTSIDE surface points.
                    facing = "west" if x < cx else "east"
                    
                    element["target_info"] = {
                        "type": "wall",
                        "orientation": "vertical_x", # Constant X
                        "constant_val": x,
                        "ranges": {
                            "h": sorted([edge_a[0][2], edge_a[1][2]]), # Z range
                            "v": sorted([edge_a[0][1], edge_b[0][1]])  # Y range
                        },
                        "facing_guess": facing
                    }

                # Vertical Wall X-aligned (Normal along Z) -> Constant Z
                elif edge_a[0][2] == edge_a[1][2] == edge_b[0][2]:
                    z = edge_a[0][2]
                    # If Wall Z < Centroid Z, Normal points North (-Z)
                    # If Wall Z > Centroid Z, Normal points South (+Z)
                    facing = "north" if z < cz else "south"

                    element["target_info"] = {
                        "type": "wall",
                        "orientation": "vertical_z", # Constant Z
                        "constant_val": z,
                        "ranges": {
                            "h": sorted([edge_a[0][0], edge_a[1][0]]), # X range
                            "v": sorted([edge_a[0][1], edge_b[0][1]])  # Y range
                        },
                        "facing_guess": facing
                    }
                
                # Sloped Roof or Horizontal Floor
                else:
                    # Treat as roof plane
                    element["target_info"] = {
                        "type": "roof",
                        "edge_a": edge_a,
                        "edge_b": edge_b,
                        "facing_guess": "up"
                    }

            # 2. Windows
            elif tool == "place_window":
                pos = params["position"]
                element["target_info"] = {
                    "type": "window",
                    "base": pos,
                    "width": params.get("width", 1),
                    "height": params.get("height", 2),
                    "facing": params.get("facing", "north")
                }
            
            # 3. Doors
            elif tool == "place_door":
                pos = params["position"]
                element["target_info"] = {
                    "type": "door",
                    "base": pos,
                    "facing": params.get("facing", "north"),
                    "width": 2 if params.get("is_double") else 1,
                    "height": 2
                }

            # 4. Pillars
            elif tool == "place_smart_pillar":
                element["target_info"] = {
                    "type": "pillar",
                    "base": params["base"],
                    "top": params["top"]
                }
            
            # 5. Curve Loft (Arches/Roofs)
            elif tool == "draw_curve_loft":
                 element["target_info"] = {
                    "type": "curve_loft",
                    "params": params,
                    "facing_guess": "up" # Simplified
                }

            if element["target_info"]:
                self.elements.append(element)

    def get_element_summary(self) -> str:
        """Generates a text summary of elements for the LLM."""
        lines = []
        for el in self.elements:
            info = el["target_info"]
            eid = el["id"]
            e_type = info["type"]
            
            desc = f"ID: {eid} | Type: {e_type.upper()}"
            
            if e_type == "wall":
                facing = info.get("facing_guess", "unknown")
                rng = info["ranges"]
                w = abs(rng['h'][1] - rng['h'][0])
                h = abs(rng['v'][1] - rng['v'][0])
                desc += f" | Facing: {facing} | Size: {w}x{h} (W x H)"
            
            elif e_type == "window":
                desc += f" | Facing: {info['facing']} | Pos: {info['base']} | Size: {info['width']}x{info['height']}"
            
            elif e_type == "door":
                desc += f" | Facing: {info['facing']} | Pos: {info['base']} | Size: {info['width']}x{info['height']}"

            elif e_type == "roof":
                desc += " | Sloped/Flat Plane"

            lines.append(desc)
        return "\n".join(lines)

    def get_element_dimensions(self, element_id: int) -> Tuple[int, int]:
        """Returns (width, height) of the element."""
        el = self.get_element_by_id(element_id)
        if not el: return 0, 0
        
        info = el["target_info"]
        e_type = info["type"]
        
        if e_type == "wall":
            h_min, h_max = info["ranges"]["h"]
            v_min, v_max = info["ranges"]["v"]
            return abs(h_max - h_min), abs(v_max - v_min)
            
        elif e_type in ["window", "door"]:
            return info.get("width", 1), info.get("height", 2)
            
        elif e_type == "pillar":
            # Height is top - base y
            # Width is 1 (assumed)
            by = info["base"][1]
            ty = info["top"][1]
            return 1, abs(ty - by)
            
        return 0, 0

    def get_element_by_id(self, eid: int):
        for el in self.elements:
            if el["id"] == eid:
                return el
        return None

    def calculate_anchor(self, element_id: int, pos_mode: str = "center") -> Tuple[float, float, float, str]:
        """
        Calculates the absolute world coordinate (anchor) and facing vector
        for a given element ID and position mode.
        
        Args:
            element_id: Target ID
            pos_mode: "center", "bottom_center", "bottom_left", "top_center", "surface_random"
            
        Returns:
            (x, y, z, facing_direction)
        """
        el = self.get_element_by_id(element_id)
        if not el:
            return 0,0,0, "north"

        info = el["target_info"]
        e_type = info["type"]

        # --- WINDOW / DOOR ---
        if e_type in ["window", "door"]:
            bx, by, bz = info["base"]
            w = info.get("width", 1)
            h = info.get("height", 2)
            facing = info["facing"]
            
            dx, dy, dz = 0, 0, 0
            
            # Helper for Width-axis offset (Centered vs Left)
            # Viewer's Perspective:
            # If "Left", we start at the Viewer's Left edge.
            # If "Center", we start at Middle.
            
            # Base Position (bx,bz) is Top-Left or Bottom-Left?
            # Usually Architect positions are Bottom-Left (Min Coords).
            # Let's assume (bx, by, bz) is the 'Min X, Min Y, Min Z' corner of the block.
            
            # Center Calculation
            cx = w / 2
            cz = w / 2 # Only one applies
            
            if pos_mode == "bottom_left":
                # If bx,bz is already min-coords for the block, we return it? 
                # But we need "Viewer's Bottom Left".
                # South Facing (View North): Right=+X, Left=-X. Min X is Left. -> OK.
                # North Facing (View South): Right=-X, Left=+X. Min X is Right. -> Needs Max X.
                # West Facing (View East): Right=+Z, Left=-Z. Min Z is Left. -> OK.
                # East Facing (View West): Right=-Z, Left=+Z. Min Z is Right. -> Needs Max Z.
                
                if facing == "north": dx = w # Start at Max X (Viewer Left)
                elif facing == "east": dz = w # Start at Max Z (Viewer Left)
                # south: dx=0 (Min X is Left)
                # west: dz=0 (Min Z is Left)
                return bx + dx, by, bz + dz, facing

            elif pos_mode == "bottom_center":
                if facing in ["north", "south"]: dx = w / 2
                else: dz = w / 2
                return bx + dx, by, bz + dz, facing
            
            elif pos_mode == "top_center":
                if facing in ["north", "south"]: dx = w / 2
                else: dz = w / 2
                return bx + dx, by + h, bz + dz, facing

            else: # Center
                if facing in ["north", "south"]: dx = w / 2
                else: dz = w / 2
                return bx + dx, by + h / 2, bz + dz, facing

        # --- WALL ---
        elif e_type == "wall":
            facing = info["facing_guess"]
            const_val = info["constant_val"]
            h_min, h_max = info["ranges"]["h"]
            v_min, v_max = info["ranges"]["v"]
            
            # Wall "Center"
            h_mid = (h_min + h_max) / 2
            v_mid = (v_min + v_max) / 2
            
            if info["orientation"] == "vertical_z": # Runs along X (Constant Z)
                # h_range is X
                if pos_mode == "bottom_left":
                    # Facing South (+Z): View North. Right=+X, Left=-X. Min X is LEFT.
                    # Facing North (-Z): View South. Right=-X, Left=+X. Max X is LEFT.
                    x_start = h_max if facing == "north" else h_min
                    return x_start, v_min, const_val, facing
                elif pos_mode == "bottom_center":
                    return h_mid, v_min, const_val, facing
                else: # Center
                    return h_mid, v_mid, const_val, facing
                    
            else: # Runs along Z (Constant X)
                # h_range is Z
                if pos_mode == "bottom_left":
                    # Facing East (+X): View West. Right=-Z, Left=+Z. Max Z is LEFT.
                    # Facing West (-X): View East. Right=+Z, Left=-Z. Min Z is LEFT.
                    z_start = h_max if facing == "east" else h_min
                    return const_val, v_min, z_start, facing
                elif pos_mode == "bottom_center":
                    return const_val, v_min, h_mid, facing
                else: # Center
                    return const_val, v_mid, h_mid, facing

        # --- ROOF ---
        elif e_type == "roof":
            # Just return center of bounding box approx
            ea = info["edge_a"]
            eb = info["edge_b"]
            
            mid_x = (ea[0][0] + eb[1][0]) / 2
            mid_y = (ea[0][1] + eb[0][1]) / 2
            mid_z = (ea[0][2] + eb[1][2]) / 2
            
            return mid_x, mid_y, mid_z, "up"

        # Default fallback
        return 0,0,0, "north"