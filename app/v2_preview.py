#!/usr/bin/env python
"""
Bananacraft 2.0 - AI Architect Preview App

A standalone Streamlit app for testing Gemini's building instruction generation
and previewing the results in 3D.
"""
import streamlit as st
import os
import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from v2.carpenter import CarpenterSession
from v2.preview import create_3d_preview_colored_by_type, get_block_statistics
from v2.architect import Architect, BuildingInstruction, HAS_GENAI

# Page config
st.set_page_config(
    page_title="Bananacraft 2.0 - AI Architect",
    page_icon="🍌",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .main-header { 
        font-size: 2.5rem; 
        font-weight: bold;
        background: linear-gradient(90deg, #FFD700, #FFA500);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .block-stat { 
        background: #1E2130; 
        padding: 1rem; 
        border-radius: 0.5rem;
        border-left: 3px solid #FFD700;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<p class="main-header">🍌 Bananacraft 2.0 - AI Architect</p>', unsafe_allow_html=True)
st.caption("Gemini 3 Pro による建築指示書生成と3Dプレビュー")

# Initialize session state
if 'blocks' not in st.session_state:
    st.session_state.blocks = []
if 'instructions' not in st.session_state:
    st.session_state.instructions = []
if 'raw_json' not in st.session_state:
    st.session_state.raw_json = ""

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    # API Key
    api_key = st.text_input("Gemini API Key", type="password", 
                            value=os.getenv("GEMINI_API_KEY", ""))
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key
    
    st.divider()
    
    # Building parameters
    st.subheader("🏗️ Building Area")
    origin_x = st.number_input("Origin X", value=0, step=10)
    origin_y = st.number_input("Origin Y (Ground)", value=64, step=1)
    origin_z = st.number_input("Origin Z", value=0, step=10)
    
    width = st.number_input("Width (X)", value=30, min_value=5, max_value=100)
    depth = st.number_input("Depth (Z)", value=30, min_value=5, max_value=100)
    
    st.divider()
    
    # Quick presets
    st.subheader("🎨 Quick Presets")
    if st.button("Simple House"):
        st.session_state.raw_json = json.dumps([
            {"tool": "draw_wall", "parameters": {"start": [0, 0, 0], "end": [15, 6, 0], "material": "stone_bricks", "window_pattern": "grid_2x2"}},
            {"tool": "draw_wall", "parameters": {"start": [0, 0, 15], "end": [15, 6, 15], "material": "stone_bricks", "window_pattern": "grid_2x2"}},
            {"tool": "draw_wall", "parameters": {"start": [0, 0, 0], "end": [0, 6, 15], "material": "stone_bricks"}},
            {"tool": "draw_wall", "parameters": {"start": [15, 0, 0], "end": [15, 6, 15], "material": "stone_bricks"}},
            {"tool": "place_smart_pillar", "parameters": {"base": [0, 0, 0], "top": [0, 6, 0], "material": "stone_bricks", "style": "classical"}},
            {"tool": "place_smart_pillar", "parameters": {"base": [15, 0, 0], "top": [15, 6, 0], "material": "stone_bricks", "style": "classical"}},
            {"tool": "place_smart_pillar", "parameters": {"base": [0, 0, 15], "top": [0, 6, 15], "material": "stone_bricks", "style": "classical"}},
            {"tool": "place_smart_pillar", "parameters": {"base": [15, 0, 15], "top": [15, 6, 15], "material": "stone_bricks", "style": "classical"}},
        ], indent=2)
        st.rerun()
    
    if st.button("Station Canopy"):
        st.session_state.raw_json = json.dumps([
            {"tool": "draw_curve_loft", "parameters": {
                "curve_a": {"start": [0, 5, 0], "end": [25, 5, 0], "control_height": 12},
                "curve_b": {"start": [0, 5, 20], "end": [25, 5, 20], "control_height": 12},
                "frame_material": "iron_block", "fill_material": "glass", "pattern": "grid_4x4"
            }},
            {"tool": "place_smart_pillar", "parameters": {"base": [0, 0, 0], "top": [0, 5, 0], "material": "iron_block", "style": "modern"}},
            {"tool": "place_smart_pillar", "parameters": {"base": [25, 0, 0], "top": [25, 5, 0], "material": "iron_block", "style": "modern"}},
            {"tool": "place_smart_pillar", "parameters": {"base": [0, 0, 20], "top": [0, 5, 20], "material": "iron_block", "style": "modern"}},
            {"tool": "place_smart_pillar", "parameters": {"base": [25, 0, 20], "top": [25, 5, 20], "material": "iron_block", "style": "modern"}},
            {"tool": "place_smart_pillar", "parameters": {"base": [12, 0, 0], "top": [12, 5, 0], "material": "iron_block", "style": "modern"}},
            {"tool": "place_smart_pillar", "parameters": {"base": [12, 0, 20], "top": [12, 5, 20], "material": "iron_block", "style": "modern"}},
        ], indent=2)
        st.rerun()

# Main content - two columns
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 Building Instructions")
    
    # Tabs for different input methods
    tab_manual, tab_ai = st.tabs(["📋 Manual JSON", "🤖 AI Generate"])
    
    with tab_manual:
        # JSON editor
        json_input = st.text_area(
            "Building Instructions (JSON)",
            value=st.session_state.raw_json,
            height=400,
            help="Enter building instructions as JSON array"
        )
        
        if st.button("🔨 Build from JSON", type="primary"):
            try:
                instructions = json.loads(json_input)
                session = CarpenterSession(origin=(origin_x, origin_y, origin_z))
                blocks = session.build_from_json(instructions)
                
                st.session_state.blocks = blocks
                st.session_state.instructions = instructions
                st.session_state.raw_json = json_input
                
                st.success(f"✅ Generated {len(blocks)} blocks!")
                st.rerun()
                
            except json.JSONDecodeError as e:
                st.error(f"❌ Invalid JSON: {e}")
            except Exception as e:
                st.error(f"❌ Build error: {e}")
    
    with tab_ai:
        st.markdown("### 🎨 AI建築指示書生成")
        
        if not HAS_GENAI:
            st.warning("⚠️ google-genai パッケージがインストールされていません")
        elif not api_key:
            st.warning("⚠️ サイドバーでAPI Keyを入力してください")
        else:
            # Image upload
            uploaded_file = st.file_uploader(
                "コンセプト画像をアップロード",
                type=["jpg", "jpeg", "png", "webp"],
                help="建物のコンセプトアートや設計図をアップロード"
            )
            
            if uploaded_file:
                st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)
            
            # Building description
            description = st.text_area(
                "建物の説明",
                placeholder="例: 石レンガで作られた2階建ての家。アーチ型の窓が特徴。",
                height=100
            )
            
            # Additional context
            style_hint = st.selectbox(
                "建築スタイル",
                ["クラシック (石造り)", "モダン (鉄とガラス)", "和風 (木造)", "ファンタジー", "産業風"]
            )
            
            if st.button("🤖 Geminiに建築を依頼", type="primary", disabled=not (uploaded_file or description)):
                with st.spinner("Gemini が建築プランを考えています..."):
                    try:
                        # Prepare building info
                        building_info = {
                            "name": "AI Generated Building",
                            "description": description or "Building from image",
                            "position": {
                                "x": 0, "z": 0,
                                "width": width,
                                "depth": depth
                            },
                            "decorations": []
                        }
                        
                        architect = Architect(api_key)
                        
                        if uploaded_file:
                            # Save temp file
                            temp_path = f"/tmp/bananacraft_upload.{uploaded_file.name.split('.')[-1]}"
                            with open(temp_path, "wb") as f:
                                f.write(uploaded_file.getvalue())
                            
                            instructions = architect.analyze_and_plan(
                                image_path=temp_path,
                                building_info=building_info,
                                additional_context=f"Style: {style_hint}. {description or ''}"
                            )
                        else:
                            # Text only
                            instructions = architect.generate_from_description(
                                description=f"{style_hint}. {description}",
                                building_info=building_info
                            )
                        
                        if instructions:
                            # Convert to JSON
                            json_instructions = [
                                {"tool": inst.tool_name, "parameters": inst.parameters}
                                for inst in instructions
                            ]
                            
                            st.session_state.raw_json = json.dumps(json_instructions, indent=2, ensure_ascii=False)
                            
                            # Build immediately
                            session = CarpenterSession(origin=(origin_x, origin_y, origin_z))
                            blocks = session.build_from_json(json_instructions)
                            
                            st.session_state.blocks = blocks
                            st.session_state.instructions = json_instructions
                            
                            st.success(f"✅ Gemini generated {len(instructions)} instructions → {len(blocks)} blocks!")
                            st.rerun()
                        else:
                            st.warning("⚠️ Gemini returned no building instructions")
                            
                    except Exception as e:
                        st.error(f"❌ AI Error: {e}")
                        import traceback
                        st.code(traceback.format_exc())

with col2:
    st.subheader("🎮 3D Preview")
    
    if st.session_state.blocks:
        # Statistics
        stats = get_block_statistics(st.session_state.blocks)
        
        cols = st.columns(4)
        with cols[0]:
            st.metric("Total Blocks", stats["total"])
        with cols[1]:
            st.metric("Width (X)", stats["dimensions"]["width"])
        with cols[2]:
            st.metric("Depth (Z)", stats["dimensions"]["depth"])
        with cols[3]:
            st.metric("Height (Y)", stats["dimensions"]["height"])
        
        # 3D Preview
        fig = create_3d_preview_colored_by_type(
            st.session_state.blocks,
            title=f"Building Preview ({stats['total']} blocks)"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Block distribution
        with st.expander("📊 Block Distribution"):
            for block_type, count in list(stats["type_distribution"].items())[:10]:
                percentage = count / stats["total"] * 100
                st.progress(percentage / 100, text=f"{block_type}: {count} ({percentage:.1f}%)")
        
        # Export options
        with st.expander("💾 Export"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.download_button(
                    "📥 Download Instructions (JSON)",
                    data=st.session_state.raw_json,
                    file_name="building_instructions.json",
                    mime="application/json"
                )
            with col_b:
                blocks_json = json.dumps(st.session_state.blocks, indent=2)
                st.download_button(
                    "📥 Download Blocks (JSON)",
                    data=blocks_json,
                    file_name="building_blocks.json",
                    mime="application/json"
                )
    else:
        st.info("👈 左側で建築指示を入力するか、AIに生成させてください")
        
        # Show placeholder
        st.markdown("""
        ### 使い方
        
        1. **Manual JSON**: 建築指示を直接JSONで入力
        2. **AI Generate**: 画像や説明からGeminiが建築指示を生成
        
        サイドバーの **Quick Presets** でサンプルを試せます！
        """)

# Footer
st.divider()
st.caption("Bananacraft 2.0 - Neuro-symbolic AI Architecture System")
