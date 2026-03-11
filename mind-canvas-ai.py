import streamlit as st
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont
from streamlit_drawable_canvas import st_canvas
import io
import json
import base64
import numpy as np
import streamlit.components.v1 as components
import re

#==========================================
# 🚀 2026 終極無敵補丁：Base64 繞過法 (雲端專用)
#==========================================
import streamlit.elements.image as st_image

def bulletproof_image_to_url(data, *args, **kwargs):
    """直接繞過 Streamlit 內部管理器，將圖片轉為 Base64 字串"""
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

#==========================================
# 0. 核心工具函數
#==========================================
def add_watermark(image, text="Mind Canvas AI"):
    """為成品加上優雅的浮水印"""
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

def render_svg_animation(svg_content, h):
    """渲染具有繪製動畫效果的 SVG"""
    if not svg_content: return
    clean_svg = svg_content.replace("```svg\n", "").replace("```svg", "").replace("```", "").strip()
    if "<svg" in clean_svg:
        clean_svg = clean_svg.replace("<svg", '<svg style="max-width:100%; height:auto;"')
    
    animated_html = f"""
    <div style="display: flex; justify-content: center; align-items: center; background: #fafafa; padding: 10px; border-radius: 10px; border: 1px solid #ddd; overflow: hidden;">
        <style>
            svg path, svg circle, svg rect, svg line, svg polyline, svg polygon {{
                fill: none !important; stroke: #333 !important; stroke-width: 2 !important;
                stroke-dasharray: 2000; stroke-dashoffset: 2000;
                animation: draw 3s ease-in-out forwards;
            }}
            @keyframes draw {{ to {{ stroke-dashoffset: 0; }} }}
        </style>
        {clean_svg}
    </div>
    """
    components.html(animated_html, height=h + 50)

def update_canvas_summary(client, history, model_name):
    """提煉目前的對話狀態作為繪圖參考"""
    summary_prompt = f"根據對話更新目前畫面構思狀態，回傳 JSON (主體, 環境, 光影, 風格)。對話：{history}"
    try:
        res = client.models.generate_content(model=model_name, contents=summary_prompt)
        clean_json = res.text.replace("json", "").replace("```", "").strip()
        st.session_state.canvas_summary = json.loads(clean_json)
    except: pass

#==========================================
# [LOCKED: 模型列表與全域配置]
#==========================================
CHAT_MODEL_OPTIONS = ["gemini-3.1-pro-preview", "gemini-3.1-flash-lite-preview", "gemini-3-flash-preview",  "gemini-3-pro-preview", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"]
IMAGE_MODEL_OPTIONS =  ["gemini-3.1-pro-preview", "gemini-3.1-flash-lite-preview", "gemini-3-flash-preview",  "gemini-3-pro-preview", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro", "gemini-3.1-flash-image-preview", "gemini-3-pro-image-preview", "gemini-2.5-flash-image", "imagen-4.0-generate-001"]

if "available_models" not in st.session_state: st.session_state.available_models = []
if "api_key_valid" not in st.session_state: st.session_state.api_key_valid = False

def model_format_func(m_id):
    """格式化模型顯示名稱並標註權限"""
    if not st.session_state.api_key_valid: return m_id
    status = "✅" if m_id in st.session_state.available_models else "❌ (無權限)"
    return f"{m_id} {status}"

#==========================================
# 1. 網頁基本設定
#==========================================
st.set_page_config(page_title="腦內場景側寫師", page_icon="🎨", layout="wide")

if "gallery" not in st.session_state: st.session_state.gallery = []
if "canvas_reset_counter" not in st.session_state: st.session_state.canvas_reset_counter = 0
if "canvas_initial_drawing" not in st.session_state: st.session_state.canvas_initial_drawing = None
if "current_svg" not in st.session_state: st.session_state.current_svg = ""
if "tool_choice" not in st.session_state: st.session_state.tool_choice = "pencil"
if "stroke_width_val" not in st.session_state: st.session_state.stroke_width_val = 3

#==========================================
# 2. 側邊欄：設定、權限檢查與模型選取
#==========================================
with st.sidebar:
    st.header("🔑 設定與權限")
    api_key = st.text_input("輸入你的 API Key:", type="password", key="user_api_key")
    st.link_button("👉 取得免費 API Key", "https://aistudio.google.com/app/apikey")
    
    # --- [MODIFIED: 強化權限呼叫邏輯] ---
    if api_key:
        try:
            # 建立暫時 Client 進行預檢
            check_client = genai.Client(api_key=api_key)
            # 獲取模型清單並去前綴
            models_list = check_client.models.list()
            st.session_state.available_models = [m.name.split('/')[-1] for m in models_list]
            st.session_state.api_key_valid = True
        except Exception:
            st.session_state.available_models = []
            st.session_state.api_key_valid = False
    else:
        st.session_state.api_key_valid = False

    st.subheader("🤖 模型配置")
    selected_chat_model = st.selectbox("對話模型：", CHAT_MODEL_OPTIONS, format_func=model_format_func)
    selected_image_model = st.selectbox("出圖模型：", IMAGE_MODEL_OPTIONS, format_func=model_format_func)
    
    # 定義權限旗標
    is_chat_allowed = selected_chat_model in st.session_state.available_models
    is_image_allowed = selected_image_model in st.session_state.available_models
    # --- [END MODIFIED] ---

    st.divider()
    st.header("🖼️ 畫布尺寸設定")
    device_type = st.selectbox("載具類型：", ["手機", "平板", "電腦"])
    orientation = st.radio("方向：", ["直式", "橫式"])
    
    st.divider()
    st.header("📂 參考圖上傳")
    uploaded_ref = st.file_uploader("上傳靈感參考圖", type=["png", "jpg", "jpeg"])
    
    st.divider()
    st.header("🚀 最終行動")
    enable_watermark = st.checkbox("🏷️ 加上浮水印", value=True)
    generate_btn = st.button("✨ 最終具現化 (Imagen)", type="primary", use_container_width=True)
    
    if st.session_state.gallery:
        st.divider()
        st.header("📜 歷史畫廊")
        for idx, item in enumerate(reversed(st.session_state.gallery)):
            with st.expander(f"作品 {len(st.session_state.gallery) - idx}"):
                st.image(item["image"], use_container_width=True)
                st.download_button("⬇️ 下載", data=item["image_bytes"], file_name=f"art-{idx}.jpg", key=f"dl_{idx}")

#==========================================
# 📐 畫板比例動態計算
#==========================================
MAX_SIDE = 400
if device_type == "手機":
    canvas_w, canvas_h = (int(MAX_SIDE * 9/16), MAX_SIDE) if orientation == "直式" else (MAX_SIDE, int(MAX_SIDE * 9/16))
    ratio = "9:16" if orientation == "直式" else "16:9"
elif device_type == "平板":
    canvas_w, canvas_h = (int(MAX_SIDE * 3/4), MAX_SIDE) if orientation == "直式" else (MAX_SIDE, int(MAX_SIDE * 3/4))
    ratio = "3:4" if orientation == "直式" else "4:3"
else:
    canvas_w, canvas_h = MAX_SIDE, int(MAX_SIDE * 9/16)
    ratio = "16:9"

#==========================================
# 3. 主頁面佈局
#==========================================
st.title("🎨 腦內場景側寫師：畫布協作室")
col_chat, col_canvas = st.columns([1, 1])

with col_chat:
    if api_key:
        # [MODIFIED: 參考呼叫模式]
        client = genai.Client(api_key=api_key)
        if "messages" not in st.session_state:
            system_instruction = """ 你是一位充滿熱情、地位平等的「場景繪師」。你正與一位搭檔（使用者）共同構思一個視覺傑作。你的目標是透過輕鬆、專業且像好朋友般的聊天，與搭檔磨合出最完美的畫面。並且完全使用繁體中文。 """
            st.session_state.messages = [{"role": "assistant", "content": "嘿！你來了 🎨。你有什麼好點子嗎？"}]
            st.session_state.persona = system_instruction
            st.session_state.canvas_summary = {"主體": "討論中", "環境": "討論中", "光影": "討論中", "風格": "討論中"}

        st.markdown("#### 📝 繪師的草圖筆記")
        s_cols = st.columns(4)
        for i, (k, v) in enumerate(st.session_state.canvas_summary.items()):
            s_cols[i].caption(f"**{k}**")
            s_cols[i].write(f"`{v}`")

        chat_placeholder = st.container(height=450)
        with chat_placeholder:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])
        prompt = st.chat_input("跟繪師聊聊你的點子...")
    else:
        st.info("👋 請先在左側邊欄輸入 API Key 以開始協作！")

with col_canvas:
    st.markdown("#### 🖌️ 繪師的 SVG 構圖示範")
    if st.session_state.get("current_svg"):
        render_svg_animation(st.session_state.current_svg, canvas_h)
    else:
        st.info("點擊下方按鈕，我會現場勾勒線條給你看。")

    st.markdown(f"#### ✍️ 協作畫布 ({device_type} {orientation})")
    
    color = "#000000" if st.session_state.tool_choice == "pencil" else "#ffffff"
    width = st.session_state.stroke_width_val if st.session_state.tool_choice == "pencil" else st.session_state.stroke_width_val + 10

    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",
        stroke_width=width, stroke_color=color,
        background_color="#ffffff", update_streamlit=True,
        height=canvas_h, width=canvas_w, drawing_mode="freedraw",
        initial_drawing=st.session_state.canvas_initial_drawing,
        key=f"canvas_{st.session_state.canvas_reset_counter}_{device_type}_{orientation}",
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        st.radio("工具：", ["pencil", "eraser"], format_func=lambda x: "🖊️ 鉛筆" if x=="pencil" else "🧽 橡皮擦", key="tool_choice", horizontal=True)
    with c2:
        st.slider("粗細：", 1, 30, 3, key="stroke_width_val")

    cb1, cb2 = st.columns([1, 1])
    with cb1:
        send_drawing_btn = st.button("📤 傳送我的塗鴉", use_container_width=True)
    with cb2:
        draw_sketch_btn = st.button("🖌️ 請繪師示範構圖", use_container_width=True, type="primary")

#==========================================
# 4. 邏輯處理：AI 對話與請求
#==========================================
def send_message_to_ai(client, text_prompt, include_canvas=False):
    # [MODIFIED: 嚴格權限檢查]
    if not is_chat_allowed:
        st.warning(f"⚠️ 權限不足：您的 API Key 不支援使用 `{selected_chat_model}`。")
        return

    current_parts = []
    if text_prompt:
        current_parts.append({"text": text_prompt})
    else:
        current_parts.append({"text": "（搭檔傳送了一張塗鴉草稿，請看圖給予建議）"})

    if include_canvas and canvas_result and canvas_result.image_data is not None:
        if np.any(canvas_result.image_data[:, :, 3] > 0):
            white_bg = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
            canvas_img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
            white_bg.paste(canvas_img, (0, 0), canvas_img)
            buf = io.BytesIO(); white_bg.save(buf, format="JPEG")
            current_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": buf.getvalue()}})
            
    if uploaded_ref:
        ref_img = Image.open(uploaded_ref).convert("RGB")
        buf = io.BytesIO(); ref_img.save(buf, format="JPEG")
        current_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": buf.getvalue()}})

    display_text = text_prompt if text_prompt else "【已傳送塗鴉板畫面】"
    st.session_state.messages.append({"role": "user", "content": display_text})

    with chat_placeholder:
        with st.chat_message("user"): st.markdown(display_text)
        with st.chat_message("assistant"):
            try:
                full_contents = []
                for m in st.session_state.messages[:-1]:
                    role = "user" if m["role"] == "user" else "model"
                    full_contents.append({"role": role, "parts": [{"text": m["content"]}]})
                full_contents.append({"role": "user", "parts": current_parts})

                # [MODIFIED: 參考呼叫模式]
                resp = client.models.generate_content(
                    model=selected_chat_model,
                    contents=full_contents,
                    config=types.GenerateContentConfig(system_instruction=st.session_state.persona, temperature=0.7)
                )
                
                ai_reply = resp.text
                
                # 攔截 SVG
                svg_pattern = r"```[a-zA-Z]*\s*(<svg[\s\S]*?</svg>)\s*```|(<svg[\s\S]*?</svg>)"
                svg_match = re.search(svg_pattern, ai_reply, re.IGNORECASE)
                if svg_match:
                    st.session_state.current_svg = svg_match.group(1) if svg_match.group(1) else svg_match.group(2)
                    ai_reply = re.sub(svg_pattern, "\n\n*(我在上方為你畫了一張草圖，看看這個感覺對不對？)*\n\n", ai_reply, flags=re.IGNORECASE)

                ai_reply = re.sub(r"```[\s\S]*?```", "\n\n*(繪師優雅地收起了技術細節...)*\n\n", ai_reply)

                st.markdown(ai_reply)
                st.session_state.messages.append({"role": "assistant", "content": ai_reply})
                update_canvas_summary(client, "\n".join([m['content'] for m in st.session_state.messages]), selected_chat_model)
                st.rerun()
            except Exception as e: st.error(f"對話錯誤：{e}")

#==========================================
# 最終行動
#==========================================
if api_key:
    if prompt: send_message_to_ai(client, prompt, include_canvas=False)
    if send_drawing_btn: send_message_to_ai(client, "", include_canvas=True)
    
    if draw_sketch_btn:
        if not is_chat_allowed:
            st.warning("⚠️ 繪師現在無法動筆，請檢查權限。")
        else:
            with st.spinner("繪師正在運筆..."):
                hist = "\n".join([m['content'] for m in st.session_state.messages])
                # [MODIFIED: 參考呼叫模式]
                canvas_req = client.models.generate_content(
                    model=selected_chat_model,
                    contents=f"請根據對話，生成一個簡潔的 SVG 作為構圖示範（尺寸 {canvas_w}x{canvas_h}）。對話：{hist}"
                )
                try:
                    match = re.search(r"<svg[\s\S]*?</svg>", canvas_req.text, re.IGNORECASE)
                    if match:
                        st.session_state.current_svg = match.group(0)
                        st.rerun()
                except: st.warning("繪師手滑了，請再試一次。")
    
    if generate_btn:
        if not is_image_allowed:
            st.error(f"🚫 無法具現化：您的 API Key 無權限呼叫 `{selected_image_model}`。")
        else:
            with st.spinner(f"✨ {selected_image_model} 具現化中..."):
                try:
                    chat_hist = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
                    p_req = client.models.generate_content(model=selected_chat_model,
                        contents=f"提煉英文 {selected_image_model} 指令。這是一張 {ratio} 比例的構圖：{chat_hist}")
                    
                    img_res = client.models.generate_images(model=selected_image_model,
                        prompt=p_req.text, config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio=ratio))
                    
                    if img_res.generated_images:
                        raw_bytes = img_res.generated_images[0].image.image_bytes
                        final_img = Image.open(io.BytesIO(raw_bytes))
                        if enable_watermark: final_img = add_watermark(final_img)
                        buf = io.BytesIO(); final_img.save(buf, format="JPEG")
                        st.session_state.gallery.append({"image": final_img, "image_bytes": buf.getvalue()})
                        with chat_placeholder: st.image(final_img, caption="具現化完成")
                        st.download_button("⬇️ 下載", data=buf.getvalue(), file_name="art.jpg")
                except Exception as e: st.error(f"出圖失敗：{e}")
