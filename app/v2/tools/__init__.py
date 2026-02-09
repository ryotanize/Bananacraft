"""
Tools Registry for Bananacraft 2.0
"""
from .wall import DrawWallTool
from .plane import PlaneTool
from .curve import CurveLoftTool
from .pillar import PlacePillarTool
from .window import PlaceWindowTool
from .door import PlaceDoorTool
from .decoration import PlaceDecorationTool
from .infrastructure import DrawRoadTool, FillZoneTool, PlaceStreetDecorTool
# New
from .detailer import DecorateElementTool

TOOL_REGISTRY = {
    # Structure
    "draw_wall": DrawWallTool,
    "draw_plane": PlaneTool,
    "place_smart_pillar": PlacePillarTool,
    "draw_curve_loft": CurveLoftTool,
    "place_window": PlaceWindowTool,
    "place_door": PlaceDoorTool,
    
    # Old Decoration (Legacy support)
    "place_decoration": PlaceDecorationTool,
    
    # New Phase 3 Decoration
    "decorate_element": DecorateElementTool,
    
    # Infrastructure
    "draw_road": DrawRoadTool,
    "fill_zone": FillZoneTool,
    "place_street_decor": PlaceStreetDecorTool,
}

__all__ = ["TOOL_REGISTRY"]