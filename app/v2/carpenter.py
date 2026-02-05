"""
Carpenter - Tool execution engine for Bananacraft 2.0

The Carpenter receives building instructions from the Architect
and executes them using the registered tools, generating block
coordinates for Minecraft.
"""
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .tools import TOOL_REGISTRY
from .tools.base import Block


@dataclass
class BuildResult:
    """Result of a building operation."""
    success: bool
    blocks: List[Block]
    tool_name: str
    message: str = ""


class Carpenter:
    """
    The Carpenter - executes building instructions.
    
    Takes BuildingInstructions from the Architect and converts them
    into actual block placements using the tool registry.
    """
    
    def __init__(self, origin: tuple = (0, 64, 0)):
        """
        Initialize the Carpenter.
        
        Args:
            origin: World coordinates (x, y, z) for the building area origin.
                    Y=64 is typical ground level in default Minecraft worlds.
        """
        self.origin = origin
        self.tools = {}
        self._register_tools()
    
    def _register_tools(self):
        """Initialize all available tools."""
        for name, tool_class in TOOL_REGISTRY.items():
            self.tools[name] = tool_class()
    
    def execute_instruction(self, instruction: 'BuildingInstruction') -> BuildResult:
        """
        Execute a single building instruction.
        
        Args:
            instruction: BuildingInstruction from the Architect
            
        Returns:
            BuildResult with blocks to place
        """
        tool_name = instruction.tool_name
        params = instruction.parameters
        
        # Check if tool exists
        if tool_name not in self.tools:
            return BuildResult(
                success=False,
                blocks=[],
                tool_name=tool_name,
                message=f"Unknown tool: {tool_name}"
            )
        
        tool = self.tools[tool_name]
        
        # Validate parameters
        if not tool.validate_params(params):
            return BuildResult(
                success=False,
                blocks=[],
                tool_name=tool_name,
                message=f"Invalid parameters for {tool_name}"
            )
        
        # Execute tool
        try:
            blocks = tool.execute(params, self.origin)
            return BuildResult(
                success=True,
                blocks=blocks,
                tool_name=tool_name,
                message=f"Generated {len(blocks)} blocks"
            )
        except Exception as e:
            return BuildResult(
                success=False,
                blocks=[],
                tool_name=tool_name,
                message=f"Execution error: {str(e)}"
            )
    
    def execute_all(self, instructions: List['BuildingInstruction']) -> List[BuildResult]:
        """
        Execute all building instructions.
        
        Args:
            instructions: List of BuildingInstructions from the Architect
            
        Returns:
            List of BuildResults
        """
        results = []
        for instruction in instructions:
            result = self.execute_instruction(instruction)
            results.append(result)
        return results
    
    def build(self, instructions: List['BuildingInstruction']) -> List[Dict]:
        """
        Execute instructions and return all blocks as dicts.
        
        This is the main entry point for building operations.
        Returns blocks in the format expected by RconClient.
        
        Args:
            instructions: List of BuildingInstructions
            
        Returns:
            List of block dicts: [{"x": int, "y": int, "z": int, "type": str}, ...]
        """
        all_blocks = []
        seen = set()  # Deduplicate blocks at same position
        
        for instruction in instructions:
            result = self.execute_instruction(instruction)
            
            if result.success:
                for block in result.blocks:
                    pos = (block.x, block.y, block.z)
                    if pos not in seen:
                        seen.add(pos)
                        all_blocks.append(block.to_dict())
        
        return all_blocks
    
    def set_origin(self, x: int, y: int, z: int):
        """Update the building origin."""
        self.origin = (x, y, z)
    
    def preview_instruction(self, instruction: 'BuildingInstruction') -> Dict:
        """
        Preview an instruction without executing.
        
        Returns information about what would be built.
        """
        tool_name = instruction.tool_name
        params = instruction.parameters
        
        return {
            "tool": tool_name,
            "params": params,
            "valid": tool_name in self.tools and self.tools[tool_name].validate_params(params)
        }


class CarpenterSession:
    """
    A session manager for building operations.
    
    Coordinates between Architect and Carpenter, maintaining
    state and providing high-level building APIs.
    """
    
    def __init__(self, origin: tuple = (0, 64, 0)):
        self.carpenter = Carpenter(origin)
        self.instructions_history: List = []
        self.blocks_placed: List[Dict] = []
    
    def build_from_instructions(self, instructions: List['BuildingInstruction']) -> List[Dict]:
        """
        Execute building instructions and track history.
        
        Returns:
            List of block dicts ready for RCON placement
        """
        blocks = self.carpenter.build(instructions)
        
        self.instructions_history.extend(instructions)
        self.blocks_placed.extend(blocks)
        
        return blocks
    
    def build_from_json(self, json_instructions: List[Dict]) -> List[Dict]:
        """
        Build from raw JSON instruction format.
        
        Expected format:
        [
            {
                "tool": "draw_wall",
                "parameters": {...}
            },
            ...
        ]
        """
        from .architect import BuildingInstruction
        
        instructions = [
            BuildingInstruction(
                tool_name=item.get("tool", item.get("tool_name", "")),
                parameters=item.get("parameters", item.get("params", {}))
            )
            for item in json_instructions
        ]
        
        return self.build_from_instructions(instructions)
    
    def get_stats(self) -> Dict:
        """Get statistics about the current session."""
        return {
            "total_instructions": len(self.instructions_history),
            "total_blocks": len(self.blocks_placed),
            "origin": self.carpenter.origin
        }
    
    def clear(self):
        """Clear the session history."""
        self.instructions_history = []
        self.blocks_placed = []
    
    def export_blocks_json(self) -> str:
        """Export placed blocks as JSON string."""
        return json.dumps(self.blocks_placed, indent=2)

    def run_bot(self, project_name: str, target_file: str, origin: Optional[tuple] = None):
        """
        Run the external Node.js AI Carpenter Bot.
        
        Args:
            project_name: Name of the project (folder name in projects/)
            target_file: Name of the JSON file in the project folder (e.g. 'decoration.json')
            origin: Optional (x, y, z) tuple to override bot origin.
        """
        import subprocess
        import os
        import sys

        # Resolve paths
        # Assuming app/v2/carpenter.py -> .../app/v2/ -> .../app/ -> .../root
        # The bot is in root/AI_Carpenter_Bot
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
        bot_dir = os.path.join(root_dir, "AI_Carpenter_Bot")
        index_js = os.path.join(bot_dir, "index.js")
        
        if not os.path.exists(index_js):
            # Fallback for deployment structure where AI_Carpenter_Bot might be sibling to app
            # root/app, root/AI_Carpenter_Bot
            root_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
            bot_dir = os.path.join(root_dir, "AI_Carpenter_Bot")
            index_js = os.path.join(bot_dir, "index.js")

        cmd = ["node", index_js, project_name]
        
        if origin:
            cmd.extend([str(origin[0]), str(origin[1]), str(origin[2])])
        else:
            # Pass placeholder args if origin is not set but file is needed?
            # index.js expects: <PROJECT> [X] [Y] [Z] [FILE]
            # If we want to skip origin but pass file, we might need dummy args or update index.js
            # Based on index.js logic:
            # const argX = process.argv[3]
            # const argFile = process.argv[6]
            # It seems strict on position.
            # If origin is None, we shouldn't pass it?
            # But index.js checks: if (argX && argY && argZ)
            # So if we want to pass filename without origin, we might need to modify index.js or pass 0 0 0?
            # Waait, let's look at index.js:
            # const argFile = process.argv[6]
            # It explicitly grabs index 6. So we MUST provide 3, 4, 5 if we want 6.
            # But if origin is None, we usually sync with player.
            # We can pass empty strings?
            # Let's pass "0" "0" "0" and handle it? 
            # Or better, update index.js to use a flag parser if I could, but simple is better.
            # If origin is None, we probably want the bot to find the player. 
            pass

        # If we have a target file, we MUST provide X, Y, Z or placeholders to reach argv[6]
        if target_file:
            if not origin:
                # Use empty strings or 0? 
                # If we pass "0" "0" "0", the bot will use that as origin.
                # If we want 'find player' behavior + specific file, index.js doesn't support it easily 
                # because `if (argX && ...)` will be true.
                # I should just update index.js to be smarter OR just always ensure we have an origin in Phase 3.
                pass
            
            # The current Phase 3 UI knows the origin! 
            # `current_origin` is available in main.py.
            pass

        # Let's assume we always pass origin if we are automating.
        if origin:
             cmd.extend([str(origin[0]), str(origin[1]), str(origin[2])])
        else:
             # Add dummies if we really need to pass file
             cmd.extend(["", "", ""]) # Node might treat empty string as falsey?
        
        if target_file:
            cmd.append(target_file)

        # Run
        # We use Popen to capture output real-time? 
        # Or simple run if we just want to wait.
        # Streamlit spinner covers the wait.
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=bot_dir # Run from bot dir so it finds node_modules
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Bot Error: {stderr}\nOutput: {stdout}")
        
        return stdout



# Convenience function for direct building
def build_from_json(json_data: List[Dict], origin: tuple = (0, 64, 0)) -> List[Dict]:
    """
    Convenience function to build from JSON instructions.
    
    Args:
        json_data: List of tool instructions
        origin: World origin (x, y, z)
        
    Returns:
        List of block dicts ready for RCON
    """
    session = CarpenterSession(origin)
    return session.build_from_json(json_data)
