import base64
import io
import json
import os
import re
import requests
import streamlit as st
from PIL import Image

# ページの設定
st.set_page_config(
    page_title="Ｔroom - LINE風チャット", page_icon="💬", layout="centered"
)

# スタイリング（LINE風チャット＆丸型アイコン・画像デザイン用）
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
.chat-img-container { position: relative; width: 100%; margin-top: 8px; margin-bottom: 8px; }
.chat-img { width: 100%; max-height: 280px; object-fit: cover; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
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
st.sidebar.markdown("### 🖼️ キャラクターアイコン設定")
default_ai_icon = "https://api.iconify.design/noto:girl.svg"
user_default_icon = "https://api.iconify.design/noto:boy.svg"

# セッションステートの初期化（永続保持）
if "yuuka_avatar" not in st.session_state:
  st.session_state.yuuka_avatar = default_ai_icon
if "aoi_avatar" not in st.session_state:
  st.session_state.aoi_avatar = default_ai_icon
if "noa_avatar" not in st.session_state:
  st.session_state.noa_avatar = default_ai_icon
if "user_avatar" not in st.session_state:
  st.session_state.user_avatar = user_default_icon


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


# 各ファイルアップローダーの配置
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

# 新しくファイルがアップロードされた場合のみセッションを更新する（保持する仕様）
if yuuka_icon_file is not None:
  st.session_state.yuuka_avatar = process_avatar_fixed(
      yuuka_icon_file, st.session_state.yuuka_avatar, "yuuka"
  )
if aoi_icon_file is not None:
  st.session_state.aoi_avatar = process_avatar_fixed(
      aoi_icon_file, st.session_state.aoi_avatar, "aoi"
  )
if noa_icon_file is not None:
  st.session_state.noa_avatar = process_avatar_fixed(
      noa_icon_file, st.session_state.noa_avatar, "noa"
  )
if user_icon_file is not None:
  st.session_state.user_avatar = process_avatar_fixed(
      user_icon_file, st.session_state.user_avatar, "user"
  )


def get_character_avatar(char_name):
  c_name = str(char_name).strip()
  if "アオイ" in c_name:
    return st.session_state.aoi_avatar
  elif "ノア" in c_name:
    return st.session_state.noa_avatar
  elif "ユウカ" in c_name:
    return st.session_state.yuuka_avatar
  else:
    return st.session_state.yuuka_avatar


if st.sidebar.button("🗑️ チャット履歴をクリア"):
  st.session_state.messages = []
  st.rerun()

if "messages" not in st.session_state:
  st.session_state.messages = []


# AIからのメッセージを解析し、単体または複数（みんな）の吹き出しを順番に描画する関数
def render_ai_message(content):
  raw_content = str(content)
  parsed_list = []

  # 1. まず全体（<think>タグの中も含めて）からリスト形式（[ ... ]）のJSONを探す
  try:
    start_idx = raw_content.find("[")
    end_idx = raw_content.rfind("]")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
      json_str = raw_content[start_idx : end_idx + 1]
      parsed_list = json.loads(json_str)
  except Exception:
    pass

  # 2. リストでなければ、単体オブジェクト形式（{ ... }）のJSONを探す
  if not isinstance(parsed_list, list) or not parsed_list:
    try:
      cleaned = re.sub(r"<think>.*?</think>", "", raw_content, flags=re.DOTALL)
      start_idx = cleaned.find("{")
      end_idx = cleaned.rfind("}")
      if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_str = cleaned[start_idx : end_idx + 1]
        single_parsed = json.loads(json_str)
        if isinstance(single_parsed, dict):
          parsed_list = [single_parsed]
    except Exception:
      pass

  # 3. それでもパースできなかった場合のフォールバック
  if not parsed_list:
    cleaned = re.sub(r"<think>.*?</think>", "", raw_content, flags=re.DOTALL).strip()
    detected_name = "ユウカ"
    if "アオイ" in cleaned:
      detected_name = "アオイ"
    elif "ノア" in cleaned:
      detected_name = "ノア"
    parsed_list = [{"Name": detected_name, "message": cleaned, "Image": ""}]

  # リストに含まれるキャラクターごとに順番に吹き出しを描画
  for idx, item in enumerate(parsed_list):
    if not isinstance(item, dict):
      continue

    detected_name = str(item.get("Name", item.get("name", "ユウカ"))).strip()
    display_text = str(
        item.get("message", item.get("text", item.get("content", "")))
    ).strip()

    if not display_text:
      display_text = str(item)

    current_avatar = get_character_avatar(detected_name)
    image_url = current_avatar

    custom_img = (
        item.get("Image", "")
        or item.get("image", "")
        or item.get("image_prompt", "")
    )

    if custom_img:
      clean_val = str(custom_img).strip()
      clean_val = re.sub(r"^\[.*?\]\((.*?)\)$", r"\1", clean_val)
      clean_val = clean_val.strip('"').strip("'").rstrip("}").strip()

      if clean_val.startswith("http") or clean_val.startswith("data:"):
        image_url = clean_val.split(" ")[0]
      else:
        import urllib.parse

        c_name = str(detected_name).strip()

        # ★ リアル感を抑え、パキッとした2Dアニメ（セルシェーディング調）にするためのベースプロンプト
        anime_2d_base = (
            "masterpiece, best quality, 2d animation, flat color, cel shading, "
            "clean lines, high quality anime drawing, vivid colors, "
            "completely removing photorealistic, no realism"
        )

        if "アオイ" in c_name:
          char_base = (
              f"{anime_2d_base}, 31-year-old smart Japanese woman Aoi, "
              "short dark bob hair, smart purple eyes, wearing a stylish dark blue "
              "business pants suit with white shirt, intelligent and cool expression"
          )
        elif "ノア" in c_name:
          char_base = (
              f"{anime_2d_base}, 31-year-old cool professional Japanese woman Noa, "
              "dark purple long hair tied in a half-up style, sharp intelligent eyes, "
              "wearing a dark grey business suit jacket and skirt with white shirt"
          )
        else:
          char_base = (
              f"{anime_2d_base}, 31-year-old Japanese woman Yuuka, "
              "long brown wavy hair with braided side hair ornament, warm amber eyes, "
              "wearing wine-red off-shoulder sweater, gentle smiling expression"
          )

        combined_prompt = f"{char_base}, {clean_val}"
        encoded_prompt = urllib.parse.quote(combined_prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=600&nologo=true"

    for marker in ["👗", "✨", "📍", "Time:", "Outfit:"]:
      if marker in display_text:
        display_text = display_text.split(marker)[0].strip()

    # 先頭の要素のみ画像を表示
    img_html = (
        f'<div class="chat-img-container"><img src="{image_url}"'
        ' class="chat-img"></div>'
        if idx == 0 and custom_img
        else ""
    )

    st.markdown(
        f"""
        <div class="chat-row ai">
            <img src="{current_avatar}" class="avatar">
            <div class="bubble-container">
                <div class="sender-name">{detected_name}</div>
                <div class="bubble">{img_html}{display_text}</div>
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
      with st.spinner("考えています...（応答中）"):
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
