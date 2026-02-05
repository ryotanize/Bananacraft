"""
3D Preview module for Bananacraft 2.0

Provides Streamlit-compatible 3D visualization of block placements
using plotly for interactive 3D scatter plots.
"""
import plotly.graph_objects as go
from typing import List, Dict, Any, Optional
import numpy as np


# Minecraft block colors (approximate)
BLOCK_COLORS = {
    # Stone variants
    "stone": "#7F7F7F",
    "stone_bricks": "#7A7A7A",
    "cobblestone": "#6B6B6B",
    "andesite": "#8A8A8A",
    "diorite": "#C8C8C8",
    "granite": "#9B6B5B",
    "brick": "#8B4513",
    "bricks": "#8B4513",
    "nether_brick": "#2B1414",
    "deepslate": "#4A4A4A",
    
    # Glass
    "glass": "#ADD8E6",
    "glass_pane": "#ADD8E6",
    "white_stained_glass": "#FFFFFF",
    "light_blue_stained_glass": "#87CEEB",
    
    # Wood
    "oak_planks": "#B8945F",
    "oak_log": "#6B5038",
    "spruce_planks": "#5E4A32",
    "spruce_log": "#3B2816",
    "birch_planks": "#D5C98C",
    "dark_oak_planks": "#3E2912",
    
    # Metals
    "iron_block": "#D8D8D8",
    "gold_block": "#FFDF00",
    "copper_block": "#C17952",
    
    # Natural
    "grass_block": "#7CBA4E",
    "dirt": "#8B6914",
    "sand": "#DBCFA0",
    "sandstone": "#D9C97C",
    "red_sandstone": "#BA6A39",
    
    # Decorative
    "quartz_block": "#EBE8E4",
    "smooth_quartz": "#EBE8E4",
    "prismarine": "#639D94",
    "sea_lantern": "#9BEBE8",
    "glowstone": "#FFE87C",
    
    # Colored blocks
    "white_concrete": "#CFD5D6",
    "black_concrete": "#080A0F",
    "gray_concrete": "#36393D",
    "red_concrete": "#8E2121",
    "blue_concrete": "#2C2E8F",
    "green_concrete": "#495B24",
    
    # Default
    "default": "#808080",
}


def get_block_color(block_type: str) -> str:
    """Get the color for a block type."""
    # Remove minecraft: prefix if present
    if block_type.startswith("minecraft:"):
        block_type = block_type[10:]
    
    # Remove properties like [facing=north]
    if "[" in block_type:
        block_type = block_type.split("[")[0]
    
    # Check for slab/stairs variants
    for suffix in ["_slab", "_stairs", "_wall", "_fence"]:
        if block_type.endswith(suffix):
            base_type = block_type.replace(suffix, "")
            if base_type in BLOCK_COLORS:
                return BLOCK_COLORS[base_type]
    
    # Direct match
    if block_type in BLOCK_COLORS:
        return BLOCK_COLORS[block_type]
    
    # Partial match (e.g., "stone_brick_stairs" -> "stone_bricks")
    for key in BLOCK_COLORS:
        if key in block_type or block_type in key:
            return BLOCK_COLORS[key]
    
    return BLOCK_COLORS["default"]


def create_3d_preview(blocks: List[Dict], title: str = "Building Preview") -> go.Figure:
    """
    Create a 3D scatter plot visualization of blocks.
    
    Args:
        blocks: List of block dicts with x, y, z, type
        title: Title for the plot
        
    Returns:
        Plotly figure object
    """
    if not blocks:
        # Return empty figure
        fig = go.Figure()
        fig.add_annotation(text="No blocks to display", 
                          xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        return fig
    
    # Extract coordinates and colors
    x_coords = []
    y_coords = []
    z_coords = []
    colors = []
    hover_texts = []
    
    for block in blocks:
        x_coords.append(block["x"])
        y_coords.append(block["y"])
        z_coords.append(block["z"])
        
        block_type = block.get("type", "stone")
        colors.append(get_block_color(block_type))
        
        # Hover text
        clean_type = block_type.replace("minecraft:", "")
        hover_texts.append(f"{clean_type}<br>({block['x']}, {block['y']}, {block['z']})")
    
    # Create 3D scatter plot with cube-like markers
    fig = go.Figure(data=[go.Scatter3d(
        x=x_coords,
        y=z_coords,  # Swap Y/Z for Minecraft coordinate system
        z=y_coords,
        mode='markers',
        marker=dict(
            size=5,
            color=colors,
            opacity=0.9,
            symbol='square',
        ),
        hovertemplate="%{text}<extra></extra>",
        text=hover_texts,
    )])
    
    # Layout
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        scene=dict(
            xaxis_title='X',
            yaxis_title='Z',
            zaxis_title='Y (Height)',
            aspectmode='data',
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=0.5)
            )
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        height=600,
    )
    
    return fig


def create_3d_preview_colored_by_type(blocks: List[Dict], title: str = "Building Preview") -> go.Figure:
    """
    Create a 3D visualization with blocks grouped by type for legend.
    
    Better for understanding the structure composition.
    """
    if not blocks:
        fig = go.Figure()
        fig.add_annotation(text="No blocks to display", 
                          xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        return fig
    
    # Group blocks by type
    blocks_by_type = {}
    for block in blocks:
        block_type = block.get("type", "stone").replace("minecraft:", "")
        if "[" in block_type:
            block_type = block_type.split("[")[0]
        
        if block_type not in blocks_by_type:
            blocks_by_type[block_type] = []
        blocks_by_type[block_type].append(block)
    
    # Create traces for each block type
    traces = []
    for block_type, type_blocks in blocks_by_type.items():
        x_coords = [b["x"] for b in type_blocks]
        y_coords = [b["z"] for b in type_blocks]  # Swap for MC coords
        z_coords = [b["y"] for b in type_blocks]
        
        traces.append(go.Scatter3d(
            x=x_coords,
            y=y_coords,
            z=z_coords,
            mode='markers',
            name=block_type,
            marker=dict(
                size=5,
                color=get_block_color(f"minecraft:{block_type}"),
                opacity=0.9,
                symbol='square',
            ),
            hovertemplate=f"{block_type}<br>(%{{x}}, %{{z}}, %{{y}})<extra></extra>",
        ))
    
    fig = go.Figure(data=traces)
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        scene=dict(
            xaxis_title='X',
            yaxis_title='Z',
            zaxis_title='Y (Height)',
            aspectmode='data',
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=0.5)
            )
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        height=600,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.8)"
        )
    )
    
    return fig


def get_block_statistics(blocks: List[Dict]) -> Dict[str, Any]:
    """
    Calculate statistics about the block placement.
    """
    if not blocks:
        return {"total": 0}
    
    # Count by type
    type_counts = {}
    for block in blocks:
        block_type = block.get("type", "unknown").replace("minecraft:", "")
        if "[" in block_type:
            block_type = block_type.split("[")[0]
        type_counts[block_type] = type_counts.get(block_type, 0) + 1
    
    # Bounding box
    x_coords = [b["x"] for b in blocks]
    y_coords = [b["y"] for b in blocks]
    z_coords = [b["z"] for b in blocks]
    
    return {
        "total": len(blocks),
        "type_distribution": dict(sorted(type_counts.items(), key=lambda x: -x[1])),
        "bounding_box": {
            "x": (min(x_coords), max(x_coords)),
            "y": (min(y_coords), max(y_coords)),
            "z": (min(z_coords), max(z_coords)),
        },
        "dimensions": {
            "width": max(x_coords) - min(x_coords) + 1,
            "height": max(y_coords) - min(y_coords) + 1,
            "depth": max(z_coords) - min(z_coords) + 1,
        }
    }
