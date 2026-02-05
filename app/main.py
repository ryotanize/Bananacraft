import streamlit as st
import time
import pandas as pd
import altair as alt
import json
import os
import requests
import base64
from dotenv import load_dotenv
from dotenv import load_dotenv
load_dotenv()

# Fix path for imports when running via Streamlit from root
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from api_client import GeminiClient
from api_client import GeminiClient
from meshy_client import MeshyClient
# Legacy voxelizer import commented out
# from voxelizer import Voxelizer

# New BVH Ray-Cast Voxelizer
from voxelizer.mesh_loader import load_mesh
from voxelizer.bvh_ray_voxelizer import voxelize_mesh
from voxelizer.block_assigner import BlockAssigner
import plotly.graph_objects as go
import pandas as pd
from file_manager import FileManager 
from rcon_client import RconClient
from terraformer import Terraformer 

# v2 Imports
from v2.architect import Architect
from v2.carpenter import CarpenterSession
from v2.decorator import Decorator
from v2.preview import create_3d_preview 

# --- Page Configuration ---
st.set_page_config(
    page_title="Bananacraft Architect",
    page_icon="🍌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stButton>button { color: #0E1117; background-color: #F63366; border: none; font-weight: bold; }
    h1, h2, h3 { font-family: 'Helvetica Neue', sans-serif; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if 'phase' not in st.session_state:
    st.session_state.phase = 0 # 0 = Project Setup
if 'project_name' not in st.session_state:
    st.session_state.project_name = ""
if 'architect' not in st.session_state:
    st.session_state.architect = None
if 'carpenter_session' not in st.session_state:
    st.session_state.carpenter_session = None
if 'file_manager' not in st.session_state:
    st.session_state.file_manager = None
if 'gemini_client' not in st.session_state:
    st.session_state.gemini_client = None
if 'chat_session' not in st.session_state:
    st.session_state.chat_session = None

if 'concept' not in st.session_state:
    st.session_state.concept = None # {title, description, image_bytes}
if 'zoning' not in st.session_state:
    st.session_state.zoning = None
if 'selected_zone' not in st.session_state:
    st.session_state.selected_zone = None
# For Design Phase
if 'design_images' not in st.session_state:
    st.session_state.design_images = None

# --- Sidebar ---
with st.sidebar:
    st.title("🍌 Bananacraft")
    st.caption("AI都市開発システム")
    
    # API Key Input
    api_key = st.text_input("Gemini API Key", type="password")
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key
    
    st.divider()
    if st.session_state.phase > 0:
        st.info(f"Project: {st.session_state.project_name}")
        
        # --- World Settings (Global) ---
        st.subheader("🌍 World Settings")
        fm = st.session_state.file_manager
        
        # Check config
        config_path = "project_config.json"
        project_config = {}
        if fm and fm.exists(config_path):
            project_config = fm.load_json(config_path)
        
        saved_origin = project_config.get("origin", {"x": 0, "y": 64, "z": 0})
        
        st.caption("建設予定地の原点(南西)")
        origin_x = st.number_input("Origin X", value=saved_origin['x'])
        origin_y = st.number_input("Origin Y", value=saved_origin['y'])
        origin_z = st.number_input("Origin Z", value=saved_origin['z'])
        
        # Save automatically or via implicit state update? 
        # Better to have a save button or just use session state persistence if strictly needed.
        # For simplicity, we save when button clicked.
        if st.button("Save Origin"):
             if fm:
                 project_config["origin"] = {"x": origin_x, "y": origin_y, "z": origin_z}
                 fm.save_json(config_path, project_config)
                 st.success("Saved!")
        
        st.divider()
        
        if st.button("プロジェクトを閉じる"):
            st.session_state.clear()
            st.rerun()

# --- Phase 0: Project Setup ---
if st.session_state.phase == 0:
    st.title("Welcome to Bananacraft")
    st.markdown("新しい都市開発プロジェクトを開始します。")
    
    with st.form("project_init"):
        p_name = st.text_input("プロジェクト名 (半角英数推奨)", placeholder="Neo_Tokyo_2077")
        submitted = st.form_submit_button("プロジェクト作成")
        
        if submitted and p_name:
            # Init Managers
            try:
                key = os.getenv("GEMINI_API_KEY")
                if not key:
                    st.error("API Keyを入力してください。")
                    st.stop()
                    
                st.session_state.project_name = p_name
                st.session_state.project_name = p_name
                st.session_state.file_manager = FileManager(p_name)
                st.session_state.gemini_client = GeminiClient(key)
                st.session_state.chat_session = st.session_state.gemini_client.start_chat()
                
                # Initializing v2 Architect
                try:
                    st.session_state.architect = Architect(key)
                except Exception as e:
                    st.error(f"Failed to initialize Architect: {e}")

                
                # Persistence Check
                fm = st.session_state.file_manager
                if fm.exists("concept_art.jpg") and fm.exists("concept_prompt_refined.txt") and fm.exists("concept_reasoning.txt"):
                    st.toast("Existing project data found. Loading...", icon="📂")
                    st.session_state.concept = {
                        "title": "Concept Art",
                        "description": fm.load_text("concept_reasoning.txt"),
                        "refined_prompt": fm.load_text("concept_prompt_refined.txt"),
                        "image_path": os.path.join(fm.project_dir, "concept_art.jpg")
                    }
                
                if fm.exists("zoning_data.json"):
                    st.session_state.zoning = fm.load_json("zoning_data.json")

                st.session_state.phase = 1
                st.rerun()
            except Exception as e:
                st.error(f"初期化エラー: {e}")

# --- Phase 1: Concept & Zoning ---
elif st.session_state.phase == 1:
    st.title("Planning Phase: コンセプト & 区画整理")
    fm = st.session_state.file_manager
    client = st.session_state.gemini_client
    
    # 1. Concept Definition
    if not st.session_state.concept:
        prompt = st.text_area("街のコンセプトを入力", height=150, placeholder="例：魔法使いが住むかっこいいお城")
        if st.button("コンセプト生成"):
            if prompt:
                with st.spinner("Gemini Brain is refining the concept..."):
                    # 1. Refine Prompt (Text Interaction)
                    # Returns dict: {"reasoning": "...", "image_prompt": "..."}
                    try:
                        refined_data = client.refine_prompt(prompt)
                        reasoning = refined_data.get("reasoning", "No reasoning provided.")
                        img_prompt = refined_data.get("image_prompt", prompt)
                    except Exception as e:
                        st.error(f"Refinement Error: {e}")
                        st.stop()
                    
                    st.write(f"Thinking Process: {reasoning}")

                with st.spinner("Nano Banana Pro is painting..."):
                    # 2. Image Generation with refined prompt
                    img_bytes = client.generate_image(img_prompt)
                    
                    if img_bytes:
                        # Save Artifacts
                        fm.save_text("concept_input.txt", prompt)
                        fm.save_text("concept_reasoning.txt", reasoning)
                        fm.save_text("concept_prompt_refined.txt", img_prompt)
                        img_path = fm.save_image("concept_art.jpg", img_bytes)
                        
                        st.session_state.concept = {
                            "title": "Concept Art", 
                            "description": reasoning,
                            "refined_prompt": img_prompt,
                            "image_path": img_path
                        }
                        st.rerun()
                    else:
                        st.error("画像生成に失敗しました。")

    else:
        # Display & Feedback
        c1, c2 = st.columns([2, 1])
        with c1:
            st.image(st.session_state.concept['image_path'], caption="Generated Concept")
            with st.expander("Geminiの思考プロセス (Detail)", expanded=True):
                st.write(st.session_state.concept['description'])
            with st.expander("生成プロンプト (Internal)", expanded=False):
                st.code(st.session_state.concept['refined_prompt'])
        
        with c2:
            st.subheader("Feedback Loop")
            feedback = st.text_area("修正指示", placeholder="例：もっと不気味にして。夜にして。")
            if st.button("修正案を再生成"):
                with st.spinner("Refining based on feedback..."):
                    # Context is maintained in chat_session
                    try:
                        refined_data = client.refine_prompt(f"修正指示: {feedback}")
                        reasoning = refined_data.get("reasoning", "")
                        img_prompt = refined_data.get("image_prompt", "")
                    except Exception as e:
                        st.error(f"Refinement Error: {e}")
                        st.stop()

                    with st.spinner("Repainting..."):
                        new_img_bytes = client.generate_image(img_prompt)
                        
                        if new_img_bytes:
                            timestamp = fm._get_timestamp()
                            fm.save_text(f"concept_feedback_{timestamp}.txt", feedback)
                            fm.save_text(f"concept_reasoning_{timestamp}.txt", reasoning)
                            fm.save_text(f"concept_prompt_{timestamp}.txt", img_prompt)
                            new_img_path = fm.save_image(f"concept_art_{timestamp}.jpg", new_img_bytes)
                            
                            st.session_state.concept['description'] = reasoning
                            st.session_state.concept['refined_prompt'] = img_prompt
                            st.session_state.concept['image_path'] = new_img_path
                            st.rerun()

            st.divider()
            if not st.session_state.zoning:
                if st.button("✅ コンセプト承認 -> 区画整理へ"):
                    with st.spinner("Generating Zoning Data..."):
                        try:
                            zoning_data = client.generate_zoning_json("")
                            # The client now returns parsed object or list
                            # Apply Fixes (Collision Resolution & Orientation)
                            from v2.zoning_fixer import fix_zoning
                            zoning_data = fix_zoning(zoning_data)
                            st.session_state.zoning = zoning_data
                            fm.save_json("zoning_data.json", zoning_data)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Zoning Generation Error: {e}")

    # 2. Zoning Visualization
    if st.session_state.zoning:
        st.divider()
        st.subheader(f"Zoning Map: {st.session_state.zoning.get('theme', 'Urban Plan')}")
        
        zoning_data = st.session_state.zoning
        buildings = zoning_data.get("buildings", [])

        if not buildings:
            st.warning("No building data found in zoning JSON.")
        else:
            # Matplotlib Visualization
            import matplotlib.pyplot as plt
            import matplotlib.patches as patches
            import matplotlib.colors as mcolors

            # Create figure
            fig, ax = plt.subplots(figsize=(8, 8))
            ax.set_xlim(0, 200)
            ax.set_ylim(200, 0) # 0 at Top-Left (Map style)
            ax.set_aspect('equal')
            ax.set_xlabel("X Block")
            ax.set_ylabel("Z Block")
            ax.grid(True, linestyle='--', alpha=0.3)
            ax.set_title("City Layout Plan (200x200)")

            # Draw Frame
            frame = patches.Rectangle((0, 0), 200, 200, linewidth=2, edgecolor='black', facecolor='#f0f2f6')
            ax.add_patch(frame)

            # 1. Visualize Infrastructure (Roads/Zones)
            infra_file = "infrastructure.json"
            if fm.exists(infra_file):
                infra_data = fm.load_json(infra_file)
                for item in infra_data:
                    tool = item.get("tool_name", "")
                    params = item.get("parameters", {})
                    
                    if tool == "draw_road":
                        start = params.get("start", [0, 0])
                        end = params.get("end", [0, 0])
                        width = params.get("width", 3)
                        # Draw Line
                        ax.plot([start[0], end[0]], [start[1], end[1]], color='gray', linewidth=width, alpha=0.6, solid_capstyle='round')
                        
                    elif tool == "fill_zone":
                        zx = params.get("x", 0)
                        zz = params.get("z", 0)
                        zw = params.get("width", 1)
                        zd = params.get("depth", 1)
                        mat = params.get("material", "grass")
                        c = "green" if "grass" in mat else "lightgray"
                        rect = patches.Rectangle((zx, zz), zw, zd, linewidth=0, facecolor=c, alpha=0.3)
                        ax.add_patch(rect)

            colors = list(mcolors.TABLEAU_COLORS.values())

            # 2. Visualize Buildings
            for i, b in enumerate(buildings):
                pos = b.get("position", {})
                x = pos.get("x", 0)
                z = pos.get("z", 0)
                w = pos.get("width", 10)
                d = pos.get("depth", 10)
                
                b_name = b.get("name", "Unknown")
                b_type = b.get("type", "normal")
                
                # Check for overlap or out of bounds (Visual only)
                color = "gold" if b_type == "landmark" else colors[i % len(colors)]
                
                rect = patches.Rectangle((x, z), w, d, linewidth=1, edgecolor='black', facecolor=color, alpha=0.7)
                ax.add_patch(rect)
                
                # Add text label
                ax.text(x + w/2, z + d/2, str(i+1), fontsize=10, ha='center', va='center', color='white', fontweight='bold')

            st.pyplot(fig)
            
            # --- Infrastructure Controls ---
            st.divider()
            st.subheader("Phase 1.5: Infrastructure")
            ic1, ic2 = st.columns(2)
            
            with ic1:
                if st.button("🛣️ Generate City Infrastructure"):
                    with st.spinner("City Planner is designing roads & parks..."):
                        try:
                            planner = CityPlanner() # Uses env API Key
                            concept_text = st.session_state.concept.get('description', '')
                            infra_plan = planner.generate_infrastructure(zoning_data, concept_text)
                            
                            # Convert to dicts for JSON
                            infra_json = [i.to_dict() for i in infra_plan]
                            fm.save_json("infrastructure.json", infra_json)
                            st.success(f"Infrastructure Plan Generatored ({len(infra_json)} steps)!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Planning Error: {e}")

            with ic2:
                if fm.exists("infrastructure.json"):
                    if st.button("🚜 Construct Infrastructure (RCON)"):
                        with st.spinner("Terraforming..."):
                            try:
                                # Load plan
                                plan = fm.load_json("infrastructure.json")
                                # Convert tool names back if needed, but build_from_json handles 'tool_name'
                                rcon_ip = os.getenv("RCON_HOST", "localhost")
                                rcon_port = int(os.getenv("RCON_PORT", 25575))
                                rcon_pass = os.getenv("RCON_PASSWORD", "")
                                
                                # Use Carpenter directly via Session or Function
                                # Need RconClient
                                # The current 'build_from_json' in carpenter sends commands? 
                                # No, 'Carpenter.build' returns Block dicts. 
                                # We need RconClient to send them.
                                
                                # Initialize Session
                                session = CarpenterSession(origin=(0, 64, 0)) # Default Origin
                                blocks_to_place = session.build_from_json(plan)
                                
                                # Send via RCON
                                rcon = RconClient()
                                logs = rcon.build_voxels(blocks_to_place, origin=(0, 0, 0))
                                st.success(f"Infrastructure Built! ({len(blocks_to_place)} blocks)")
                                
                            except Exception as e:
                                st.error(f"Construction Error: {e}")
            
            st.divider()
            
            # Legacy Altair removed for clarity as requested

        # Selection Interface
        st.write("### Building List")
        
        # Display as cards or list
        cols = st.columns(3)
        for i, b in enumerate(buildings):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"**{i+1}. {b['name']}**")
                    st.caption(f"{b['type']} | ({b['position']['x']}, {b['position']['z']})")
                    if st.button(f"Design This", key=f"btn_{i}"):
                        st.session_state.selected_zone = b
                        st.session_state.phase = 2
                        st.session_state.design_images = None
                        st.rerun()

# --- Phase 2: Design ---
elif st.session_state.phase == 2:
    st.title("Phase 2: Building Design")
    zone = st.session_state.selected_zone
    st.markdown(f"**Target Zone**: {zone['name']} ({zone['type']})")
    
    client = st.session_state.gemini_client
    fm = st.session_state.file_manager
    
    # Attempt to restore design images from disk if not in session
    if not st.session_state.design_images:
        dec_filename = f"design_{zone['id']}_decorated.jpg"
        str_filename = f"design_{zone['id']}_structure.jpg"
        
        # Check if files exist
        if fm.exists(dec_filename):
            # We need absolute paths for st.image
            dec_path = os.path.join(fm.project_dir, dec_filename)
            str_path = None
            
            if fm.exists(str_filename):
                str_path = os.path.join(fm.project_dir, str_filename)
                
            st.session_state.design_images = {
                "decorated": dec_path,
                "structure": str_path
            }
            # Rerun to update UI with loaded images
            st.rerun()
    
    col_in, col_view = st.columns([1, 2])
    
    with col_in:
        design_prompt = st.text_area("デザインプロンプト", value=f"{zone.get('description')} architecture, detailed")
        if st.button("Generate Designs"):
            with st.spinner("Generating Dual Images (Concept & Structure)..."):
                try:
                    if st.session_state.concept and 'image_path' in st.session_state.concept:
                        # Re-read the file bytes
                        try:
                            with open(st.session_state.concept['image_path'], "rb") as f:
                                concept_image_bytes = f.read()
                        except Exception as e:
                            print(f"Warning: Could not read concept art for reference: {e}")

                    # 1. Generate Concept (Decorated) First
                    width = zone.get('position', {}).get('width', 10)
                    depth = zone.get('position', {}).get('depth', 10)
                    
                    dec_bytes = client.generate_concept_image(design_prompt, width, depth, concept_image_bytes)
                    
                    if dec_bytes:
                        p_path = fm.save_image(f"design_{zone['id']}_decorated.jpg", dec_bytes)
                        # Store in session state immediately to show progress
                        st.session_state.design_images = {
                            "decorated": p_path,
                            "structure": None 
                        }
                        # Force a rerun to render the decorated image before starting the heavy structure gen
                        # BUT, rerun stops execution. We need a way to continue.
                        # Simplest way in Streamlit is to use st.image directly here for immediate feedback, 
                        # or use a placeholder.
                        
                        placeholder = st.empty()
                        with placeholder.container():
                            st.success("Concept Image Generated!")
                            st.image(p_path, caption="Concept Art (Decorated)")
                        
                        # 2. Generate Structure
                        with st.spinner("Generating Structure Image (Removing Decorations)..."):
                            str_bytes = client.generate_structure_image(dec_bytes)
                            
                            if str_bytes:
                                s_path = fm.save_image(f"design_{zone['id']}_structure.jpg", str_bytes)
                                st.session_state.design_images["structure"] = s_path
                                st.rerun()
                            else:
                                st.error("Structure generation failed.")
                    else:
                        st.error("Concept generation failed.")
                except Exception as e:
                    st.error(f"Generation Error: {e}")
        
        if st.session_state.design_images:
            feedback = st.text_area("修正指示 (Design)")
            if st.button("デザイン修正"):
                with st.spinner("Regenerating..."):
                    # Simplified regen for prototype
                    new_dec = client.generate_image(f"{design_prompt}, {feedback}, detailed")
                    if new_dec:
                        ts = fm._get_timestamp()
                        p_path = fm.save_image(f"design_{zone['id']}_dec_{ts}.jpg", new_dec)
                        st.session_state.design_images['decorated'] = p_path
                        st.rerun()

            st.markdown("---")
            # Legacy Mock button removed

    with col_view:
        if st.session_state.design_images:
            t1, t2 = st.tabs(["✨ Concept", "🏗️ Structure"])
            
            with t1: 
                if st.session_state.design_images.get('decorated'):
                    st.image(st.session_state.design_images['decorated'])
            
            with t2: 
                if st.session_state.design_images.get('structure'):
                    st.image(st.session_state.design_images['structure'])
                else:
                    st.info("Generating Structure...")

            if st.session_state.design_images and st.session_state.design_images.get('structure'):
                st.markdown("---")
                st.subheader("Architectural Planning (Gemini 3)")
                
                # Check for existing instruction
                inst_file = f"building_{zone['id']}_instructions.json"
                if fm.exists(inst_file):
                    try:
                        instructions = fm.load_json(inst_file)
                        st.success("Architectural Blueprint Found!")
                        st.json(instructions, expanded=False)
                    except Exception as e:
                        st.warning(f"Corrupted blueprint found, resetting: {e}")
                        instructions = None
                    
                    if st.button("Regenerate Blueprint"):
                         instructions = None # Force regen logic below

                else:
                    instructions = None

                if not instructions:
                    if st.button("Create Blueprint (Analyze Structure)"):
                         arc = st.session_state.architect
                         if not arc:
                             st.error("Architect not initialized.")
                         else:
                             with st.spinner("Gemini 3 is analyzing the structure..."):
                                 # Prepare building info
                                 b_info = {
                                     "name": zone['name'],
                                     "width": zone['position']['width'],
                                     "depth": zone['position']['depth'],
                                     "description": zone.get('description', '')
                                 }
                                 # Local path
                                 s_path = st.session_state.design_images['structure']
                                 
                                 try:
                                     # Stage 1: Analyze
                                     analysis = arc.analyze_structure(s_path, b_info)
                                     
                                     # Stage 2: Plan (Generate Instructions)
                                     instructions_list = arc.generate_from_structure(analysis, b_info)
                                     
                                     # Convert to serializable format
                                     instructions = [i.to_dict() for i in instructions_list]
                                     
                                     # Debug: Show analysis
                                     with st.expander("Debug: Gemini Analysis"):
                                         st.json(analysis)
                                         st.write("Generated Instructions count:", len(instructions))
                                     
                                     # Save
                                     fm.save_json(inst_file, instructions)
                                     st.success("Blueprint Created!")
                                     st.rerun()
                                 except Exception as e:
                                     st.error(f"Planning Error: {e}")

                if instructions:
                    st.markdown("---")
                    st.subheader("Construction Planning (Carpenter)")
                    
                    # Check for existing blocks
                    blocks_file = f"building_{zone['id']}_blocks_v2.json"
                    blocks = []
                    
                    if fm.exists(blocks_file):
                         blocks = fm.load_json(blocks_file)
                         st.success(f"Construction Data Ready: {len(blocks)} blocks")
                         
                    if not blocks:
                        if st.button("Generate Construction Data"):
                            try:
                                with st.spinner("Carpenter is calculating block placements..."):
                                    # Init Carpenter
                                    carpenter = CarpenterSession()
                                    
                                    # Build
                                    blocks = carpenter.build_from_json(instructions)
                                    
                                    # Save
                                    fm.save_json(blocks_file, blocks)
                                    st.success(f"Construction Complete! Generated {len(blocks)} blocks.")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Construction Error: {e}")
                    
                    # Preview Section
                    if blocks:
                         st.markdown("### 3D Preview")
                         fig = create_3d_preview(blocks, title=f"{zone['name']} (Preview)")
                         st.plotly_chart(fig, use_container_width=True)
                         
                         if st.button("Proceed to Site (Phase 3)"):
                             st.session_state.phase = 3
                             st.rerun()

# --- Phase 3: Construction ---
# --- Phase 3: Construction & Integration ---
elif st.session_state.phase == 3:
    st.header("Phase 3: Construction & Integration")
    fm = st.session_state.file_manager
    zone = st.session_state.selected_zone
    
    # 1. World Settings
    project_config = {}
    if fm.exists("project_config.json"):
        project_config = fm.load_json("project_config.json")
    saved_origin = project_config.get("origin", {'x':0, 'y':64, 'z':0})
    current_origin = (saved_origin['x'], saved_origin['y'], saved_origin['z'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. Terraforming (整地)")
        st.caption(f"Target Area: {current_origin} to ({current_origin[0]+200}, {current_origin[1]}, {current_origin[2]+200})")
        
        if st.button("🚜 Run Terraformer"):
            try:
                with st.spinner("Clearing area & Fixing chunks..."):
                    rcon = RconClient()
                    terra = Terraformer(rcon)
                    logs = terra.terraform(current_origin, width=200, depth=200, base_y=current_origin[1])
                    st.success("Terraforming Complete!")
                    with st.expander("Logs"):
                        st.write(logs)
            except Exception as e:
                st.error(f"Terraforming Failed: {e}")

        st.divider()

        st.subheader("2. Structure Build")
        st.info("Deploy the blueprint to the Minecraft Server.")
        
        # Load Zoning Data to get Offset
        zoning_offset = (zone['position']['x'], zone['position']['z'])
        st.caption(f"Building: {zone['name']} (Offset: {zoning_offset})")
        
        # Final Absolute Coordinate
        abs_x = current_origin[0] + zoning_offset[0]
        abs_y = 0 # Y is already calculated in blocks (default 64)
        abs_z = current_origin[2] + zoning_offset[1]
        
        build_origin = (abs_x, abs_y, abs_z)
        st.markdown(f"**Build Location**: `{build_origin}`")
        
        # Update: Look for v2 blocks file
        v2_blocks_file = f"building_{zone['id']}_blocks_v2.json"
        
        if fm.exists(v2_blocks_file):
            if st.button("🚀 Instant Build (Structure)"):
                try:
                    with st.spinner(f"Building at {build_origin}..."):
                        rcon = RconClient()
                        blocks = fm.load_json(v2_blocks_file)
                        
                        # Build at absolute location
                        # blocks_v2 already has relative coordinates (x, y, z)
                        # rcon.build_voxels adds origin to them
                        log = rcon.build_voxels(blocks, origin=build_origin)
                        
                        st.success(f"Build Command Sent! ({len(blocks)} blocks)")
                        with st.expander("Server Response Log"):
                             st.write(log)
                except Exception as e:
                    st.error(f"Build Failed: {e}")
        else:
            st.warning(f"No blueprint found ({v2_blocks_file}). Please complete Phase 2.")
            if st.button("Back to Phase 2"):
                st.session_state.phase = 2
                st.rerun()

    with col2:
        st.subheader("3. AI Decoration (Bot)")
        # A. Analyze & Plan
        if st.button("🎨 Generate Decoration Plan"):
            with st.spinner("Gemini is analyzing structure & concept..."):
                try:
                    # Uses globally imported Decorator
                    dec = Decorator() # Uses env API key
                    
                    # Context
                    concept = zone.get('description', '')
                    if fm.exists("concept_reasoning.txt"):
                        concept += "\n" + fm.load_text("concept_reasoning.txt")
                        
                    # Structure Instructions (for context)
                    inst_file = f"building_{zone['id']}_instructions.json"
                    instructions_data = []
                    if fm.exists(inst_file):
                        instructions_data = fm.load_json(inst_file) # dicts
                    
                    # Image (Target)
                    image_path = None
                    # Try finding the best image
                    possible_images = [
                        st.session_state.design_images.get('decorated'),
                        f"projects/{st.session_state.project_name}/design_1_decorated.jpg",
                         "design_1_decorated.jpg"
                    ]
                    for img in possible_images:
                        if img and os.path.exists(img):
                            image_path = img
                            break
                    
                    if not image_path:
                        st.error("No decorated design image found!")
                    else:
                        st.info(f"Using design: {os.path.basename(image_path)}")
                        
                        # Reconstruct building info
                        b_info = {
                             "name": zone['name'],
                             "width": zone['position']['width'],
                             "depth": zone['position']['depth'],
                             "description": zone.get('description', '')
                        }

                        # Check for existing decoration plan
                        deco_file = f"building_{zone['id']}_decoration.json"
                        deco_instructions_list = []
                        
                        if fm.exists(deco_file):
                            st.info(f"Loading existing decoration plan: {deco_file}")
                            raw_data = fm.load_json(deco_file)
                            deco_instructions_list = raw_data
                        else:
                             # Load actual blocks for accurate placement
                             blocks_file = f"building_{zone['id']}_blocks_v2.json"
                             structure_blocks = []
                             if fm.exists(blocks_file):
                                 raw_blocks = fm.load_json(blocks_file)
                                 # Normalize blocks to Y=0 base
                                 # The blocks in file are at Y=64 (default carpenter)
                                 # We want Decorator to see a building at Y=0
                                 if raw_blocks:
                                     min_y = min(b['y'] for b in raw_blocks)
                                     # Shift everyone down
                                     structure_blocks = [
                                         {**b, 'y': b['y'] - min_y} 
                                         for b in raw_blocks
                                     ]
                             else:
                                 st.warning(f"No block data found ({blocks_file}). Using instructions fallback.")
                                 # Fallback? But we changed the signature. 
                                 # Whatever, empty list will trigger naive placement (or fail prompt context).
                                 structure_blocks = []

                             # Generate new
                             deco_instructions_objects = dec.generate_decoration_plan(
                                 image_path=image_path,
                                 concept_text=concept,
                                 structure_blocks=structure_blocks,
                                 building_info=b_info
                             )
                             if deco_instructions_objects:
                                 deco_instructions_list = [i.to_dict() for i in deco_instructions_objects]
                                 fm.save_json(deco_file, deco_instructions_list)
                        
                        # B. Execution (Manual -> Bot)
                        if deco_instructions_list:
                            st.subheader("B. Execute Decoration")
                            st.write(f"Plan ready with {len(deco_instructions_list)} instructions.")
                            
                            # Existing file for Bot
                            # The bot reads from projects/<Project>/<File>
                            # Our file is "building_<ID>_decoration.json" in projects/<Project>/
                            
                            target_file_name = f"building_{zone['id']}_decoration.json"
                            
                            if st.button("👷 Run AI Carpenter (Auto)"):
                                try:
                                    with st.spinner("AI Carpenter is working... (This may take a minute)"):
                                        # Use CarpenterSession to run bot
                                        cs = CarpenterSession()
                                        
                                        # origin is needed? 
                                        # The bot logic in index.js says: if origin provided, use it. 
                                        # Else find player.
                                        # We prefer provided origin for stability.
                                        # Use 'build_origin' calculated in Structure Build section
                                        
                                        # build_origin = (abs_x, abs_y, abs_z)
                                        # But wait, decoration blocks might be relative to 0,0,0 if we shifted them?
                                        # In 'generate_decoration_plan', we passed structure_blocks normalized to 0.
                                        # The OUTPUT of decorator (instructions) are usually relative to the building origin?
                                        # Let's check decorator.py output. usually relative.
                                        # So we pass the same build_origin as the structure.
                                        
                                        # One catch: Decoration instructions X,Y,Z are relative to what?
                                        # If the plan was generated based on normalized Y=0 blocks, 
                                        # and the bot applies them at 'origin', then 'origin' should be the building corner.
                                        # Yes, build_origin is the correct origin.
                                        
                                        result_log = cs.run_bot(
                                            project_name=st.session_state.project_name, 
                                            target_file=target_file_name,
                                            origin=build_origin
                                        )
                                        
                                        st.success("Decoration Complete!")
                                        with st.expander("Carpenter Bot Logs"):
                                            st.code(result_log)
                                            
                                except Exception as e:
                                    st.error(f"Bot Execution Failed: {e}")
                            
                            st.caption("Legacy Manual Command:")
                            st.code(f"node AI_Carpenter_Bot/index.js {st.session_state.project_name} {build_origin[0]} {build_origin[1]} {build_origin[2]} {target_file_name}")

                        
                        if deco_instructions_list:
                             st.success(f"Decoration Plan Ready! ({len(deco_instructions_list)} steps)")
                             
                             # Convert high-level tools to raw blocks for Bot
                             try:
                                 # Use Carpenter to calculate blocks
                                 # NOTE: Use (0,0,0) origin here so blocks are relative to the building's 0-point,
                                 # not shifted by default Y=64. The Bot script adds the actual world origin Y.
                                 carpenter = CarpenterSession(origin=(0, 0, 0))
                                 # Note: decorator instructions might need to be wrapped or passed directly
                                 # build_from_json expects list of dicts with 'tool_name' etc.
                                 deco_blocks = carpenter.build_from_json(deco_instructions_list)
                                 
                                 # Convert blocks to Bot format
                                 # Bot expects: {x, y, z, action='setblock', block='material'}
                                 bot_instructions = []
                                 for b in deco_blocks:
                                     block_type = b['type']
                                     # Force persistent leaves to prevent decay regardless of logs
                                     if "leaves" in block_type and "[" not in block_type:
                                         block_type += "[persistent=true]"
                                         
                                     bot_instructions.append({
                                         "x": b['x'],
                                         "y": b['y'],
                                         "z": b['z'],
                                         "action": "setblock",
                                         "block": block_type
                                     })
                                     
                                 # Save for Bot
                                 fm.save_json("decoration.json", {"instructions": bot_instructions})
                                 st.success(f"Bot Instructions Generated! ({len(bot_instructions)} blocks)")
                                 
                             except Exception as e:
                                 st.error(f"Carpenter Processing Failed: {e}")

                             with st.expander("View Decoration Plan"):
                                 st.json(deco_instructions_list)
                        else:
                            st.warning("No decorations generated.")
                            
                except Exception as e:
                    st.error(f"Decoration Planning Failed: {e}")
        
        # Show Plan if exists
        if fm.exists("decoration.json"):
            plan = fm.load_json("decoration.json")
            # plan['instructions'] is the list
            count = len(plan.get('instructions', []))
            st.caption(f"Ready to deploy {count} blocks via Bot.")
            
            # B. Deploy Bot (Mock / Future)
            if st.button("Merge & Build (Structure + Decoration)"):
                 st.info("Merging decoration into final build...")
                 try:
                     # 1. Structure Blocks
                     carpenter = CarpenterSession(origin=(0, 0, 0))
                     # Re-load structure instructions
                     inst_file = f"building_{zone['id']}_instructions.json"
                     structure_blocks = []
                     if fm.exists(inst_file):
                         inst_data = fm.load_json(inst_file)
                         structure_blocks = carpenter.build_from_json(inst_data)
                     
                     # 2. Decoration Blocks
                     # plan['instructions'] is already in Bot format ({x,y,z,block,action})
                     # We need to parse them back or just append. 
                     # Structure blocks from carpenter are dicts {x,y,z,type,properties...}
                     # We need to convert structure blocks to Bot format first.
                     
                     final_instructions = []
                     
                     # Add Structure
                     for b in structure_blocks:
                         final_instructions.append({
                             "x": b['x'],
                             "y": b['y'],
                             "z": b['z'],
                             "action": "setblock",
                             "block": b['type']
                         })
                         
                     # Add Decoration (already in bot format in plan['instructions'])
                     # But we should ensure no duplicates? 
                     # For now, just append. Decoration comes last, so it overwrites (replace) structure if overlap.
                     deco_bot_instr = plan.get('instructions', [])
                     final_instructions.extend(deco_bot_instr)
                     
                     # Save
                     final_file = "full_build.json"
                     fm.save_json(final_file, {"instructions": final_instructions})
                     
                     st.success(f"Merged Build Ready! Total blocks: {len(final_instructions)}")
                     
                     # 3. Instant Build (RCON Optimized)
                     if st.checkbox("Execute Instant Build (RCON)", value=True):
                         with st.spinner(f"Building {len(final_instructions)} blocks via RCON..."):
                             # Convert to format expected by build_voxels ({x,y,z,type})
                             # Our final_instructions are {x,y,z,block,action}
                             rcon_blocks = []
                             for inst in final_instructions:
                                 rcon_blocks.append({
                                     'x': inst['x'],
                                     'y': inst['y'],
                                     'z': inst['z'],
                                     'type': inst['block'] # build_voxels expects 'type'
                                 })
                             
                             # Calculate Absolute Origin
                             abs_origin = (
                                 current_origin[0] + zone['position']['x'],
                                 current_origin[1],
                                 current_origin[2] + zone['position']['z']
                             )
                             
                             rcon = RconClient()
                             logs = rcon.build_voxels(rcon_blocks, origin=abs_origin)
                             st.success(f"Build Complete! Sent {len(logs)} commands.")

                     # Fallback Command
                     project_id = st.session_state.project_name
                     abs_x = current_origin[0] + zone['position']['x']
                     abs_y = current_origin[1]
                     abs_z = current_origin[2] + zone['position']['z']
                     
                     cmd = f"node AI_Carpenter_Bot/index.js {project_id} {abs_x} {abs_y} {abs_z} full_build.json"
                     with st.expander("Show Bot Command (Fallback)"):
                         st.code(cmd, language="bash")
                         st.info("Use this if RCON fails or for animation.")
                     
                 except Exception as e:
                     st.error(f"Merge & Build Failed: {e}")
            
            if st.button("🤖 Summon Carpenter Bot (Decoration Only)"):
                st.info("Summoning Bot...")
                project_id = st.session_state.project_name
                
                # Pass origin
                abs_x = current_origin[0] + zone['position']['x']
                abs_y = current_origin[1]
                abs_z = current_origin[2] + zone['position']['z']
                
                cmd = f"node AI_Carpenter_Bot/index.js {project_id} {abs_x} {abs_y} {abs_z}"
                st.code(cmd, language="bash")
                st.warning("Run this to build DECORATION ONLY.")

    st.divider()
    if st.button("Restart Project"):
        st.session_state.clear()
        st.rerun()
