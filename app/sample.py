import streamlit as st
import time
import json
import os

# ページ設定
st.set_page_config(layout="wide", page_title="Bananacraft Architect", page_icon="🍌")

# --- Dummy Data & Mock API Functions ---
# 本来はここでGeminiやMeshyのAPIを叩きますが、今はダミーデータを返します

def mock_generate_concept(prompt):
    """Phase 1: コンセプト生成のダミー"""
    time.sleep(2) # 生成しているフリ
    return {
        "text": f"「{prompt}」に基づき、ネオンが反射するウェットな質感のサイバーパンク・ストリートを設計しました。",
        "image": "https://images.unsplash.com/photo-1555680202-c86f0e12f086?q=80&w=1000&auto=format&fit=crop" # ダミー画像
    }

def mock_generate_zoning():
    """Phase 1: 区画整理のダミー"""
    time.sleep(1.5)
    return [
        {"id": "z1", "name": "Dragon Ramen", "type": "Commercial", "color": "#FF5733"},
        {"id": "z2", "name": "Capsule Hotel", "type": "Residential", "color": "#33FF57"},
        {"id": "z3", "name": "Cyber Park", "type": "Public", "color": "#3357FF"},
    ]

def mock_generate_3d_model(zone_name):
    """Phase 2: Meshy 3D生成のダミー"""
    time.sleep(3)
    # 本来はMeshyのGLB URLを返すが、ここではサンプルモデルを使用
    # (Duck.glbはWeb上のフリーサンプルとしてよく使われるものです)
    return "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Models/master/2.0/Duck/glTF-Binary/Duck.glb"

def mock_build_structure(zone_id):
    """Phase 3: 構造建築のダミー"""
    time.sleep(1)
    return True

def mock_ai_decorate(zone_id, feedback=None):
    """Phase 4: AI装飾のダミー"""
    time.sleep(4) # Botが頑張っている時間
    if feedback:
        return f"「{feedback}」のご要望に合わせて、提灯を赤色に変更し、数を増やしました。"
    return "外観にランタンを追加し、屋根の素材を滑らかなものに変更しました。"

# --- Session State Management ---
if 'phase' not in st.session_state:
    st.session_state.phase = 1
if 'concept_data' not in st.session_state:
    st.session_state.concept_data = None
if 'zoning_data' not in st.session_state:
    st.session_state.zoning_data = None
if 'selected_zone' not in st.session_state:
    st.session_state.selected_zone = None
if 'model_url' not in st.session_state:
    st.session_state.model_url = None
if 'build_status' not in st.session_state:
    st.session_state.build_status = {} # zone_id: status
if 'decoration_log' not in st.session_state:
    st.session_state.decoration_log = []

# --- UI Components ---

st.title("🍌 Bananacraft Architect System")

# サイドバー：進捗表示
st.sidebar.header("Development Phase")
st.sidebar.progress(st.session_state.phase * 25)
st.sidebar.write(f"Current Phase: {st.session_state.phase}/4")

# ==========================================
# Phase 1: Concept & Zoning
# ==========================================
if st.session_state.phase == 1:
    st.header("Phase 1: Concept & Zoning")
    
    user_input = st.text_input("どんな街を作りますか？", "ネオン輝くサイバーパンクな屋台街")
    
    if st.button("Generate Concept"):
        with st.spinner("Gemini is dreaming..."):
            st.session_state.concept_data = mock_generate_concept(user_input)
            
    if st.session_state.concept_data:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.image(st.session_state.concept_data["image"], caption="Concept Art", use_column_width=True)
        with col2:
            st.write(st.session_state.concept_data["text"])
            st.info("このコンセプトで区画整理を行いますか？")
            
            if st.button("Proceed to Zoning"):
                with st.spinner("Gemini is zoning the area..."):
                    st.session_state.zoning_data = mock_generate_zoning()
                    st.session_state.phase = 2
                    st.rerun()

# ==========================================
# Phase 2: Design & 3D Modeling
# ==========================================
elif st.session_state.phase == 2:
    st.header("Phase 2: 3D Modeling")
    
    # 区画図の可視化（簡易版）
    st.subheader("City Zoning Map")
    cols = st.columns(len(st.session_state.zoning_data))
    for i, zone in enumerate(st.session_state.zoning_data):
        with cols[i]:
            st.markdown(f"**{zone['name']}**")
            st.caption(zone['type'])
            if st.button(f"Select {zone['name']}", key=f"btn_{zone['id']}"):
                st.session_state.selected_zone = zone

    if st.session_state.selected_zone:
        zone = st.session_state.selected_zone
        st.divider()
        st.subheader(f"Modeling: {zone['name']}")
        
        if st.button("Generate 3D Model (Meshy API)"):
            with st.spinner("Sending construction image to Meshy..."):
                st.session_state.model_url = mock_generate_3d_model(zone['name'])
        
        if st.session_state.model_url:
            st.success("3D Model Generated!")
            # 3Dモデル表示コンポーネント (iframe等でも代用可だが、専用コンポーネント推奨)
            # ここでは簡易的に iframe で glb ビューアを使うか、st_model_3d を使う
            # ※今回はダミーとしてテキストリンクを表示しますが、
            # 本番は `st_model_3d` パッケージなどを使います。
            st.write("▼ 3D Preview (Interactive)")
            # st_model_3d があれば以下のように書けます
            # st_model_3d(st.session_state.model_url) 
            st.components.v1.iframe(f"https://modelviewer.dev/examples/1.0.0/documentation/index.html#src={st.session_state.model_url}", height=400)

            if st.button("Approve & Build Structure"):
                st.session_state.phase = 3
                st.rerun()

# ==========================================
# Phase 3: Instant Build (Voxelization)
# ==========================================
elif st.session_state.phase == 3:
    st.header("Phase 3: Structural Build")
    st.info("3Dモデルをブロックデータ(Voxel)に変換し、サーバーに一括転送します。")
    
    if st.button("🚀 EXECUTE INSTANT BUILD"):
        with st.status("Building...", expanded=True) as status:
            st.write("Voxelizing 3D Model...")
            time.sleep(1)
            st.write("Connecting to PaperMC Server...")
            time.sleep(0.5)
            st.write("Sending /setblock commands...")
            mock_build_structure("z1")
            status.update(label="Build Complete!", state="complete", expanded=False)
        
        st.success("構造体の建築が完了しました！")
        time.sleep(1)
        st.session_state.phase = 4
        st.rerun()

# ==========================================
# Phase 4: AI Decoration (The Carpenter)
# ==========================================
elif st.session_state.phase == 4:
    st.header("Phase 4: AI Decoration")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Decoration Status")
        if not st.session_state.decoration_log:
             st.warning("まだ装飾が行われていません。")
             if st.button("Call AI Carpenter"):
                 with st.spinner("AI Carpenter is working... (Placing blocks, Adding lights)"):
                     result = mock_ai_decorate("z1")
                     st.session_state.decoration_log.append(result)
                     st.rerun()
        else:
            for log in st.session_state.decoration_log:
                st.success(f"✅ {log}")
            
            st.image("https://images.unsplash.com/photo-1599939571322-792a326991f2?q=80&w=1000", caption="Current State (Mock Screenshot)", use_column_width=True)

    with col2:
        st.subheader("Feedback")
        feedback = st.text_area("修正指示があれば入力してください", placeholder="例：もっと派手にして、入り口に花を置いて")
        if st.button("Apply Changes"):
            if feedback:
                with st.spinner("Re-decorating..."):
                    result = mock_ai_decorate("z1", feedback)
                    st.session_state.decoration_log.append(result)
                    st.rerun()

    if st.button("Finish Project"):
        st.balloons()
        st.success("All Done! Bananacraft Project Completed.")