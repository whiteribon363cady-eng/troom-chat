import os
import requests
import streamlit as st

# ページの基本設定（スマホのブラウザでも見やすいように最適化）
st.set_page_config(
    page_title="Ｔroom - LINE風チャット", page_icon="💬", layout="centered"
)

# --- LINE風のデザインスタイル（CSS調整） ---
st.markdown(
    """
    <style>
    /* 全体の背景色 */
    .stApp {
        background-color: #727D71; /* LINEのトークルーム背景に近い落ち着いた色 */
    }
    /* チャットメッセージの調整 */
    .chat-row {
        display: flex;
        align-items: flex-start;
        margin-bottom: 15px;
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
    .bubble {
        max-width: 70%;
        padding: 10px 14px;
        border-radius: 15px;
        font-size: 15px;
        line-height: 1.4;
        word-break: break-word;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .bubble.ai {
        background-color: #FFFFFF;
        color: #000000;
        border-top-left-radius: 3px;
    }
    .bubble.user {
        background-color: #85E249; /* LINEの送信メッセージ風の緑 */
        color: #000000;
        border-top-right-radius: 3px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- サイドバー：設定・API情報・アイコン変更 ---
with st.sidebar:
    st.header("⚙️ 設定メニュー")

    # DifyのAPIキー設定（サイドバーに入力）
    api_key_input = st.text_input(
        "Dify APIキー",
        type="password",
        value=os.getenv("DIFY_API_KEY", ""),
        placeholder="app-xxxxxxxxxxxx",
    )
    api_base_url = st.text_input(
        "API Base URL", value="https://api.dify.ai/v1"
    )

    st.markdown("---")
    st.subheader("🖼️ アイコンの変更")
    st.caption("いつでも好きな画像に変更できます")

    # AIアイコンのアップロード
    ai_img_file = st.file_uploader(
        "AIのアイコン画像", type=["png", "jpg", "jpeg"]
    )
    if ai_img_file is not None:
        st.session_state["ai_icon"] = ai_img_file
    elif "ai_icon" not in st.session_state:
        st.session_state["ai_icon"] = (
            "https://api.iconify.design/lucide:bot.svg?color=%23888888"
        )

    # ユーザーアイコンのアップロード
    user_img_file = st.file_uploader(
        "自分のアイコン画像", type=["png", "jpg", "jpeg"]
    )
    if user_img_file is not None:
        st.session_state["user_icon"] = user_img_file
    elif "user_icon" not in st.session_state:
        st.session_state["user_icon"] = (
            "https://api.iconify.design/lucide:user.svg?color=%23888888"
        )

    if st.button("🗑️ チャット履歴をクリア"):
        st.session_state.messages = []
        st.session_state.conversation_id = ""
        st.rerun()

# --- タイトル表示 ---
st.markdown(
    "<h3 style='text-align: center; color: white;'>Ｔroom チャット</h3>",
    unsafe_allow_html=True,
)

# --- セッション状態の初期化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = ""

# --- 過去のメッセージ表示 ---
for message in st.session_state.messages:
    role = message["role"]
    content = message["content"]

    if role == "user":
        # ユーザー側（右側）
        st.markdown(
            f"""
            <div class="chat-row user">
                <div class="bubble user">{content}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # AI側（左側）
        st.markdown(
            f"""
            <div class="chat-row">
                <div class="bubble ai">{content}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# --- チャット入力欄 ---
if prompt := st.chat_input("メッセージを入力... (ユウカ、アオイ、ノアなど)"):
    if not api_key_input:
        st.warning("⚠️ サイドバーにDifyのAPIキーを入力してください。")
    else:
        # ユーザーの入力を履歴に追加
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

# ユーザー発言後のDify API呼び出し処理
if (
    st.session_state.messages
    and st.session_state.messages[-1]["role"] == "user"
):
    last_user_msg = st.session_state.messages[-1]["content"]

    with st.spinner("Ｔroomのメンバーが考えています..."):
        headers = {
            "Authorization": f"Bearer {api_key_input}",
            "Content-Type": "application/json",
        }

        payload = {
            "inputs": {},
            "query": last_user_msg,
            "response_mode": "blocking",
            "user": "toshifumi-user",
            "conversation_id": st.session_state.conversation_id,
        }

        try:
            url = f"{api_base_url.rstrip('/')}/chat-messages"
            response = requests.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                res_data = response.json()
                ai_answer = res_data.get("answer", "（返答がありませんでした）")
                st.session_state.conversation_id = res_data.get(
                    "conversation_id", ""
                )

                # AIの返答を履歴に追加
                st.session_state.messages.append(
                    {"role": "assistant", "content": ai_answer}
                )
                st.rerun()
            else:
                st.error(
                    f"APIエラーが発生しました (ステータスコード: {response.status_code}): {response.text}"
                )
        except Exception as e:
            st.error(f"通信エラーが発生しました: {e}")
