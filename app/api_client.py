import os
from google import genai
from google.genai import types
import base64
from io import BytesIO

# Default model configuration
TEXT_MODEL = "gemini-3-pro-preview" 
CHAT_MODEL = "gemini-3-pro-preview" 
IMAGE_MODEL = "gemini-3-pro-image-preview"

class GeminiClient:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.chat_session = None
        # System instruction for the "Brain"
        self.system_instruction = """
        あなたは世界最高峰のMinecraftコンセプトアーティストであり、プロンプトエンジニアです。
        ユーザーから提供される「曖昧なテーマ」は、200x200ブロックの広大な「街」や「都市」の建設予定地のためのものです。
        単体の建物ではなく、街全体の雰囲気、区画、複数の建物の配置、道路、地形が見渡せるような「鳥瞰図（Bird's-eye view）」や「広角ショット」のコンセプトアートを描くためのプロンプトを作成してください。

        【重要】生成された画像は後続の3Dモデル化処理に使用されます。以下の点を必ずプロンプトに含めてください：
        - ボクセル/キューブ状のブロックが明確に分かる表現
        - 鮮やかで識別しやすい配色（後のブロック変換で色が失われないようにするため）
        - Minecraft Bedrock Editionに実在するブロックを意識したテクスチャ

        以下のJSON形式で常に出力してください：
        {
            "reasoning": "なぜそのようなプロンプトにしたのか、どのような情景（街の規模感、広がり）を想像したのかの日本語による思考プロセス・解説",
            "image_prompt": "画像生成AI（Nano Banana Pro）に入力するための詳細な日本語プロンプト。必ず『広大な街の全景』『鳥瞰図』『200x200ブロックの規模感』『複数の建物』『道』『地形』といった要素を含め、単体の建物アップにならないようにしてください。光の表現、建築様式、ボクセル/キューブ表現、色彩設計、環境（天候、時間帯）、質感も具体的に含めてください。"
        }
        """

    def start_chat(self, history=None):
        """
        Starts a chat session with the model, maintaining context.
        """
        config = types.GenerateContentConfig(
            system_instruction=self.system_instruction,
            response_mime_type="application/json", # Enforce structured output
            thinking_config=types.ThinkingConfig(include_thoughts=True) # Explicitly enable thinking if model supports
        )
        
        self.chat_session = self.client.chats.create(
             model=CHAT_MODEL,
             config=config,
             history=history or []
        )
        return self.chat_session

    def generate_text(self, prompt: str, system_instruction: str = None, image_bytes: bytes = None) -> str:
        """
        Generates text using a one-off request, bypassing the concept-art chat session constraints.
        Supports multimodal input (text + image).
        """
        print(f"Generating text with Gemini 3 (One-off)...")
        
        config = None
        if system_instruction:
            config = types.GenerateContentConfig(system_instruction=system_instruction)
            
        contents = [prompt]
        if image_bytes:
            print("Attaching reference image to generation request...")
            # Create a Part object for the image data
            # Assuming JPEG as default for now, can be sophisticated later
            image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            contents.append(image_part)

        try:
             response = self.client.models.generate_content(
                 model=CHAT_MODEL,
                 contents=contents,
                 config=config
             )
             return response.text
        except Exception as e:
            print(f"Text generation error: {e}")
            return ""

    def refine_prompt(self, user_input: str):
        """
        Sends user input to the chat model to get a refined image prompt.
        Maintains conversation history for feedback loops.
        """
        if not self.chat_session:
            self.start_chat()
            
        print(f"Sending to Gemini 3: {user_input}")
        response = self.chat_session.send_message(user_input)
        
        # Debug: Print raw text
        print(f"Gemini 3 Raw Response: {response.text}")

        # Verify JSON
        try:
            if response.parsed:
                return response.parsed
        except Exception:
            pass
            
        # Fallback manual parsing if SDK behavior varies or parsed is None
        try:
            import json
            # Cleaning potential markdown code blocks
            text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except Exception as e:
            print(f"JSON Parsing Error: {e}")
            return {"reasoning": "Error parsing response", "image_prompt": user_input}

    def generate_image(self, prompt: str, reference_image_bytes: bytes = None):
        """
        Generates an image using Nano Banana Pro (gemini-3-pro-image-preview).
        If reference_image_bytes is provided, performs Image-to-Image (Editing/Variation).
        """
        try:
            print(f"Generating image with prompt: {prompt[:50]}...")
            
            contents = [prompt]
            if reference_image_bytes:
                print("Attaching reference image for consistency...")
                # Assuming JPEG, but could be inferred if we tracked it.
                # Creates a blob part for the image
                image_part = types.Part.from_bytes(data=reference_image_bytes, mime_type="image/jpeg")
                contents.append(image_part)

            # Using generate_content as verified by test script
            response = self.client.models.generate_content(
                model=IMAGE_MODEL,
                contents=contents
            )
            
            # Extract image bytes from response parts
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                     # Check if part has inline_data (Blob)
                    if hasattr(part, 'inline_data') and part.inline_data:
                        return part.inline_data.data
                        
            return None
        except Exception as e:
            print(f"Image generation error: {e}")
            return None

    def generate_concept_image(self, base_description: str, width: int, depth: int, concept_image_bytes: bytes = None):
        """
        Generates the Concept (Decorated) image.
        Optimized for subsequent 3D modeling and voxelization.
        """
        prompt = (
            f"マインクラフト（Minecraft）のボクセル建築物の画像を生成してください。\n"
            f"\n"
            f"【建築物の説明】\n"
            f"{base_description}\n"
            f"\n"
            f"【建築サイズ】幅 {width} ブロック × 奥行 {depth} ブロック\n"
            f"\n"
            f"【視点・構図】※3Dモデル化のため非常に重要\n"
            f"- 斜め上45度からのアイソメトリック視点（Isometric view）\n"
            f"- 建物全体が画面内に収まること（上下左右に適度な余白）\n"
            f"- 建物は画面の中央に配置\n"
            f"\n"
            f"【背景】\n"
            f"- シンプルな空のグラデーション背景のみ（他の建物や地形は配置しない）\n"
            f"- 建物の輪郭が背景から明確に分離できること\n"
            f"\n"
            f"【スタイル・テクスチャ】\n"
            f"- Minecraft Bedrock Edition (Vanilla) に実在するブロックのテクスチャを使用\n"
            f"- 1ブロック = 1立方体が明確に分かるボクセルスタイル\n"
            f"- 鮮やかで識別しやすい配色（パステルや淡い色は避ける）\n"
            f"\n"
            f"【ライティング】\n"
            f"- 柔らかい自然光（影MOD風でもOK）\n"
            f"- ブロックの色が正確に分かる明るさ\n"
            f"\n"
            f"【装飾】\n"
            f"- 理想的な完成形として装飾を含めてOK\n"
            f"- ランタン、旗、植物、フェンスなどで雰囲気を演出\n"
            f"\n"
            f"【参照画像について】\n"
            f"添付のコンセプトアート（街の全景）の世界観・配色・雰囲気を継承してください。"
        )
        
        print(f"--- Generating Decorated Image (Concept) ---\nPrompt: {prompt[:200]}...")
        return self.generate_image(prompt, reference_image_bytes=concept_image_bytes)

    def generate_structure_image(self, decorated_image_bytes: bytes):
        """
        Generates the Structure (Meshy-ready) image based on the Decorated image.
        Optimized for 3D model generation with color preservation.
        """
        if not decorated_image_bytes:
            return None

        prompt = (
            "この建築画像を「3Dモデル生成用の躯体画像」に変換してください。\n"
            "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "【最重要ルール】絶対に守ってください\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "\n"
            "1. **色を絶対に変えない**\n"
            "   - 壁が青なら青のまま、屋根が赤なら赤のまま\n"
            "   - グレースケールや単一色への変換は禁止\n"
            "   - 元画像のカラーパレットを完全に維持\n"
            "\n"
            "2. **形状を維持する**\n"
            "   - 建物のシルエット、プロポーション、大きさを変えない\n"
            "   - 視点・アングルも元画像と同一に\n"
            "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "【削除するもの】細かい装飾のみ\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "- ランタン、松明、看板、旗\n"
            "- 植木鉢、花、ツタ、苔\n"
            "- フェンス、鉄格子、板ガラス\n"
            "- ボタン、レバー、トラップドア\n"
            "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "【残すもの】主要構造\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "- 壁、屋根、床、柱、階段\n"
            "- 窓（ガラス部分はシンプルに）\n"
            "- ドア（閉じた状態で）\n"
            "- 各パーツの元の色とテクスチャ\n"
            "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "【出力スタイル】\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "- 背景：純白 (#FFFFFF) の単色\n"
            "- ライティング：フラット（影なし、均一な明るさ）\n"
            "- 各ブロック面の色が明確に識別できること\n"
        )
        
        print(f"--- Generating Structure Image ---\nPrompt: {prompt[:200]}...")
        return self.generate_image(prompt, reference_image_bytes=decorated_image_bytes)

    def generate_zoning_json(self, concept_text: str):
        """
        Ask the chat model to generate Zoning JSON based on the concept.
        This reuses the chat context so it 'knows' the concept.
        """
        prompt = f"""
        あなたは熟練した都市計画家であり、マインクラフトの建築家です。
        現在設計中の都市コンセプト（ムードボード）の世界観に基づき、200x200ブロックのエリアに建設する「街の設計図」を作成してください。

        【制約条件】
        エリア定義: ワールド座標 (x: 0, z: 0) を始点とし、(x: 200, z: 200) を終点とする正方形の範囲内です。
        創造的補完: 文脈から「この世界観なら当然あるべき施設（例：画像にお城があれば、城下町や兵舎など）」を想像して追加してください。
        配置ルール:
        - 【超重要】1つの区画（アイテム）には、必ず「単一の建築物」のみを配置すること。「高層ビル群」「住宅街」のように複数の建物を1つの区画にまとめることは禁止です。
        - 建物数と規模の目安:
          - ランドマーク（超大型・シンボル）: 1〜2個
          - 大型建築（主要施設）: 4〜7個
          - 小型建築（民家・商店など）: 10〜20個
        - 各建物が重ならないように、200x200のグリッド内に座標を分散配置すること。
        - 道路や広場のための余白を確保すること。

        【出力形式】 以下のJSON形式のみを出力してください。
        {{
          "theme": "コンセプトテーマ",
          "area": {{"start": [0, 0], "end": [200, 200]}},
          "buildings": [
            {{
              "id": 1,
              "name": "建物の名前",
              "type": "landmark",
              "description": "外見や役割の詳細。",
              "position": {{
                "x": 開始X座標(int),
                "z": 開始Z座標(int),
                "width": X方向の幅(int),
                "depth": Z方向の奥行き(int)
              }},
              "decorations": ["特徴的な装飾ブロックのアイデア"]
            }}
          ]
        }}
        """
        response = self.chat_session.send_message(prompt)
        
        # Debug
        print(f"Zoning Raw Response: {response.text}")

        try:
             if response.parsed:
                 return response.parsed
        except:
             pass
             
        # Fallback
        import json
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)

    def generate_voxel_prompt(self, building_type: str, style: str = "Minecraft") -> str:
        """
        Generates a Text-to-3D prompt optimized for voxel/Minecraft style.
        Targeting Meshy-6 Text-to-3D API.
        """
        print(f"Generating Voxel Prompt for: {building_type}...")
        
        system_instruction = """
        You are an expert 3D generative artist specializing in voxel art and Minecraft aesthetics.
        Your task is to create a highly detailed text prompt for an AI 3D model generator (Meshy).
        The goal is to generate a 3D model that looks like it belongs in Minecraft.
        
        Guidelines:
        1. Start with "Minecraft-style voxel [Object Name]".
        2. Emphasize "blocky geometric shapes", "cube-based architecture", "flat surfaces", "sharp edges".
        3. Explicitly forbid "organic curves", "round shapes", "high poly".
        4. Focus on architectural details: roof type, window style, materials (brick, stone, wood).
        5. Use keywords like "isometric game-ready asset", "low poly", "finely detailed textures".
        6. Keep the description under 500 characters.
        7. Output ONLY the English prompt.
        """
        
        user_prompt = f"Create a Meshy Text-to-3D prompt for a {style} style {building_type}."
        
        try:
            # Use generate_text method instead of direct client usage if possible, 
            # but generate_text is simple. Let's use direct client call for specific config.
            # Or reuse generate_text if it allows system instruction override? 
            # Looking at existing code, generate_text takes system_instruction.
            
            return self.generate_text(user_prompt, system_instruction=system_instruction)

        except Exception as e:
            print(f"Error generating voxel prompt: {e}")
            return f"Minecraft-style voxel {building_type}, blocky, low-poly, game asset"
