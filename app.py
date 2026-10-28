import json
import os
import streamlit as st
import requests

# ページの設定
st.set_page_config(page_title="Ｔroom - LINE風チャット", page_icon="💬", layout="centered")

# スタイリング（LINE風チャット＆丸型アイコン・メタ情報表示用）
st.markdown(
    """
    <style>
    .chat-row {
        display: flex;
        align-items: flex-start;
        margin-bottom: 15px;
        width: 100%;
    }
    .chat-row.user {
        flex-direction: row-reverse;
    }
    .avatar {
        width: 42px;
        height: 42px;
        border-radius: 50%;
        object-fit: cover;
        margin: 0 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.15);
    }
    .bubble-container {
        max-width: 75%;
    }
    .sender-name {
        font-size: 12px;
        color: #666;
        margin-bottom: 3px;
    }
    .chat-row.user .sender-name {
        text-align: right;
    }
    .bubble {
        padding: 10px 14px;
        border-radius: 15px;
        font-size: 15px;
        line-height: 1.5;
        word-break: break-all;
        position: relative;
    }
    .chat-row.ai .bubble {
        background-color: #ffffff;
        color: #333;
        border-top-left-radius: 2px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .chat-row.user .bubble {
        background-color: #84eb63;
        color: #000;
        border-top-right-radius: 2px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .meta-box {
        font-size: 11px;
        color: #888;
        background-color: #f0f2f5;
        padding: 6px 10px;
        border-radius: 8px;
        margin-top: 8px;
        border-left: 3px solid #84eb63;
    }
    .chat-img {
        width: 100%;
        max-height: 300px;
        object-fit: cover;
        border-radius: 10px;
        margin-top: 8px;
        margin-bottom: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# サイドバー：設定メニュー（APIキーをあらかじめ保存・記憶しておきたい場合はここに初期値を入れられます）
st.sidebar.markdown("## ⚙️ 設定メニュー")
api_key = st.sidebar.text_input("Dify APIキー", type="password", value="app-pAwP6UDpxXlomy9C7nqG5t8Q")
api_base_url = st.sidebar.text_input("API Base URL", value="https://api.dify.ai/v1")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🖼️ アイコン設定（アップロードするか、そのまま使用）")

default_ai_icon = "https://api.iconify.design/noto:girl.svg"
user_default_icon = "https://api.iconify.design/noto:boy.svg"

yuuka_icon_file = st.sidebar.file_uploader("ユウカのアイコン", type=["png", "jpg", "jpeg"], key="yuuka")
aoi_icon_file = st.sidebar.file_uploader("アオイのアイコン", type=["png", "jpg", "jpeg"], key="aoi")
noa_icon_file = st.sidebar.file_uploader("ノアのアイコン", type=["png", "jpg", "jpeg"], key="noa")
user_icon_file = st.sidebar.file_uploader("自分のアイコン", type=["png", "jpg", "jpeg"], key="user")

import base64

# アップロードされた画像を自動で綺麗な丸型アイコン用に正方形トリミング＆変換する関数
def get_image_base64(uploaded_file, default_url):
    if uploaded_file is not None:
        try:
            from PIL import Image
            import io
            
            # Pillowを使って画像を読み込み、正方形に中央クロップしてリサイズ
            image = Image.open(uploaded_file)
            image = image.convert("RGB")
            
            width, height = image.size
            min_side = min(width, height)
            left = (width - min_side) / 2
            top = (height - min_side) / 2
            right = (width + min_side) / 2
            bottom = (height + min_side) / 2
            
            image = image.crop((left, top, right, bottom))
            image = image.resize((200, 200), Image.Resampling.LANCZOS)
            
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{encoded}"
        except Exception:
            # 万が一ライブラリの処理でエラーが出た場合のフォールバック
            bytes_data = uploaded_file.getvalue()
            encoded = base64.b64encode(bytes_data).decode("utf-8")
            return f"data:image/jpeg;base64,{encoded}"
            
    return default_url

yuuka_avatar_path = get_image_base64(yuuka_icon_file, default_ai_icon)
aoi_avatar_path = get_image_base64(aoi_icon_file, default_ai_icon)
noa_avatar_path = get_image_base64(noa_icon_file, default_ai_icon)
user_avatar_path = get_image_base64(user_icon_file, user_default_icon)

def get_character_avatar(char_name):
    if "ユウカ" in char_name:
        return yuuka_avatar_path
    elif "アオイ" in char_name:
        return aoi_avatar_path
    elif "ノア" in char_name:
        return noa_avatar_path
    else:
        return default_ai_icon

if st.sidebar.button("🗑️ チャット履歴をクリア"):
    st.session_state.messages = []
    st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

# 過去のメッセージの表示
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f"""
            <div class="chat-row user">
                <img src="{user_avatar_path}" class="avatar">
                <div class="bubble-container">
                    <div class="sender-name">あなた</div>
                    <div class="bubble">{msg["content"]}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        content = msg["content"]
        display_text = content
        meta_info = None
        char_name = "AI"
        img_url = None
        
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                display_text = parsed.get("message", content)
                char_name = parsed.get("Name", "AI")
                time_val = parsed.get("Time", "")
                loc_val = parsed.get("Location", "")
                outfit = parsed.get("Outfit", "")
                expr = parsed.get("Expression", "")
                img_url = parsed.get("Image", "")
                meta_info = f"📍 {loc_val} | ⏰ {time_val} | 👗 {outfit} | ✨ {expr}"
        except json.JSONDecodeError:
            pass
            
        current_avatar = get_character_avatar(char_name)
        img_html = f'<img src="{img_url}" class="chat-img">' if img_url and img_url.startswith("http") else ""
        meta_html = f'<div class="meta-box">{meta_info}</div>' if meta_info else ""
        
        st.markdown(
            f"""
            <div class="chat-row ai">
                <img src="{current_avatar}" class="avatar">
                <div class="bubble-container">
                    <div class="sender-name">{char_name}</div>
                    <div class="bubble">{img_html}{display_text}{meta_html}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# チャット入力
if prompt := st.chat_input("メッセージを入力... (ユウカ、アオイ、ノアなど)"):
    if not api_key:
        st.sidebar.error("左側のメニューからDify APIキーを入力してください。")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.markdown(
            f"""
            <div class="chat-row user">
                <img src="{user_avatar_path}" class="avatar">
                <div class="bubble-container">
                    <div class="sender-name">あなた</div>
                    <div class="bubble">{prompt}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": {},
            "query": prompt,
            "response_num": 1,
            "response_mode": "blocking",
            "user": "toshi-user",
        }
        
        try:
            with st.spinner("考えています..."):
                response = requests.post(
                    f"{api_base_url}/chat-messages",
                    headers=headers,
                    json=payload,
                )
                
                if response.status_code == 200:
                    res_data = response.json()
                    answer = res_data.get("answer", "（応答がありませんでした）")
                    st.session_state.messages.append({"role": "ai", "content": answer})
                    
                    display_text = answer
                    meta_info = None
                    char_name = "AI"
                    img_url = None
                    
                    try:
                        parsed = json.loads(answer)
                        if isinstance(parsed, dict):
                            display_text = parsed.get("message", answer)
                            char_name = parsed.get("Name", "AI")
                            time_val = parsed.get("Time", "")
                            loc_val = parsed.get("Location", "")
                            outfit = parsed.get("Outfit", "")
                            expr = parsed.get("Expression", "")
                            img_url = parsed.get("Image", "")
                            meta_info = f"📍 {loc_val} | ⏰ {time_val} | 👗 {outfit} | ✨ {expr}"
                    except json.JSONDecodeError as e:
            st.error(f"JSONパースエラーが発生しました: {e}")
                        pass
                        
                    current_avatar = get_character_avatar(char_name)
                    img_html = f'<img src="{img_url}" class="chat-img">' if img_url and img_url.startswith("http") else ""
                    meta_html = f'<div class="meta-box">{meta_info}</div>' if meta_info else ""
                    
                    st.markdown(
                        f"""
                        <div class="chat-row ai">
                            <img src="{current_avatar}" class="avatar">
                            <div class="bubble-container">
                                <div class="sender-name">{char_name}</div>
                                <div class="bubble">{img_html}{display_text}{meta_html}</div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.error(f"APIエラーが発生しました (ステータスコード: {response.status_code}): {response.text}")
        except Exception as e:
            st.error(f"通信エラーが発生しました: {e}")
