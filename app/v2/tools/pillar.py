"""
Pillar Tool - Creates pillars with optional decorative styles.
"""
from typing import List, Dict, Any
from .base import BaseTool, Block


class PlacePillarTool(BaseTool):
    """
    Creates a pillar (vertical column) between base and top points.
    
    Supports styles:
    - simple: Plain column
    - classical: With decorative capital and base using stairs
    - modern: Clean lines with slab accents
    """
    
    name = "place_smart_pillar"
    description = "Creates a vertical pillar with optional decorative style"
    
    # Stair block mappings for classical style
    STAIR_MATERIALS = {
        "stone_bricks": "stone_brick_stairs",
        "stone_brick": "stone_brick_stairs",
        "quartz_block": "quartz_stairs",
        "smooth_quartz": "smooth_quartz_stairs",
        "brick": "brick_stairs",
        "bricks": "brick_stairs",
        "sandstone": "sandstone_stairs",
        "oak_planks": "oak_stairs",
        "spruce_planks": "spruce_stairs",
        "cobblestone": "cobblestone_stairs",
        "andesite": "andesite_stairs",
        "diorite": "diorite_stairs",
        "granite": "granite_stairs",
        "prismarine": "prismarine_stairs",
        "dark_prismarine": "dark_prismarine_stairs",
        "nether_brick": "nether_brick_stairs",
        "red_nether_bricks": "red_nether_brick_stairs",
        "purpur_block": "purpur_stairs",
        "end_stone_bricks": "end_stone_brick_stairs",
        "blackstone": "blackstone_stairs",
        "polished_blackstone": "polished_blackstone_stairs",
        "deepslate_bricks": "deepslate_brick_stairs",
        "deepslate_tiles": "deepslate_tile_stairs",
    }
    
    SLAB_MATERIALS = {
        "stone_bricks": "stone_brick_slab",
        "stone_brick": "stone_brick_slab",
        "quartz_block": "quartz_slab",
        "smooth_quartz": "smooth_quartz_slab",
        "brick": "brick_slab",
        "bricks": "brick_slab",
        "sandstone": "sandstone_slab",
        "oak_planks": "oak_slab",
        "spruce_planks": "spruce_slab",
        "cobblestone": "cobblestone_slab",
    }
    
    def execute(self, params: Dict[str, Any], origin: tuple = (0, 0, 0)) -> List[Block]:
        """
        Execute pillar creation.
        
        Args:
            params: {
                "base": [x, y, z],
                "top": [x, y, z],
                "material": str,
                "style": Optional[str] ("simple", "classical", "modern")
            }
            origin: World origin offset
        """
        base = params.get("base", [0, 0, 0])
        top = params.get("top", [0, 0, 0])
        material = params.get("material", "stone_bricks")
        style = params.get("style", "simple")
        
        # Apply origin offset
        ox, oy, oz = origin
        x = base[0] + ox
        z = base[2] + oz
        y_min = min(base[1], top[1]) + oy
        y_max = max(base[1], top[1]) + oy
        
        blocks: List[Block] = []
        
        if style == "classical":
            blocks.extend(self._create_classical_pillar(x, y_min, y_max, z, material))
        elif style == "modern":
            blocks.extend(self._create_modern_pillar(x, y_min, y_max, z, material))
        else:  # simple
            blocks.extend(self._create_simple_pillar(x, y_min, y_max, z, material))
        
        return blocks
    
    def _create_simple_pillar(self, x: int, y_min: int, y_max: int, z: int, material: str) -> List[Block]:
        """Create a simple vertical column."""
        blocks = []
        for y in range(y_min, y_max + 1):
            blocks.append(Block(x, y, z, material))
        return blocks
    
    def _create_classical_pillar(self, x: int, y_min: int, y_max: int, z: int, material: str) -> List[Block]:
        """
        Create a classical pillar with decorative capital and base.
        
        Uses stairs facing outward at top (capital) and bottom (base).
        """
        blocks = []
        height = y_max - y_min + 1
        
        # Get stair material
        stair = self.STAIR_MATERIALS.get(material, f"{material}_stairs")
        
        # Base decoration (bottom layer with stairs facing outward)
        if height >= 3:
            # Four stairs around the base
            for facing, (dx, dz) in [
                ("north", (0, -1)),
                ("south", (0, 1)),
                ("east", (1, 0)),
                ("west", (-1, 0))
            ]:
                blocks.append(Block(x + dx, y_min, z + dz, f"{stair}[facing={facing}]"))
        
        # Main shaft
        for y in range(y_min, y_max + 1):
            blocks.append(Block(x, y, z, material))
        
        # Capital decoration (top layer with stairs facing outward, upside down)
        if height >= 3:
            for facing, (dx, dz) in [
                ("north", (0, -1)),
                ("south", (0, 1)),
                ("east", (1, 0)),
                ("west", (-1, 0))
            ]:
                blocks.append(Block(x + dx, y_max, z + dz, f"{stair}[facing={facing},half=top]"))
        
        return blocks
    
    def _create_modern_pillar(self, x: int, y_min: int, y_max: int, z: int, material: str) -> List[Block]:
        """
        Create a modern-style pillar with clean lines.
        
        Uses slabs at transitions for subtle accent.
        """
        blocks = []
        height = y_max - y_min + 1
        
        # Get slab material
        slab = self.SLAB_MATERIALS.get(material, f"{material}_slab")
        
        # Slim base (slab on bottom)
        if height >= 4:
            blocks.append(Block(x, y_min, z, f"{slab}[type=bottom]"))
            start_y = y_min + 1
        else:
            start_y = y_min
        
        # Main shaft
        end_y = y_max - 1 if height >= 4 else y_max
        for y in range(start_y, end_y + 1):
            blocks.append(Block(x, y, z, material))
        
        # Slim cap (slab on top)
        if height >= 4:
            blocks.append(Block(x, y_max, z, f"{slab}[type=top]"))
        
        return blocks
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate pillar parameters."""
        required = ["base", "top", "material"]
        for key in required:
            if key not in params:
                return False
        
        base = params.get("base", [])
        top = params.get("top", [])
        
        if len(base) != 3 or len(top) != 3:
            return False
        
        # Base and top should have same X and Z
        if base[0] != top[0] or base[2] != top[2]:
            # This is okay - we'll use base's X,Z
            pass
        
        return True
