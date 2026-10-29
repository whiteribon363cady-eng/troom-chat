import base64
import json
import os
import re
import requests
import streamlit as st

# ページの設定
st.set_page_config(
    page_title="Ｔroom - LINE風チャット", page_icon="💬", layout="centered"
)

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
    background-color: #f0f2f5;
    margin: 0 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.15);
    flex-shrink: 0;
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

# サイドバー：設定メニュー
st.sidebar.markdown("## ⚙️ 設定メニュー")
api_key = st.sidebar.text_input(
    "Dify APIキー", type="password", value="app-pAwP6UDpxXlomy9C7nqG5t8Q"
)
api_base_url = st.sidebar.text_input(
    "API Base URL", value="https://api.dify.ai/v1"
)
st.sidebar.markdown("---")
st.sidebar.markdown("### 🖼️ アイコン設定")

default_ai_icon = "https://api.iconify.design/noto:girl.svg"
user_default_icon = "https://api.iconify.design/noto:boy.svg"

# アイコン用画像をアップロード
yuuka_icon_file = st.sidebar.file_uploader("ユウカのアイコン", type=["png", "jpg", "jpeg"], key="yuuka_up")
aoi_icon_file = st.sidebar.file_uploader("アオイのアイコン", type=["png", "jpg", "jpeg"], key="aoi_up")
noa_icon_file = st.sidebar.file_uploader("ノアのアイコン", type=["png", "jpg", "jpeg"], key="noa_up")
user_icon_file = st.sidebar.file_uploader("自分のアイコン", type=["png", "jpg", "jpeg"], key="user_up")

# 画像のアスペクト比を維持して綺麗に正方形クロップする関数
def process_avatar_fixed(uploaded_file, default_url, key_prefix):
    if uploaded_file is not None:
        try:
            from PIL import Image
            import io
            image = Image.open(uploaded_file)
            image = image.convert("RGB")
            width, height = image.size
            st.sidebar.markdown(f"**{uploaded_file.name} の調整**")
            zoom = st.sidebar.slider("ズーム (拡大)", 1.0, 3.0, 1.2, 0.1, key=f"{key_prefix}_zoom")
            min_side = min(width, height)
            crop_size = int(min_side / zoom)
            max_x = max(0, width - crop_size)
            max_y = max(0, height - crop_size)
            offset_x = (st.sidebar.slider("左右の位置", 0, max(1, max_x), max_x // 2, key=f"{key_prefix}_x") if max_x > 0 else 0)
            offset_y = (st.sidebar.slider("上下の位置", 0, max(1, max_y), max_y // 2, key=f"{key_prefix}_y") if max_y > 0 else 0)
            cropped = image.crop((offset_x, offset_y, offset_x + crop_size, offset_y + crop_size))
            cropped = cropped.resize((200, 200), Image.Resampling.LANCZOS)
            buffered = io.BytesIO()
            cropped.save(buffered, format="JPEG")
            encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{encoded}"
        except Exception:
            bytes_data = uploaded_file.getvalue()
            encoded = base64.b64encode(bytes_data).decode("utf-8")
            return f"data:image/jpeg;base64,{encoded}"
    return default_url

# --- セッションステートにアイコンを永続化保存する処理（確実な維持・リロード対策） ---
if "yuuka_avatar" not in st.session_state:
    st.session_state.yuuka_avatar = default_ai_icon
if "aoi_avatar" not in st.session_state:
    st.session_state.aoi_avatar = default_ai_icon
if "noa_avatar" not in st.session_state:
    st.session_state.noa_avatar = default_ai_icon
if "user_avatar" not in st.session_state:
    st.session_state.user_avatar = user_default_icon

# 新しくファイルがアップロードされたときだけ変換してセッションを上書きする
if yuuka_icon_file is not None:
    st.session_state.yuuka_avatar = process_avatar_fixed(yuuka_icon_file, default_ai_icon, "yuuka")
if aoi_icon_file is not None:
    st.session_state.aoi_avatar = process_avatar_fixed(aoi_icon_file, default_ai_icon, "aoi")
if noa_icon_file is not None:
    st.session_state.noa_avatar = process_avatar_fixed(noa_icon_file, default_ai_icon, "noa")
if user_icon_file is not None:
    st.session_state.user_avatar = process_avatar_fixed(user_icon_file, user_default_icon, "user")


# キャラクター名に応じたアイコンを確実に取り出す関数
def get_character_avatar(char_name):
  if "アオイ" in char_name:
    return st.session_state.aoi_avatar
  elif "ノア" in char_name:
    return st.session_state.noa_avatar
  elif "ユウカ" in char_name:
    return st.session_state.yuuka_avatar
  else:
    return st.session_state.yuuka_avatar


if st.sidebar.button("🗑️ チャット履歴をクリア"):
  st.session_state.messages = []
  st.rerun()

if "messages" not in st.session_state:
  st.session_state.messages = []


# AIの返信メッセージを解析して描画する関数
def render_ai_message(content):
  cleaned = content.strip()

  # Markdownのコードブロック（```json ... ```）で囲まれていたら綺麗に剥ぎ取る
  if cleaned.startswith("```"):
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

  # 1. 個別指定のJSON形式の場合
  if cleaned.startswith("{") and cleaned.endswith("}"):
    try:
      parsed = json.loads(cleaned)
      if isinstance(parsed, dict):
        display_text = parsed.get("message", content)
        char_name = parsed.get("Name", "ユウカ")
        time_val = parsed.get("Time", "")
        loc_val = parsed.get("Location", "")
        outfit = parsed.get("Outfit", "")
        expr = parsed.get("Expression", "")
        img_url = parsed.get("Image", "")

        meta_info = (
            f"📍 {loc_val} | ⏰ {time_val} | 👗 {outfit} | ✨ {expr}"
            if loc_val or time_val
            else None
        )
        current_avatar = get_character_avatar(char_name)

        img_html = (
            f'<img src="{img_url}" class="chat-img">'
            if img_url and img_url.startswith("http")
            else ""
        )
        meta_html = (
            f'<div class="meta-box">{meta_info}</div>' if meta_info else ""
        )

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
        return
    except Exception:
      pass

  # 2. テキストの中に「アオイ：」「ノア：」「ユウカ：」が含まれている箇所をすべて見つけて個別分割する
  char_positions = []
  for c in ["ユウカ", "アオイ", "ノア"]:
    for match in re.finditer(rf"{c}\s*[:：]", cleaned):
      char_positions.append((match.start(), c))

  char_positions.sort(key=lambda x: x[0])
  matches = []

  if char_positions:
    for i in range(len(char_positions)):
      start_idx, char_name = char_positions[i]
      end_idx = (
          char_positions[i + 1][0] if i + 1 < len(char_positions) else len(cleaned)
      )

      chunk = cleaned[start_idx:end_idx].strip()
      speech_part = re.sub(r"^(ユウカ|アオイ|ノア)\s*[:：]\s*", "", chunk).strip()

      meta_text = None
      if "📍" in speech_part:
        parts = speech_part.split("📍")
        speech_part = parts[0].strip()
        meta_text = "📍 " + parts[1].strip()

      clean_speech = speech_part.strip("「『」』")
      if clean_speech:
        matches.append((char_name, clean_speech, meta_text))

  if matches:
    for i, (char_name, speech, meta_text) in enumerate(matches):
      current_avatar = get_character_avatar(char_name)
      meta_html = ""
      if i == len(matches) - 1 and meta_text:
        meta_html = f'<div class="meta-box">{meta_text}</div>'

      st.markdown(
          f"""
            <div class="chat-row ai">
                <img src="{current_avatar}" class="avatar">
                <div class="bubble-container">
                    <div class="sender-name">{char_name}</div>
                    <div class="bubble">{speech}{meta_html}</div>
                </div>
            </div>
            """,
          unsafe_allow_html=True,
      )
    return

  # 3. どちらにも当てはまらない通常のテキストの場合（本文に含まれる名前からアイコンを推測）
  detected_name = "ユウカ"
  if "アオイ" in content:
    detected_name = "アオイ"
  elif "ノア" in content:
    detected_name = "ノア"

  current_avatar = get_character_avatar(detected_name)
  st.markdown(
      f"""
      <div class="chat-row ai">
          <img src="{current_avatar}" class="avatar">
          <div class="bubble-container">
              <div class="sender-name">{detected_name}</div>
              <div class="bubble">{content}</div>
          </div>
      </div>
      """,
      unsafe_allow_html=True,
  )


# 過去のメッセージの表示
for msg in st.session_state.messages:
  if msg["role"] == "user":
    st.markdown(
        f"""
        <div class="chat-row user">
            <img src="{st.session_state.user_avatar}" class="avatar">
            <div class="bubble-container">
                <div class="sender-name">あなた</div>
                <div class="bubble">{msg["content"]}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
  else:
    render_ai_message(msg["content"])

# チャット入力
if prompt := st.chat_input("メッセージを入力... (ユウカ、アオイ、ノアなど)"):
  if not api_key:
    st.sidebar.error("左側のメニューからDify APIキーを入力してください。")
  else:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.markdown(
        f"""
        <div class="chat-row user">
            <img src="{st.session_state.user_avatar}" class="avatar">
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
            f"{api_base_url}/chat-messages", headers=headers, json=payload
        )

        if response.status_code == 200:
          res_data = response.json()
          answer = res_data.get("answer", "（応答がありませんでした）")
          st.session_state.messages.append({"role": "ai", "content": answer})
          render_ai_message(answer)
        else:
          st.error(
              f"APIエラーが発生しました (ステータスコード:"
              f" {response.status_code}): {response.text}"
          )
    except Exception as e:
      st.error(f"通信エラーが発生しました: {e}")
