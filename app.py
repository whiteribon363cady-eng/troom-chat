import json
import os
import streamlit as st
import requests

# ページの設定
st.set_page_config(page_title="Ｔroom - LINE風チャット", page_icon="💬", layout="centered")

# スタイリング（LINE風チャット＆メタ情報表示用）
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
        width: 40px;
        height: 40px;
        border-radius: 50%;
        object-fit: cover;
        margin: 0 10px;
    }
    .bubble-container {
        max-width: 70%;
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
        margin-top: 5px;
        border-left: 3px solid #84eb63;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# サイドバー：設定メニュー
st.sidebar.markdown("## ⚙️ 設定メニュー")
api_key = st.sidebar.text_input("Dify APIキー", type="password", value="")
api_base_url = st.sidebar.text_input(
    "API Base URL", value="https://api.dify.ai/v1"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🖼️ キャラクター別アイコン設定")

# デフォルトのアイコン画像
default_ai_icon = "https://api.iconify.design/noto:girl.svg"
user_avatar_path = "https://api.iconify.design/noto:boy.svg"

# 個別アイコンのファイルアップローダー
yuuka_icon_file = st.sidebar.file_uploader(
    "ユウカのアイコン", type=["png", "jpg", "jpeg"], key="yuuka"
)
aoi_icon_file = st.sidebar.file_uploader(
    "アオイのアイコン", type=["png", "jpg", "jpeg"], key="aoi"
)
noa_icon_file = st.sidebar.file_uploader(
    "ノアのアイコン", type=["png", "jpg", "jpeg"], key="noa"
)
user_icon_file = st.sidebar.file_uploader(
    "自分のアイコン", type=["png", "jpg", "jpeg"], key="user"
)

# 保存先フォルダの作成
os.makedirs("temp_imgs", exist_ok=True)


# パスを管理する関数
def save_uploaded_file(uploaded_file, default_path):
    if uploaded_file is not None:
        path = os.path.join("temp_imgs", uploaded_file.name)
        with open(path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return path
    return default_path


yuuka_avatar_path = save_uploaded_file(yuuka_icon_file, default_ai_icon)
aoi_avatar_path = save_uploaded_file(aoi_icon_file, default_ai_icon)
noa_avatar_path = save_uploaded_file(noa_icon_file, default_ai_icon)
user_avatar_path = save_uploaded_file(user_icon_file, user_avatar_path)


# キャラクター名に応じてアイコンを振り分ける関数
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

st.title("Ｔroom チャット")

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

        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                display_text = parsed.get("message", content)
                char_name = parsed.get("Name", "AI")
                time_val = parsed.get("Time", "")
                loc_val = parsed.get("Location", "")
                outfit = parsed.get("Outfit", "")
                expr = parsed.get("Expression", "")
                meta_info = f"📍 {loc_val} | ⏰ {time_val} | 👗 {outfit} | ✨ {expr}"
        except json.JSONDecodeError:
            pass

        current_avatar = get_character_avatar(char_name)
        meta_html = (
            f'<div class="meta-box">{meta_info}</div>' if meta_info else ""
        )

        st.markdown(
            f"""
            <div class="chat-row ai">
                <img src="{current_avatar}" class="avatar">
                <div class="bubble-container">
                    <div class="sender-name">{char_name}</div>
                    <div class="bubble">{display_text}{meta_html}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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

                st.session_state.messages.append(
                    {"role": "ai", "content": answer}
                )

                display_text = answer
                meta_info = None
                char_name = "AI"

                try:
                    parsed = json.loads(answer)
                    if isinstance(parsed, dict):
                        display_text = parsed.get("message", answer)
                        char_name = parsed.get("Name", "AI")
                        time_val = parsed.get("Time", "")
                        loc_val = parsed.get("Location", "")
                        outfit = parsed.get("Outfit", "")
                        expr = parsed.get("Expression", "")
                        meta_info = (
                            f"📍 {loc_val} | ⏰ {time_val} | 👗 {outfit} | ✨ {expr}"
                        )
                except json.JSONDecodeError:
                    pass

                current_avatar = get_character_avatar(char_name)
                meta_html = (
                    f'<div class="meta-box">{meta_info}</div>' if meta_info else ""
                )

                st.markdown(
                    f"""
                    <div class="chat-row ai">
                        <img src="{current_avatar}" class="avatar">
                        <div class="bubble-container">
                            <div class="sender-name">{char_name}</div>
                            <div class="bubble">{display_text}{meta_html}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.error(
                    f"APIエラーが発生しました (ステータスコード: {response.status_code}): {response.text}"
                )
        except Exception as e:
            st.error(f"通信エラーが発生しました: {e}")
