import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io

# ==========================================
# 1. 網頁基本設定 & 側邊欄防護網
# ==========================================
st.set_page_config(page_title="腦內場景側寫師", page_icon="🎨", layout="centered")

### 🚀 新增：側邊欄防護網設定 (UI 介面) 🚀 ###
with st.sidebar:
    st.header("🛡️ 畫面防護網 (Negative Prompt)")
    st.markdown("請告訴我你**不想**在畫面中看到的元素。")
    negative_prompt_input = st.text_input("不想出現的元素：", placeholder="例如：文字, 浮水印, 變形的手, 模糊")
    st.info("💡 工程師科普：最新的 Imagen 3 模型已取消獨立的負面參數，系統會自動在底層將您的需求轉化為強力的排除指令，完美保護您的畫面！")
#############################################

st.title("🎨 腦內場景側寫師")
st.markdown("告訴我你腦海中的一個初步畫面，我會引導你完善細節，最後為你畫出來！")

# ==========================================
# 2. API Key 設定
# ==========================================
api_key = st.text_input("請輸入你的 Gemini API Key:", type="password")

if api_key:
    client = genai.Client(api_key=api_key)
    
    # ==========================================
    # 3. 初始化 Session State (對話記憶與系統人設)
    # ==========================================
    if "messages" not in st.session_state:
        ### 🚀 修改：在系統提示詞中加入「畫風引導」的第 3 點指令 🚀 ###
        system_instruction = """
        你是一位「腦內場景側寫師」。使用者的目標是生成一張圖片，但他們一開始只能給出模糊的大框架。
        你的任務是透過溫和的對話，一步步引導使用者豐富畫面細節。
        請結合以下三個維度進行提問（每次只問1~2個問題，不要給使用者壓力）：
        1. 視覺結構（前中後景填空）：主體是什麼？背景在哪裡？
        2. 感官與情緒（感官轉譯）：光線是明亮還是昏暗？環境給人的感覺是溫暖、冷冽還是神秘？
        3. 藝術風格（畫風引導）：畫面應該呈現什麼樣的風格？（例如：水彩、賽博龐克、吉卜力、寫實攝影、油畫等）。
        
        當你覺得細節已經足夠豐富，請總結一段「最終畫面描述」，並詢問使用者：
        「這是你想像中的畫面嗎？如果確認無誤，請回覆『確認出圖』，我就會幫你把這幅畫變為現實！」
        """
        ##############################################################
        st.session_state.messages = [
            {"role": "system", "content": system_instruction},
            {"role": "assistant", "content": "你好！我是你的腦內場景側寫師 🧙‍♂️ \n\n請告訴我，你現在腦海中有什麼初步的畫面或大框架呢？（例如：一座在天空中的城市、一個神祕的賽博龐克巷弄）"}
        ]

    # ==========================================
    # 4. 渲染歷史對話記錄
    # ==========================================
    for msg in st.session_state.messages:
        if msg["role"] != "system": 
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # ==========================================
    # 5. 處理使用者輸入與互動邏輯
    # ==========================================
    if prompt := st.chat_input("請描述你的畫面，或回答側寫師的問題..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if "確認出圖" in prompt:
            with st.chat_message("assistant"):
                st.markdown("收到！正在為你將腦海中的畫面轉化為現實，請稍候... ✨")
                try:
                    chat_history_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages if m['role'] != 'system'])
                    
                    ### 🚀 新增：將側邊欄的防護網動態注入最終 Prompt 提煉任務中 🚀 ###
                    # 如果使用者有填寫防護網，就生成一段強制的排除指令
                    negative_instruction = f"\n另外，請在 Prompt 的最後加上明確的英文指令，確保畫面中絕對不要出現以下元素：{negative_prompt_input}。" if negative_prompt_input else ""
                    
                    prompt_refiner_req = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=f"根據以下對話歷史，提取出最完整的英文圖片生成 Prompt (只需回傳純英文Prompt，不要其他任何說明文字)。{negative_instruction}\n對話歷史：\n{chat_history_text}"
                    )
                    ###################################################################
                    
                    final_image_prompt = prompt_refiner_req.text.strip()
                    
                    result = client.models.generate_images(
                        model='imagen-3.0-generate-002',
                        prompt=final_image_prompt,
                        config=types.GenerateImagesConfig(
                            number_of_images=1,
                            output_mime_type="image/jpeg",
                            aspect_ratio="16:9" 
                        )
                    )
                    
                    if result.generated_images:
                        image_bytes = result.generated_images[0].image.image_bytes
                        image = Image.open(io.BytesIO(image_bytes))
                        st.image(image, caption="你的腦內場景已經具現化！", use_column_width=True)
                        st.success(f"🎨 使用的魔法咒語 (Prompt): \n{final_imXage_prompt}")
                        
                except Exception as e:
                    st.error(f"出圖過程中發生錯誤：{e}\n\n*工程師小提醒：請確認您的 API Key 是否具有 Imagen 模型的存取權限喔！*")
        
else:
            with st.chat_message("assistant"):
                formatted_contents = []
                for m in st.session_state.messages:
                    role = "user" if m["role"] in ["user", "system"] else "model"
                    formatted_contents.append({"role": role, "parts": [{"text": m["content"]}]})
                
                try:
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=formatted_contents
                    )
                    msg_text = response.text
                    st.markdown(msg_text)
                    st.session_state.messages.append({"role": "assistant", "content": msg_text})
                except Exception as e:
                    st.error(f"連線發生錯誤：{e}")
else:
    st.info("👋 歡迎！請先在上方輸入您的 Gemini API Key 才能喚醒側寫師喔！")
