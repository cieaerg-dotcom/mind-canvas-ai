import streamlit as st
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont
from streamlit_drawable_canvas import st_canvas
import io
import json
import base64
import numpy as np

# ==========================================
# 🚀 2026 終極無敵補丁：Base64 繞過法
# 徹底解決 Streamlit Cloud 上 image_to_url 的版本衝突
# ==========================================
import streamlit.elements.image as st_image

def bulletproof_image_to_url(data, *args, **kwargs):
    if isinstance(data, Image.Image):
        try:
            buf = io.BytesIO()
            data.save(buf, format="PNG")
            b64_str = base64.b64encode(buf.getvalue()).decode()
            return f"data:image/png;base64,{b64_str}"
        except Exception:
            return ""
    return ""

st_image.image_to_url = bulletproof_image_to_url

# ==========================================
# 0. 核心工具函數
# ==========================================
def add_watermark(image, text="Mind Canvas AI"):
    img = image.copy().convert("RGB")
    draw = ImageDraw.Draw(img)
    font_size = int(img.width * 0.025)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except:
        font = ImageFont.load_default()
    margin = 15
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = img.width - tw - margin, img.height - th - margin
    draw.text((x+1, y+1), text, font=font, fill=(0, 0, 0)) 
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 180)) 
    return img

def update_canvas_summary(client, history):
    summary_prompt = f"根據對話更新目前畫面構思狀態，回傳 JSON (主體, 環境, 光影, 風格)。對話：{history}"
    try:
        res = client.models.generate_content(model='gemini-3-flash-preview', contents=summary_prompt)
        clean_json = res.text.replace("```json", "").replace("```", "").strip()
        st.session_state.canvas_summary = json.loads(clean_json)
    except: pass

# ==========================================
# 1. 網頁基本設定
# ==========================================
st.set_page_config(page_title="腦內場景側寫師", page_icon="🎨", layout="wide")

if "gallery" not in st.session_state: st.session_state.gallery = []
if "canvas_reset_counter" not in st.session_state: st.session_state.canvas_reset_counter = 0
if "ai_sketch_img" not in st.session_state: st.session_state.ai_sketch_img = None

# 預先定義工具列 session_state，讓上方畫板能讀取
if "tool_choice" not in st.session_state: st.session_state.tool_choice = "pencil"
if "stroke_width" not in st.session_state: st.session_state.stroke_width = 3

# ==========================================
# 2. 側邊欄：設定、上傳與畫廊
# ==========================================
with st.sidebar:
    st.header("🖼️ 畫布尺寸設定")
    device_type = st.selectbox("載具類型：", ["手機", "平板", "電腦"])
    orientation = st.radio("方向：", ["直式", "橫式"])
    
    st.divider()
    st.header("📂 參考圖上傳")
    uploaded_ref = st.file_uploader("上傳你的靈感參考圖", type=["png", "jpg", "jpeg"])

    st.divider()
    st.header("🚀 繪師動作")
    enable_watermark = st.checkbox("🏷️ 在成品加上浮水印", value=True)
    generate_btn = st.button("✨ 最終具現化 (Imagen 4)", type="primary", use_container_width=True)

    if st.session_state.gallery:
        st.divider()
        st.header("📜 歷史畫廊")
        for idx, item in enumerate(reversed(st.session_state.gallery)):
            with st.expander(f"作品 {len(st.session_state.gallery) - idx}"):
                st.image(item["image"], use_container_width=True)
                st.download_button("⬇️ 下載", data=item["image_bytes"], file_name=f"art-{idx}.jpg", key=f"dl_{idx}")

# ==========================================
# 3. 主頁面佈局
# ==========================================
st.title("🎨 腦內場景側寫師：協作畫室")

col_chat, col_canvas = st.columns([1, 1])

with col_chat:
    api_key = st.text_input("🔑 API Key:", type="password")
    st.link_button("👉 點我取得免費 API Key", "https://aistudio.google.com/app/apikey")
    
    if api_key:
        client = genai.Client(api_key=api_key)
        
        if "messages" not in st.session_state:
            system_instruction = """
            你是一位充滿熱情、地位平等的「場景繪師」。你正與一位搭檔（使用者）共同構思一個視覺傑作。
            你的目標是透過輕鬆、專業且像好朋友般的聊天，與搭檔磨合出最完美的畫面。並且完全使用繁體中文。

            你的溝通準則：
            1. **平等協作**：不要像老師一樣下指令。改用「我覺得...」、「我們試試看...」或「如果你覺得不錯的話，我們或許可以...」這類的口吻。
            2. **主動貢獻靈感**：當搭檔提出一個想法，你除了肯定之外，要主動疊加一個專業繪師的見解。
            3. **視覺專家的直覺**：自然地提到構圖或光影的建議，就像兩個高手在討論。
            4. **節奏掌控**：每次回覆只拋出一個點子來討論。當聊到一個段落，建議：「這構思不錯喔，我先幫你勾個大概的構圖（SVG）給你看，你再告訴我哪裡要修？」
            5. **共同守護**：在按下出圖按鈕前，確保雙方都對這個「共同結晶」感到興奮。
            """
            st.session_state.messages = [{"role": "assistant", "content": "嘿！你來了 🎨。我正在看空白畫布，你有什麼好點子嗎？不管是哪種模糊的感覺都可以，我們一起來把那個場景生出來！"}]
            st.session_state.persona = system_instruction
            st.session_state.canvas_summary = {"主體": "討論中", "環境": "討論中
