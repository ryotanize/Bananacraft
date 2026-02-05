"""
Base class for all Carpenter tools.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class Block:
    """Represents a single Minecraft block placement."""
    
    def __init__(self, x: int, y: int, z: int, block_type: str):
        self.x = x
        self.y = y
        self.z = z
        self.type = block_type
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "type": f"minecraft:{self.type}" if not self.type.startswith("minecraft:") else self.type
        }
    
    def __repr__(self):
        return f"Block({self.x}, {self.y}, {self.z}, '{self.type}')"
    
    def __eq__(self, other):
        if not isinstance(other, Block):
            return False
        return (self.x, self.y, self.z, self.type) == (other.x, other.y, other.z, other.type)
    
    def __hash__(self):
        return hash((self.x, self.y, self.z, self.type))


class BaseTool(ABC):
    """
    Abstract base class for all building tools.
    
    Each tool receives parameters from Gemini's function call
    and returns a list of Block objects to be placed.
    """
    
    name: str = "base_tool"
    description: str = "Base tool"
    
    @abstractmethod
    def execute(self, params: Dict[str, Any], origin: tuple = (0, 0, 0)) -> List[Block]:
        """
        Execute the tool with given parameters.
        
        Args:
            params: Dictionary of parameters from Gemini's function call
            origin: World coordinates (x, y, z) for the building area origin
            
        Returns:
            List of Block objects to be placed
        """
        pass
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """
        Validate the parameters before execution.
        Override in subclasses for specific validation.
        """
        return True
