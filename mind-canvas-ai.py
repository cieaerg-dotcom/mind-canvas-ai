import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io

# ==========================================
# 1. 網頁基本設定 & 側邊欄設定
# ==========================================
st.set_page_config(page_title="腦內場景側寫師", page_icon="🎨", layout="centered")

with st.sidebar:
    st.header("🖼️ 畫布尺寸設定")
    st.markdown("請選擇你想將這幅畫用在哪裡？")
    
    device_type = st.selectbox("載具類型：", ["手機", "平板", "電腦"])
    orientation = st.radio("方向：", ["直式", "橫式"])
    
    aspect_ratio_mapping = {
        ("手機", "直式"): "9:16", ("手機", "橫式"): "16:9",
        ("平板", "直式"): "3:4", ("平板", "橫式"): "4:3",
        ("電腦", "直式"): "9:16", ("電腦", "橫式"): "16:9"
    }
    final_aspect_ratio = aspect_ratio_mapping.get((device_type, orientation), "1:1")
    
    st.divider()
    
    st.header("🛡️ 畫面防護網 (Negative Prompt)")
    negative_prompt_input = st.text_input("不想出現的元素：", placeholder="例如：文字, 浮水印, 變形的手, 模糊")

    ### 🚀 新增：側邊欄畫廊顯示區 🚀 ###
    st.divider()
    st.header("📜 歷史畫廊")
    if "gallery" in st.session_state and st.session_state.gallery:
        for idx, item in enumerate(reversed(st.session_state.gallery)):
            st.image(item["image"], caption=f"作品 {len(st.session_state.gallery) - idx}", use_container_width=True)
    else:
        st.info("目前還沒有產出作品喔！")
    ####################################

st.title("🎨 腦內場景側寫師")
st.markdown("告訴我你腦海中的一個初步畫面，我會引導你完善細節，最後為你畫出來！")

# ==========================================
# 2. API Key 設定
# ==========================================
api_key = st.text_input("請輸入你的 Gemini API Key:", type="password")

if api_key:
    client = genai.Client(api_key=api_key)
    
    # ==========================================
    # 3. 初始化 Session State
    # ==========================================
    if "messages" not in st.session_state:
        system_instruction = """
        你是一位「腦內場景側寫師」。引導使用者從大框架到豐富細節。
        請結合 1. 視覺結構 2. 感官情緒 3. 藝術風格 進行提問。
        當細節足夠，總結描述並提示使用者回覆「確認出圖」。
        """
        st.session_state.messages = [
            {"role": "system", "content": system_instruction},
            {"role": "assistant", "content": "你好！我是你的腦內場景側寫師 🧙‍♂️ \n\n請告訴我，你現在腦海中有什麼初步的畫面呢？"}
        ]
    
    ### 🚀 新增：初始化畫廊存儲 🚀 ###
    if "gallery" not in st.session_state:
        st.session_state.gallery = []
    ###############################

    for msg in st.session_state.messages:
        if msg["role"] != "system": 
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # ==========================================
    # 5. 互動邏輯
    # ==========================================
    if prompt := st.chat_input("請描述你的畫面..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if "確認出圖" in prompt:
            with st.chat_message("assistant"):
                st.markdown("收到！正在為你將腦海中的畫面轉化為現實... ✨")
                try:
                    chat_history_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages if m['role'] != 'system'])
                    negative_instruction = f"\n另外，請在 Prompt 的最後加上明確的英文指令，排除以下元素：{negative_prompt_input}。" if negative_prompt_input else ""
                    
                    prompt_refiner_req = client.models.generate_content(
                        model='gemini-2.5-pro',
                        contents=f"根據對話提取最完整的英文圖片生成 Prompt：\n{chat_history_text}{negative_instruction}"
                    )
                    final_image_prompt = prompt_refiner_req.text.strip()
                    
                    result = client.models.generate_images(
                        model='imagen-3.0-generate-002',
                        prompt=final_image_prompt,
                        config=types.GenerateImagesConfig(
                            number_of_images=1,
                            output_mime_type="image/jpeg",
                            aspect_ratio=final_aspect_ratio 
                        )
                    )
                    
        if result.generated_images:
                        img_data = result.generated_images[0].image.image_bytes
                        image = Image.open(io.BytesIO(img_data))
                        
                        # 🚀 存入畫廊，同時儲存 bytes 數據供下載使用 🚀
                        st.session_state.gallery.append({
                            "image": image, 
                            "image_bytes": img_data, # 這裡多存一份原始數據
                            "prompt": final_image_prompt
                        })

                        st.image(image, caption="具現化完成！", use_container_width=True)
                        
                        # 🚀 下載按鈕直接使用儲存好的 bytes 🚀
                        st.download_button(
                            label="⬇️ 下載這張作品",
                            data=img_data,
                            file_name=f"mind-canvas-{len(st.session_state.gallery)}.jpg",
                            mime="image/jpeg",
                            key=f"btn_{len(st.session_state.gallery)}" # 確保 key 唯一
                        )
                        
                except Exception as e:
                    st.error(f"出圖過程中發生錯誤：{e}")
        
        else:
            with st.chat_message("assistant"):
                formatted_contents = [{"role": "user" if m["role"] in ["user", "system"] else "model", "parts": [{"text": m["content"]}]} for m in st.session_state.messages]
                try:
                    response = client.models.generate_content(model='gemini-2.5-flash', contents=formatted_contents)
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"連線錯誤：{e}")
else:
    st.info("👋 歡迎！請先輸入 API Key 才能喚醒側寫師喔！")
