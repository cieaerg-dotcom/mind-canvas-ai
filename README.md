# 🎨 Mind Canvas AI (腦內場景側寫師)

這是一個基於 Google Gemini 模型的 AI 互動繪圖工具。專為「腦海中有畫面，但不知如何精準描述（Prompt）」的使用者設計。系統會化身為場景側寫師，透過一來一往的對話，引導使用者補齊視覺結構、感官情緒與藝術風格，最終轉化為精準的英文提示詞並生成高畫質圖片。

## ✨ 核心功能 (Features)

* **引導式對話生成**：結合「感官轉譯」與「結構引導」，透過對話一步步完善畫面細節。
* **雙模型協作架構 (Hybrid AI)**：
  * 使用 `gemini-2.5-flash` 進行快速、低延遲的日常對話引導。
  * 確認出圖時，切換至強大的 `gemini-2.5-pro` 進行最終 Prompt 的高階提煉。
* **智慧防護網 (Negative Prompt)**：透過系統底層指令，自動排除使用者不想看到的元素（如：浮水印、文字、變形等）。
* **動態畫布尺寸轉換**：將晦澀的比例數字（16:9, 9:16）轉化為直覺的「手機/平板/電腦 x 直式/橫式」選項。
* **節省算力機制**：只有在使用者明確輸入「確認出圖」後，才會呼叫昂貴的生圖 API。

## 🛠️ 技術堆疊 (Tech Stack)

* **前端介面**：[Streamlit](https://streamlit.io/)
* **核心邏輯**：Python 3
* **AI 模型 SDK**：`google-genai` (Google 最新版 SDK)
* **語言模型 (LLM)**：Gemini 2.5 Flash / Gemini 2.5 Pro
* **生圖模型 (Text-to-Image)**：Imagen 3 (`imagen-3.0-generate-002`)

## 🚀 快速開始 (Quick Start)

### 1. 安裝依賴套件
請確保你的環境已安裝 Python 3.9+，然後執行以下指令安裝所需套件：
```bash
pip install streamlit google-genai pillow