"""
Decorator - Gemini Function Calling client for Bananacraft 2.0 (Decoration Phase)

The Decorator analyzes the "Decorated" concept image and the "Structure" instructions
to generate additional tool calls for placing decorative elements.
"""
import os
import json
from typing import List, Dict, Any, Optional
from dataclasses import asdict

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

# Import shared tools and data structures
try:
    from v2.architect import BuildingInstruction, TOOL_DECLARATIONS
    from v2.carpenter import CarpenterSession
except ImportError:
    # Handle relative imports or other environments
    from .architect import BuildingInstruction, TOOL_DECLARATIONS
    from .carpenter import CarpenterSession

class Decorator:
    """
    The Decorator - adds details to the existing structure.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        if not HAS_GENAI:
            raise ImportError("google-genai package required")
        
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-3-pro-preview" 

    def _get_mime_type(self, path: str) -> str:
        ext = os.path.splitext(path)[1].lower()
        return {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}.get(ext, "image/jpeg")

    def _parse_response(self, response) -> List[BuildingInstruction]:
        """Parse function calls from response."""
        instructions = []
        for candidate in response.candidates:
            if not candidate.content or not candidate.content.parts:
                continue
            for part in candidate.content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    fc = part.function_call
                    params = dict(fc.args) if fc.args else {}
                    instructions.append(BuildingInstruction(
                        tool_name=fc.name,
                        parameters=params
                    ))
        return instructions

    def generate_decoration_plan(self, 
                                 image_path: str,
                                 concept_text: str,
                                 structure_blocks: List[Dict],
                                 building_info: Dict[str, Any]) -> List[BuildingInstruction]:
        """
        Compare the "Decorated Image" with the "Structure Blocks" (voxels) and generate
        additional tool calls for decorations.
        """
        with open(image_path, "rb") as f:
            image_data = f.read()

        width = building_info.get("position", {}).get("width", 50)
        depth = building_info.get("position", {}).get("depth", 50)
        
        # Filter relevant tools for decoration
        relevant_tools = [
            "place_decoration",
            "place_window", 
            "place_door",
            "draw_plane",       # For eaves, planters, wall layers
            "place_smart_pillar", # For adding depth/columns
            "draw_curve_loft"   # For awnings/arch details
        ]
        
        deco_tool_defs = [
            t for t in TOOL_DECLARATIONS 
            if t["name"] in relevant_tools
        ]

        # Define valid decoration blocks by category (expanded)
        VALID_DECOR_BLOCKS = {
            "Lighting": [
                "lantern", "soul_lantern", "torch", "redstone_lamp", "end_rod", "sea_lantern",
                "glowstone", "shroomlight", "campfire", "candle"
            ],
            "Plants": [
                "oak_leaves", "spruce_leaves", "flowering_azalea_leaves", "azalea_leaves", "jungle_leaves",
                "rose_bush", "peony", "lilac", "sunflower", "vine", "glow_lichen",
                "potted_red_tulip", "potted_blue_orchid", "potted_fern", "potted_bamboo", "flower_pot"
            ],
            "Fences & Walls": [
                "oak_fence", "spruce_fence", "dark_oak_fence", "birch_fence", "iron_bars",
                "cobblestone_wall", "stone_brick_wall", "mossy_stone_brick_wall", "andesite_wall",
                "oak_trapdoor", "spruce_trapdoor", "dark_oak_trapdoor", "iron_trapdoor"
            ],
            "Furniture/Details": [
                "barrel", "chest", "lectern", "loom", "composter", "cauldron",
                "white_banner", "red_banner", "blue_banner", "yellow_banner",
                "oak_sign", "spruce_sign", "chain", "bell", "anvil", "grindstone"
            ],
             "Structural/Facade": [
                "stone_bricks", "cracked_stone_bricks", "mossy_stone_bricks",
                "deepslate_bricks", "deepslate_tiles", "polished_blackstone_bricks",
                "bricks", "quartz_pillar", "smooth_quartz",
                "oak_log", "spruce_log", "dark_oak_log", "stripped_oak_log", "stripped_spruce_log",
                "white_concrete", "white_wool" # For timber framing look
            ]
        }
        
        # Flatten for prompt
        categories_str = ""
        for cat, blocks in VALID_DECOR_BLOCKS.items():
            categories_str += f"- {cat}: {', '.join(blocks)}\n"

        system_prompt = f"""You are a Minecraft Renovation Architect.
Your goal is to TRANSFORM a basic "box-like" building into a detailed, high-quality structure matching the Concept Image.

**CRITICAL RULE: DO NOT BUILD A "CURTAIN WALL" IN FRONT OF THE BUILDING.**
- You must MODIFY the existing surface or attach DISCRETE elements (pillars, beams) to it.
- **Do NOT** cover the entire facade with a single `draw_plane` layer.

CONTEXT:
- You are provided with the EXACT VOXEL BLOCKS of the current basic structure.

Your transformation tasks:

1. **ADD DEPTH (Structural Elements, NOT Walls)**:
   - Identify the corners and structural intervals (every 3-5 blocks).
   - Use `place_smart_pillar` to add columns attached to the wall surface.
   - Use `draw_line` (or generic block placement) for horizontal beams.
   - **Restriction**: Do NOT use `draw_plane` for vertical walls. Use it only for roofs or floor extensions.

2. **REPLACE & TEXTURE (In-place Modification)**:
   - Instead of building *in front* of the wall, **REPLACE** existing blocks to change the material.
   - Example: If the base needs to be stone, change the blocks at Y=0-1 to Stone by placing a new block at the **SAME COORDINATE**.
   - Create gradients (e.g., Stone -> Cobblestone -> Wood).

3. **ADD PROTRUSIONS (Discrete Details)**:
   - Add Eaves/Overhangs to roofs using `draw_plane` (only for horizontal/diagonal projections).
   - Add Window Planters/Sills individually.
   - Ensure these additions leave the original wall visible in between.

4. **MAXIMALIST DECORATION**:
   - Fill empty spots with leaves, vines, lanterns, banners, barrels.
   - Make it look "lived-in" and organic.

5. **LEAF PLACEMENT (FREEDOM)**:
   - Place leaves FREELY to create floating hedges or vines.
   - (System handles decay prevention automatically).

VALID BLOCK ID LIST:
{categories_str}

COORDINATE SYSTEM:
- X: 0 to {width}, Z: 0 to {depth}, Y: 0 = ground
- **Targeting**:
    - To CHANGE wall material: Use the EXACT coordinates of the wall.
    - To ADD depth: Place pillars/decorations adjacent to the wall (Offset by 1), but NEVER cover the whole face.

TOOLS:
- place_smart_pillar: ESSENTIAL for vertical columns.
- draw_plane: ONLY for Roofs, Floors, or Awnings. **BANNED for vertical facades.**
- place_decoration: Use to change materials (at same coord) or add props.
- place_window: Add/Refine windows.
- place_door: Refine entrances.
"""

        facing = building_info.get("facing", "unknown")
        
        # --- SMART BLOCK SELECTION (Front Facade Extraction) ---
        # Instead of random slicing, we select blocks that belong to the FRONT facade.
        # This reduces token count while maximizing relevance for the Renovator.
        
        def extract_front_facade(blocks, facing, limit=1500):
            if not blocks: return []
            
            # --- SURFACE SKINNING (Depth Map Approach) ---
            # Instead of a slice, we pick the visible surface block for each (u, v) coordinate.
            # This prevents picking internal walls or furniture.
            
            f = facing.lower()
            surface_map = {} # Key: (u, v), Value: Block
            
            for b in blocks:
                x, y, z = b['x'], b['y'], b['z']
                
                if "north" in f: # Looking at Negative Z (so front is Lowest Z)
                    key = (x, y)
                    # Keep if Z is smaller (closer to North)
                    if key not in surface_map or z < surface_map[key]['z']:
                        surface_map[key] = b
                
                elif "south" in f: # Looking at Positive Z (Front is Highest Z)
                    key = (x, y)
                    # Keep if Z is larger
                    if key not in surface_map or z > surface_map[key]['z']:
                        surface_map[key] = b
                        
                elif "west" in f: # Looking at Negative X (Front is Lowest X)
                    key = (z, y)
                    # Keep if X is smaller
                    if key not in surface_map or x < surface_map[key]['x']:
                        surface_map[key] = b
                        
                elif "east" in f: # Looking at Positive X (Front is Highest X)
                    key = (z, y)
                    # Keep if X is larger
                    if key not in surface_map or x > surface_map[key]['x']:
                        surface_map[key] = b
                
                else: 
                     # Fallback to slice
                     return blocks[:limit]

            # Convert map back to list
            facade = list(surface_map.values())
            
            # Optional: Add 1 layer of depth? (e.g. the block behind strict surface)
            # Maybe too risky. Stick to strict skin for now to solve "Fake Wall".
            
            # Subsample if needed
            if len(facade) > limit:
                step = len(facade) // limit
                facade = facade[::step]
                
            return facade

        sample_blocks = extract_front_facade(structure_blocks, facing)
        print(f"  🧱 Extracted {len(sample_blocks)} blocks for {facing} facade (from {len(structure_blocks)} total).")
        
        # Calculate Dominant Facade Plane
        facade_plane_msg = ""
        if sample_blocks:
            try:
                if "north" in facing.lower(): # Front is Min Z
                    wall_z = min(b['z'] for b in sample_blocks)
                    facade_plane_msg = f"**WALL POSITION**: The main facade wall is at **Z = {wall_z}**.\n   - DECORATIONS MUST BE AT **Z = {wall_z-1} or {wall_z-2}** (Smaller Z).\n   - **ABSOLUTELY NO BLOCKS AT Z > {wall_z}** (Inside Building)."
                elif "south" in facing.lower(): # Front is Max Z
                    wall_z = max(b['z'] for b in sample_blocks)
                    facade_plane_msg = f"**WALL POSITION**: The main facade wall is at **Z = {wall_z}**.\n   - DECORATIONS MUST BE AT **Z = {wall_z+1} or {wall_z+2}** (Larger Z).\n   - **ABSOLUTELY NO BLOCKS AT Z < {wall_z}** (Inside Building)."
                elif "west" in facing.lower(): # Front is Min X
                    wall_x = min(b['x'] for b in sample_blocks)
                    facade_plane_msg = f"**WALL POSITION**: The main facade wall is at **X = {wall_x}**.\n   - DECORATIONS MUST BE AT **X = {wall_x-1} or {wall_x-2}** (Smaller X).\n   - **ABSOLUTELY NO BLOCKS AT X > {wall_x}** (Inside Building)."
                elif "east" in facing.lower(): # Front is Max X
                    wall_x = max(b['x'] for b in sample_blocks)
                    facade_plane_msg = f"**WALL POSITION**: The main facade wall is at **X = {wall_x}**.\n   - DECORATIONS MUST BE AT **X = {wall_x+1} or {wall_x+2}** (Larger X).\n   - **ABSOLUTELY NO BLOCKS AT X < {wall_x}** (Inside Building)."
            except:
                pass

        user_prompt = f"""
# Concept Theme
{concept_text}

# Context
**Building Facing**: {facing.upper()}
The front entrance is on the {facing} side.

# Existing Structure BLOCKS (Front Facade ONLY)
Format: {{'x': int, 'y': int, 'z': int, 'type': str}}
{json.dumps(sample_blocks, indent=None)}

# Task
Compate the Basic Structure to the High-Quality Concept Image.
PERFORM A SUBSTANTIAL RENOVATION on this facade.

**CRITICAL: ATTACHMENT & DEPTH RULE**
{facade_plane_msg}
- You MUST attach your decorations TO or IMMEDIATELY IN FRONT of these blocks.
- **DO NOT** create a new wall 5 blocks away (No "Haribote" / Fake Walls).
- **DO NOT** create floating objects (doors/fences in air).
- **DO NOT** build INSIDE the building (Check the Forbidden Zone above).

**PRIORITY: FRONT FACADE ({facing.upper()})**
- This side must be the most detailed.
- Add a GRAND ENTRANCE here (Attached to the wall!).
- Add "Micro-Details" to the street level of the front:
    - Market Stalls / Carts (Ground level)
    - Benches / Street Lamps (Ground level)
    - Potted Plants (Against wall)

**General Improvements:**
1. Add PILLARS and BEAMS to break up flat walls.
2. Add EAVES/ROOF OVERHANGS.
3. Add FENCES, TRAPDOORS, LEAVES for fine detail.
4. Leaf placement is FREE (no decay). Use vines/hedges generously.
"""

        contents = [
            types.Part.from_bytes(data=image_data, mime_type=self._get_mime_type(image_path)),
            user_prompt
        ]
        
        tool_config = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name=tool["name"],
                    description=tool["description"],
                    parameters=tool["parameters"]
                )
                for tool in deco_tool_defs
            ]
        )

        print("  🎨 Decorator: Analyzing image & structure...")
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[tool_config],
                temperature=0.5,
            )
        )
        
        instructions = self._parse_response(response)
        print(f"  ✨ Generated {len(instructions)} decoration steps.")
        return instructions
