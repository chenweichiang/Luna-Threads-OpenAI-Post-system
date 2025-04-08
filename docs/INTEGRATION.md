# ThreadsPoster 系統整合指南

本文檔說明 ThreadsPoster 系統的各種整合功能，包括 AI 模型、API 和第三方服務的整合方法。

## AI 模型整合

### 1. Quasar Alpha 模型
- **當前狀態**：已完全整合（v1.2.4）
- **主要用途**：生成高質量的文章內容
- **整合方式**：
  ```python
  # 在 config.py 中設置
  QUASAR_CONFIG = {
      "model": "quasar-alpha",
      "temperature": 0.7,
      "max_tokens": 1000
  }
  ```
- **使用限制**：
  - 需要有效的 API 金鑰
  - 建議每分鐘不超過 10 次請求
  - 回文功能暫時關閉（2025-04-06）

### 2. OpenAI GPT-4
- **當前狀態**：已整合但已切換到 Quasar Alpha
- **備用功能**：作為備用內容生成引擎
- **整合設定**：
  ```python
  # 在 .env 中設置
  OPENAI_API_KEY=your_api_key
  OPENAI_MODEL=gpt-4
  ```

## API 整合

### 1. Threads API
- **用途**：發布內容和互動管理
- **設定方法**：
  ```python
  # 在 .env 中設置
  THREADS_APP_ID=your_app_id
  THREADS_APP_SECRET=your_app_secret
  THREADS_ACCESS_TOKEN=your_access_token
  THREADS_USER_ID=your_user_id
  ```

### 2. MongoDB
- **用途**：資料儲存和管理
- **連接設定**：
  ```python
  # 在 .env 中設置
  MONGODB_URI=mongodb://username:password@host:port/database
  ```
- **集合結構**：
  - articles：文章內容
  - posts：發文記錄
  - personality_memories：人設記憶
  - speaking_patterns：說話模式
  - user_history：用戶互動歷史

## 系統整合

### 1. 時間控制整合
```python
TIME_CONTROL_CONFIG = {
    "posting_hours": {
        "start": 20,  # 晚上 8 點
        "end": 2      # 凌晨 2 點
    },
    "posts_per_day": {
        "min": 3,
        "max": 5
    },
    "prime_time": {
        "start": 21,  # 晚上 9 點
        "end": 1      # 凌晨 1 點
    }
}
```

### 2. 監控系統整合
```python
MONITORING_CONFIG = {
    "performance_monitoring": True,
    "api_monitoring": True,
    "resource_monitoring": True,
    "log_level": "INFO",
    "metrics_interval": 300  # 5 分鐘
}
```

## GitHub Actions 整合

### 1. 自動部署配置
```yaml
name: Deploy ThreadsPoster

on:
  push:
    branches: [ main ]
  schedule:
    - cron: '0 12-18 * * *'  # UTC 12-18 (台灣時間 20-02)

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run ThreadsPoster
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          THREADS_APP_ID: ${{ secrets.THREADS_APP_ID }}
          THREADS_APP_SECRET: ${{ secrets.THREADS_APP_SECRET }}
          THREADS_ACCESS_TOKEN: ${{ secrets.THREADS_ACCESS_TOKEN }}
          THREADS_USER_ID: ${{ secrets.THREADS_USER_ID }}
          MONGODB_URI: ${{ secrets.MONGODB_URI }}
        run: python main.py
```

## Docker 整合

### 1. Dockerfile
```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]
```

### 2. Docker Compose
```yaml
version: '3.8'
services:
  threadsposter:
    build: .
    env_file: .env
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    restart: unless-stopped
```

## 整合檢查清單

### 初次部署檢查
1. [ ] 確認所有環境變數已正確設置
2. [ ] 測試資料庫連接
3. [ ] 驗證 API 金鑰
4. [ ] 檢查時區設定
5. [ ] 確認日誌目錄權限

### 定期維護檢查
1. [ ] 監控 API 使用量
2. [ ] 檢查資料庫容量
3. [ ] 審查系統日誌
4. [ ] 更新依賴套件
5. [ ] 備份重要數據

## 故障排除

### 1. API 連接問題
- 檢查 API 金鑰是否有效
- 確認網路連接狀態
- 查看 API 使用限制

### 2. 資料庫問題
- 確認 MongoDB 連接字串
- 檢查資料庫權限
- 驗證索引狀態

### 3. 內容生成問題
- 檢查模型設定
- 確認提示詞格式
- 驗證內容長度限制

## 安全性考慮

### 1. API 金鑰管理
- 使用環境變數存儲
- 定期更換金鑰
- 限制存取權限

### 2. 資料安全
- 加密敏感資料
- 定期備份
- 存取日誌記錄

### 3. 系統安全
- 更新依賴套件
- 限制網路存取
- 監控異常活動 