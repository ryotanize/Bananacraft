"""
Carpenter's Toolbox - Building tools for Bananacraft 2.0
"""
from .base import BaseTool
from .plane import PlaneTool
from .wall import DrawWallTool
from .pillar import PlacePillarTool
from .window import PlaceWindowTool
from .door import PlaceDoorTool
from .decoration import PlaceDecorationTool
from .curve import CurveLoftTool
from .infrastructure import DrawRoadTool, FillZoneTool, PlaceStreetDecorTool

# Tool registry - maps tool names to their implementations
TOOL_REGISTRY = {
    "draw_wall": DrawWallTool,
    "place_smart_pillar": PlacePillarTool,
    "draw_plane": PlaneTool,
    "place_window": PlaceWindowTool,
    "place_door": PlaceDoorTool,
    "place_decoration": PlaceDecorationTool,
    "draw_curve_loft": CurveLoftTool,
    "draw_road": DrawRoadTool,
    "fill_zone": FillZoneTool,
    "place_street_decor": PlaceStreetDecorTool,
}

__all__ = [
    "BaseTool",
    "PlaneTool",
    "DrawWallTool",
    "PlacePillarTool",
    "CurveLoftTool",
    "PlaceWindowTool",
    "PlaceDoorTool",
    "PlaceDecorationTool",
    "DrawRoadTool",
    "FillZoneTool",
    "PlaceStreetDecorTool",
    "TOOL_REGISTRY"
]
