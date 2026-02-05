import time
import random

class MockAI:
    @staticmethod
    def generate_concept(prompt: str):
        """Phase 1: Concept Generation Mock"""
        time.sleep(2)  # Simulate API latency
        
        concepts = [
            {
                "title": "ネオン輝くサイバー・スラム",
                "description": f"「{prompt}」に基づき、高密度で垂直に広がる都市構造を設計しました。路地は狭く、ホログラム広告の明かりが絶え間なく照らしています。金属の屋根を叩く雨音が響く、ハイテクと退廃が融合した場所です。",
                "image_url": "https://images.unsplash.com/photo-1555680202-c86f0e12f086?q=80&w=1000&auto=format&fit=crop"
            },
            {
                "title": "ソーラーパンク・オアシス",
                "description": f"「{prompt}」から着想を得て、白い大理石の構造物と豊かな緑が絡み合う美しい都市を描きました。重力クリスタルによって浮遊する島々が居住区となっています。自然とテクノロジーが調和した理想郷です。",
                "image_url": "https://images.unsplash.com/photo-1518544806314-a9b702ec8c9f?q=80&w=1000&auto=format&fit=crop"
            }
        ]
        return random.choice(concepts)

    @staticmethod
    def generate_zoning_data():
        """Phase 1: Zoning Data Mock"""
        time.sleep(1.5)
        # Mocking a grid of 3x3 zones or similar
        return [
            {"id": "z1", "name": "中央広場", "type": "Public", "x": 0, "y": 0, "color": "#FFD700", "desc": "都市の中心部。人々が集う場所。"},
            {"id": "z2", "name": "商業地区", "type": "Commercial", "x": 1, "y": 0, "color": "#FF5733", "desc": "活気ある商店や屋台が並ぶエリア。"},
            {"id": "z3", "name": "居住タワーA", "type": "Residential", "x": 0, "y": 1, "color": "#33FF57", "desc": "高密度の集合住宅タワー。"},
            {"id": "z4", "name": "テックハブ", "type": "Industrial", "x": 1, "y": 1, "color": "#3357FF", "desc": "サーバーファームと製造工場。"},
        ]

    @staticmethod
    def generate_building_design_images(prompt: str, feedback: str = None):
        """Phase 2: Dual Image Generation Mock"""
        time.sleep(2.5)
        # Return two images: one highly decorated, one simple structure for Meshy
        
        base_desc = f"Based on '{prompt}'"
        if feedback:
            base_desc += f" with adjustments: {feedback}"
            
        return {
            "decorated": {
                "url": "https://images.unsplash.com/photo-1565008576549-57569a49371d?q=80&w=1000&auto=format&fit=crop", # Vibrant neon building
                "desc": "装飾済みイメージ: ネオンや看板、植栽で彩られた完成予想図"
            },
            "structure": {
                "url": "https://images.unsplash.com/photo-1486744360530-ca9856ccb63e?q=80&w=1000&auto=format&fit=crop", # Simple concrete/structure
                "desc": "施工用イメージ(Meshy用): 装飾を排除し、構造を明確にした3D生成用データ"
            }
        }

class MockMeshy:
    @staticmethod
    def generate_3d_model(prompt: str):
        """Phase 2: 3D Model Generation Mock"""
        time.sleep(3)
        # Using a standard GLB sample (Duck is robust, but maybe we can find something more 'building'-like if available publicly)
        # For now, let's use the reliable Duck or similar GlTF sample.
        # Ideally, we would use a house model.
        return "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Models/master/2.0/SciFiHelmet/glTF-Binary/SciFiHelmet.glb"

class MockServer:
    @staticmethod
    def build_structure(zone_id: str):
        """Phase 3: Construction Mock"""
        # Simulate voxel placement steps
        steps = [
            "地形を分析中...",
            "植生を除去中...",
            "基礎工事を開始 (Stone)...",
            "構造柱を設置中 (Iron Block)...",
            "壁面を構築中 (Concrete)...",
            "屋根を施工中 (Dark Prismarine)...",
            "最終仕上げ中..."
        ]
        for step in steps:
            time.sleep(0.5)
            yield step
        return True

    @staticmethod
    def decorate_structure(zone_id: str, feedback: str = None):
        """Phase 4: Decoration Mock"""
        time.sleep(2)
        if feedback:
            return f"ご要望「{feedback}」に基づいて修正しました。照明を追加し、植栽配置を調整しました。"
        return "内装にモダンな家具を配置しました。照明計画を改善しました。"
