import base64
import io
import json
import os
import re
import requests
import streamlit as st
from PIL import Image

# ページの設定
st.set_page_config(page_title="Ｔroom - LINE風チャット", page_icon="💬", layout="centered")

# スタイリング（LINE風チャット＆丸型アイコン・メタ情報表示用）
st.markdown(
    """
<style>
.chat-row { display: flex; align-items: flex-start; margin-bottom: 15px; width: 100%; }
.chat-row.user { flex-direction: row-reverse; }
.avatar { width: 42px; height: 42px; border-radius: 50%; object-fit: cover; background-color: #f0f2f5; margin: 0 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.15); flex-shrink: 0; }
.bubble-container { max-width: 75%; }
.sender-name { font-size: 12px; color: #666; margin-bottom: 3px; }
.chat-row.user .sender-name { text-align: right; }
.bubble { padding: 10px 14px; border-radius: 15px; font-size: 15px; line-height: 1.5; word-break: break-all; position: relative; }
.chat-row.ai .bubble { background-color: #ffffff; color: #333; border-top-left-radius: 2px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
.chat-row.user .bubble { background-color: #84eb63; color: #000; border-top-right-radius: 2px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
.meta-box { font-size: 11px; color: #888; background-color: #f0f2f5; padding: 6px 10px; border-radius: 8px; margin-top: 8px; border-left: 3px solid #84eb63; }
.chat-img { width: 100%; max-height: 300px; object-fit: cover; border-radius: 10px; margin-top: 8px; margin-bottom: 4px; }
</style>
""",
    unsafe_allow_html=True,
)

# サイドバー：設定メニュー
st.sidebar.markdown("## ⚙️ 設定メニュー")
api_key = st.sidebar.text_input(
    "Dify APIキー", type="password", value="app-pAwP6UDpxXlomy9C7nqG5t8Q"
)
api_base_url = st.sidebar.text_input("API Base URL", value="https://api.dify.ai/v1")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎨 Hugging Face 画像生成設定")
hf_token = st.sidebar.text_input(
    "Hugging Face トークン",
    type="password",
    value="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",
)
hf_model = st.sidebar.text_input(
    "Stable Diffusion モデル",
    value="runwayml/stable-diffusion-v1-5",
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🖼️ アイコン設定")
default_ai_icon = "https://api.iconify.design/noto:girl.svg"
user_default_icon = "https://api.iconify.design/noto:boy.svg"

# アイコン用画像をアップロード
yuuka_icon_file = st.sidebar.file_uploader(
    "ユウカのアイコン", type=["png", "jpg", "jpeg"], key="yuuka_up"
)
aoi_icon_file = st.sidebar.file_uploader(
    "アオイのアイコン", type=["png", "jpg", "jpeg"], key="aoi_up"
)
noa_icon_file = st.sidebar.file_uploader(
    "ノアのアイコン", type=["png", "jpg", "jpeg"], key="noa_up"
)
user_icon_file = st.sidebar.file_uploader(
    "自分のアイコン", type=["png", "jpg", "jpeg"], key="user_up"
)


# 画像のアスペクト比を維持して綺麗に正方形クロップする関数
def process_avatar_fixed(uploaded_file, default_url, key_prefix):
  if uploaded_file is not None:
    try:
      image = Image.open(uploaded_file)
      image = image.convert("RGB")
      width, height = image.size
      st.sidebar.markdown(f"**{uploaded_file.name} の調整**")
      zoom = st.sidebar.slider(
          "ズーム (拡大)",
          1.0,
          3.0,
          1.2,
          0.1,
          key=f"{key_prefix}_zoom",
      )
      min_side = min(width, height)
      crop_size = int(min_side / zoom)
      max_x = max(0, width - crop_size)
      max_y = max(0, height - crop_size)
      offset_x = (
          st.sidebar.slider(
              "左右の位置", 0, max(1, max_x), max_x // 2, key=f"{key_prefix}_x"
          )
          if max_x > 0
          else 0
      )
      offset_y = (
          st.sidebar.slider(
              "上下の位置", 0, max(1, max_y), max_y // 2, key=f"{key_prefix}_y"
          )
          if max_y > 0
          else 0
      )
      cropped = image.crop((
          offset_x,
          offset_y,
          offset_x + crop_size,
          offset_y + crop_size,
      ))
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


# セッションステートにアイコンを永続化保存する処理
if "yuuka_avatar" not in st.session_state:
  st.session_state.yuuka_avatar = default_ai_icon
if "aoi_avatar" not in st.session_state:
  st.session_state.aoi_avatar = default_ai_icon
if "noa_avatar" not in st.session_state:
  st.session_state.noa_avatar = default_ai_icon
if "user_avatar" not in st.session_state:
  st.session_state.user_avatar = user_default_icon

if yuuka_icon_file is not None:
  st.session_state.yuuka_avatar = process_avatar_fixed(
      yuuka_icon_file, default_ai_icon, "yuuka"
  )
if aoi_icon_file is not None:
  st.session_state.aoi_avatar = process_avatar_fixed(
      aoi_icon_file, default_ai_icon, "aoi"
  )
if noa_icon_file is not None:
  st.session_state.noa_avatar = process_avatar_fixed(
      noa_icon_file, default_ai_icon, "noa"
  )
if user_icon_file is not None:
  st.session_state.user_avatar = process_avatar_fixed(
      user_icon_file, user_default_icon, "user"
  )


# キャラクター名に応じたアイコンを取り出す関数
def get_character_avatar(char_name):
  if "アオイ" in str(char_name):
    return st.session_state.aoi_avatar
  elif "ノア" in str(char_name):
    return st.session_state.noa_avatar
  elif "ユウカ" in str(char_name):
    return st.session_state.yuuka_avatar
  else:
    return st.session_state.yuuka_avatar


if st.sidebar.button("🗑️ チャット履歴をクリア"):
  st.session_state.messages = []
  st.rerun()

if "messages" not in st.session_state:
  st.session_state.messages = []


# Python側からHugging Faceの画像生成APIを直接叩いてbase64画像に変換する関数
def generate_image_from_hf(prompt_text):
  if not hf_token:
    return None
  headers = {
      "Authorization": f"Bearer {hf_token}",
      "Content-Type": "application/json",
  }
  payload = {"inputs": prompt_text}
  api_url = f"https://api-inference.huggingface.co/models/{hf_model}"
  try:
    response = requests.post(api_url, headers=headers, json=payload, timeout=30)
    if response.status_code == 200:
      img_bytes = response.content
      encoded = base64.b64encode(img_bytes).decode("utf-8")
      return f"data:image/jpeg;base64,{encoded}"
  except Exception:
    pass
  return None


# AIの返信メッセージを解析して描画する関数（強力なフィルタリング付き）
def render_ai_message(content):
  cleaned = content.strip()

  # 1. LLMが混ぜてしまった英語の思考プロセス（"We need to..." など）が冒頭にある場合、最初のJSONの開き括弧 `{` までを全てカットする
  json_match_idx = cleaned.find("{")
  if json_match_idx > 0:
    cleaned = cleaned[json_match_idx:]

  # Markdownのコードブロック（```json ... ```）で囲まれていたら剥ぎ取る
  if cleaned.startswith("```"):
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

  # 2. 個別指定のJSON形式の場合
  if cleaned.startswith("{") and cleaned.endswith("}"):
    try:
      parsed = json.loads(cleaned)
      if isinstance(parsed, dict):
        display_text = parsed.get("message", content)
        char_name = parsed.get("Name", "ユウカ")
        if not char_name or char_name not in ["ユウカ", "アオイ", "ノア"]:
          if "アオイ" in cleaned:
            char_name = "アオイ"
          elif "ノア" in cleaned:
            char_name = "ノア"
          else:
            char_name = "ユウカ"

        time_val = parsed.get("Time", "")
        loc_val = parsed.get("Location", "")
        outfit = parsed.get("Outfit", "")
        expr = parsed.get("Expression", "")
        img_url = parsed.get("Image", "")

        # URLではない場合はHFで画像生成を試みる
        if (
            img_url
            and not img_url.startswith("http")
            and not img_url.startswith("data:")
        ):
          generated_img = generate_image_from_hf(img_url)
          if generated_img:
            img_url = generated_img

        meta_info = (
            f"📍 {loc_val} | ⏰ {time_val} | 👗 {outfit} | ✨ {expr}"
            if loc_val or time_val
            else None
        )
        current_avatar = get_character_avatar(char_name)

        img_html = (
            f'<img src="{img_url}" class="chat-img">'
            if img_url and (img_url.startswith("http") or img_url.startswith("data:"))
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

  # 3. 通常テキストやパースしきれなかった場合のフォールバック（思考ログの英文を非表示にする）
  # 英語の長文思考ログが含まれている場合は「Message:」以降や日本語の部分だけを抽出する
  if "Message:" in cleaned:
    try:
      parts = cleaned.split("Message:")
      if len(parts) > 1:
        cleaned = parts[1].strip().strip('"')
    except Exception:
      pass

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
                <div class="bubble">{cleaned}</div>
            </div>
        </div>
        """,
      unsafe_allow_html=True,
  )


# 過去のメッセージの描画
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
