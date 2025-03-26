# ThreadsPoster - Threads 自動回覆與內容發布系統

## 系統說明
這個系統是一個透過角色設定後，使用 OpenAI 自動在 Threads 上發布內容的系統。系統會根據設定的角色特徵，自動生成符合人設的貼文。

## 主要功能
- 自動生成符合角色設定的貼文
- 根據時間自動調整發文內容和語氣
- 支援表情符號和自然語言表達
- 自動控制發文字數和格式

## 最新更新 (v1.0.0)
### 新功能
- 支援 25 字以內的完整句子生成
- 根據時間自動選擇適合的話題
- 智能調整文章語氣和表情符號使用
- 自動確保句子完整性和標點符號

### 改進
- 移除資料庫相關功能，專注於發文功能
- 優化文章生成邏輯，確保內容更自然
- 改進錯誤處理和日誌記錄
- 簡化設定檔結構

## 系統需求
- Python 3.8+
- OpenAI API 金鑰
- Threads API 存取權杖

## 安裝方式
1. 複製專案：
```bash
git clone https://github.com/chenweichiang/AI-Tools-ThreadsPoster.git
cd ThreadsPoster
```

2. 安裝相依套件：
```bash
pip install -r requirements.txt
```

3. 設定環境變數：
將 `.env.example` 複製為 `.env` 並填入必要的設定：
```bash
cp .env.example .env
```

必要的環境變數：
- THREADS_ACCESS_TOKEN
- THREADS_APP_ID
- THREADS_APP_SECRET
- OPENAI_API_KEY

## 使用方式
執行主程式：
```bash
python -m src.main
```

## 設定說明
系統設定檔位於 `src/config.py`，可以調整：
- 角色基本資料
- 發文規則
- API 設定
- 時區設定

## 授權條款
MIT License

## 作者
Chen Wei-Chiang 