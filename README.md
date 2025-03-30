<div align="center">
  <img src="luna.png" alt="Luna" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
  <h1>ThreadsPoster - Threads 自動回覆與內容發布系統</h1>
  <p>🌟 由 Luna 提供智能社群互動體驗 🌟</p>
  
  [![Version](https://img.shields.io/badge/version-1.1.9-blue.svg)](https://github.com/chenweichiang/Luna-Threads-OpenAI-Post-system)
  [![Last Updated](https://img.shields.io/badge/last%20updated-2025.03.31-green.svg)](https://github.com/chenweichiang/Luna-Threads-OpenAI-Post-system)
  [![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/chenweichiang/Luna-Threads-OpenAI-Post-system/blob/main/LICENSE)
  [![Author](https://img.shields.io/badge/author-Chiang%2C%20Chenwei-orange.svg)](https://github.com/chenweichiang)
</div>

[繁體中文](#繁體中文) | [English](#english) | [日本語](#日本語)

---

# 介紹

這是一個由生成式工具所生成的AI系統，作者想要在2025年AI元年用創作的手法打造的一虛擬少女Luna，在虛擬的世界中擁有人類思考模式的少女，喜努哀樂生活面貌都會隨著時間在Threads社群網路上逐漸被人們發現，透過Threads與Luna對話會影響Luna在虛擬世界中的生活，快來跟Luna對話吧！

This is an AI system generated by generative tools. The author aims to create a virtual girl named Luna in the AI era of 2025 using creative methods. Luna, a girl with human-like thinking patterns in the virtual world, will gradually reveal her joys, efforts, sorrows, and daily life on the Threads social network. Through conversations with Luna on Threads, you can influence her life in the virtual world. Come and chat with Luna!

これは生成型ツールによって生成されたAIシステムです。作者は2025年のAI元年に、創作的なアプローチで仮想少女Lunaを作り出すことを目指しています。仮想世界で人間のような思考パターンを持つ少女Lunaの喜怒哀楽や生活の様子は、Threadsソーシャルネットワーク上で徐々に人々に発見されていきます。ThreadsでLunaと対話することで、仮想世界での彼女の生活に影響を与えることができます。さあ、Lunaと話してみましょう！

# 繁體中文

關於Luna
這是一個由生成式工具所生成的AI系統，作者想要在2025年AI元年用創作的手法打造的一虛擬少女Luna，在虛擬的世界中擁有人類思考模式的少女，喜努哀樂生活面貌都會隨著時間在Threads社群網路上逐漸被人們發現，透過Threads與Luna對話會影響Luna在虛擬世界中的生活，快來跟Luna對話吧！

## 系統概述
ThreadsPoster 是一個基於 Python 的自動化系統，用於在 Threads 平台上進行智能內容發布和互動。系統使用 OpenAI 的 GPT 模型生成內容，並透過角色設定實現真實的人物互動體驗。

## 主要功能
- 自動生成並發布貼文
- 智能回覆其他用戶的互動
- 記憶系統追蹤互動歷史
- 主題連續性管理
- 情感分析與回應調整
- 動態發文時間管理
- 人設記憶系統
- 性能監控與分析
- 資源使用優化

## 功能清單

### ✅ 已完成功能
- 基礎系統架構建立
- OpenAI GPT-4 整合與內容生成
- MongoDB 最新版本資料庫整合
- 自動發文系統與時間管理
- 情感分析與回應系統
- 記憶系統與主題連續性追蹤
- 自動添加表情符號（優化數量）
- 多語言支援（中、英、日）
- 完整的錯誤處理與重試機制
- 系統日誌記錄與監控
- 人設記憶系統
- 內容生成質量評估系統
- 自動化測試套件
- 備份與還原機制
- GitHub Actions 自動化部署
- 程式碼品質檢查
- 安全性掃描
- 測試覆蓋率報告
- 自動化監控與通知
- 性能監控與分析
- 資源使用優化
- API請求統計與分析

### 📝 待完成功能
- 用戶互動分析報表
- AI 圖片生成與發布
- 即時系統狀態監控
- 管理員控制面板
- 自動更新系統
- 社群互動分析工具
- 內容推薦引擎
- 自適應學習系統

## 系統架構
### 核心模組架構
```
src/
├── main.py          # 主程式入口點，負責啟動和協調所有系統組件
├── config.py        # 設定檔管理，負責讀取和驗證系統配置
├── database.py      # 資料庫抽象層，提供統一的資料庫操作介面
├── db_handler.py    # 資料庫處理器，處理複雜的資料庫操作和查詢
├── threads_api.py   # Threads API 介面，處理與Threads平台的通信
├── openai_api.py    # OpenAI API 介面，處理與OpenAI服務的通信
├── ai_handler.py    # AI 內容生成器，負責管理和優化AI生成內容
├── threads_handler.py # Threads 處理器，協調發文和回覆操作
├── time_controller.py # 時間控制器，管理發文時間和頻率
├── monitor.py       # 監控系統，協調整體系統運行和任務分配
├── performance_monitor.py # 性能監控模組，追蹤系統性能和資源使用
├── content_generator.py # 內容生成器，專門處理不同場景的內容生成
├── utils.py         # 工具函數集，提供各種通用功能
├── logger.py        # 日誌處理器，統一管理系統日誌
├── retry.py         # 重試機制，提供網絡請求和操作的自動重試
├── exceptions.py    # 異常處理類，定義系統專用的異常類型
```

### 輔助工具
```
src/
├── tools/           # 系統工具腳本目錄
│   ├── __init__.py  # 工具包初始化
│   ├── tools.py     # 統一命令行工具入口
│   └── test_time_settings.py # 測試時間設定工具
├── auth_threads.py  # Threads 認證工具
├── get_access_token.py # 存取權杖獲取工具
├── oauth_server.py  # OAuth 伺服器實現
├── reset_memory.py  # 記憶重置工具
├── check_memory.py  # 記憶檢查工具
├── check_env.py     # 環境變數檢查工具
└── init_db.py       # 資料庫初始化工具
```

### CI/CD與部署
```
.github/
└── workflows/       # GitHub Actions 工作流程目錄
    └── main.yml     # 自動化部署和測試工作流程

# 其他關鍵檔案
.env.example         # 環境變數範例檔案
requirements.txt     # 依賴套件清單
LICENSE              # 授權文件
README.md            # 專案說明文件
```

### 數據流與組件關係
1. **啟動流程**
   ```
   main.py → config.py → database.py → db_handler.py
          → time_controller.py → ai_handler.py → threads_api.py
          → threads_handler.py → monitor.py
   ```

2. **發文流程**
   ```
   monitor.py → time_controller.py → content_generator.py → ai_handler.py
              → threads_handler.py → threads_api.py → database.py
   ```

3. **性能監控流程**
   ```
   performance_monitor.py → 各模組操作 → 指標收集 → 分析與報告
   ```

4. **數據存儲層**
   ```
   MongoDB → database.py → db_handler.py → 各功能模組
   ```

5. **API層**
   ```
   OpenAI API → openai_api.py → ai_handler.py → content_generator.py
   Threads API → threads_api.py → threads_handler.py → monitor.py
   ```

### 主要特點與模組職責

1. **主流程協調**
   - `main.py`: 系統入口點，負責初始化所有組件並管理事件循環
   - `monitor.py`: 核心監控組件，協調發文時機和系統狀態

2. **AI與內容生成**
   - `ai_handler.py`: 管理AI模型與優化提示詞，確保內容品質
   - `content_generator.py`: 根據不同場景和主題生成適合的內容

3. **社群互動管理**
   - `threads_handler.py`: 處理發文邏輯和互動策略
   - `threads_api.py`: 封裝Threads平台API，處理請求和響應

4. **數據管理**
   - `database.py`: 資料庫抽象層，提供通用操作接口
   - `db_handler.py`: 管理複雜數據操作，如查詢、統計和分析

5. **性能與監控**
   - `performance_monitor.py`: 追蹤系統性能指標和資源使用
   - `logger.py`: 統一日誌系統，記錄操作和錯誤

6. **時間和任務管理**
   - `time_controller.py`: 智能管理發文時間和頻率

7. **工具與支援**
   - `retry.py`: 提供自動重試機制，增強系統穩定性
   - `utils.py`: 提供通用工具函數
   - `exceptions.py`: 定義系統專用異常處理

## 技術特點
1. **效能優化**
   - 使用快取系統減少資料庫查詢
   - 非同步處理提升響應速度
   - 智能批次處理減少 API 調用
   - 人設記憶系統優化
   - 連接池優化
   - 自動記憶體使用監控
   - API 請求效能追蹤

2. **內容生成**
   - 基於 GPT-4 的智能內容生成
   - 主題連續性追蹤
   - 情感分析確保內容合適性
   - 人設記憶整合
   - 內容快取機制
   - 預先生成內容提高回應速度

3. **資料管理**
   - MongoDB 資料庫儲存
   - 自動清理過期數據
   - 高效的資料索引
   - 人設記憶存取優化
   - 快取命中率優化
   - 資料庫連接池管理

4. **錯誤處理**
   - 完整的錯誤追蹤
   - 自動重試機制
   - 優雅的錯誤恢復
   - API 調用監控
   - 資源使用監控
   - 性能瓶頸檢測

5. **性能監控**
   - 操作時間追蹤
   - API 請求統計
   - 資料庫操作統計
   - 記憶體使用監控
   - 快取命中率分析
   - 性能報告生成

## 部署需求
- Python 3.10+ (建議使用 3.13)
- MongoDB 最新版本
- OpenAI API 金鑰
- Threads API 存取權限
- SSL 憑證（用於 OAuth）
- 穩定的網路連接
- 足夠的運算資源
- 監控工具整合

## CI/CD 流程
系統使用 GitHub Actions 進行自動化部署和測試：

1. **測試階段**
   - 多版本 Python 相容性測試 (3.10-3.13)
   - 程式碼格式檢查 (black, flake8, isort)
   - 型別檢查 (mypy)
   - 安全性掃描 (bandit, safety)
   - 測試覆蓋率報告
   - 自動化測試結果上傳

2. **部署階段**
   - 自動部署到生產環境
   - 環境變數配置
   - 資料庫連接測試
   - 系統運行狀態監控

3. **監控階段**
   - 即時錯誤通知
   - 系統狀態監控
   - 自動重啟機制
   - 效能監控

## 環境設定
1. 安裝依賴套件：
```bash
pip install -r requirements.txt
```

2. 設定環境變數：
```bash
cp .env.example .env
# 編輯 .env 文件填入必要的 API 金鑰和設定
```

3. 初始化資料庫：
```bash
python init_db.py
```

## 使用方法
1. 啟動系統：
```bash
python main.py
```

2. 監控日誌：
```bash
tail -f threads_poster.log
```

3. 查看性能指標：
```bash
python view_metrics.py
```

4. 使用系統工具：
```bash
# 顯示所有可用工具
python -m src.tools.tools

# 檢查最近的文章
python -m src.tools.tools --check-posts

# 測試時間設定
python -m src.tools.tools --test-time

# 執行所有工具
python -m src.tools.tools --all
```

## 系統設定
系統的主要設定可在 `config.py` 中調整：

```python
SYSTEM_CONFIG = {
    "timezone": "Asia/Taipei",
    "post_interval": 3600,     # 發文間隔（秒）
    "reply_interval": 300,     # 回覆間隔（秒）
    "max_daily_posts": 40,     # 每日最大發文數
    "max_daily_replies": 50,   # 每日最大回覆數
    "memory_enabled": True,    # 人設記憶系統開關
    "performance_monitoring": True, # 性能監控開關
    "cache_ttl": 300,          # 快取過期時間（秒）
    "connection_pool_size": 50 # 資料庫連接池大小
}
```

## 角色設定
```json
{
  "基本資料": {
    "年齡": 20,
    "性別": "女性",
    "國籍": "台灣",
    "興趣": ["遊戲", "動漫", "收藏公仔"],
    "個性特徵": [
      "善良溫柔",
      "容易感到寂寞",
      "喜歡交朋友"
    ]
  }
}
```

## 效能優化
- 使用記憶體快取減少資料庫查詢
- 實作連接池管理資料庫連接
- 非同步處理提升系統響應
- 智能批次處理減少 API 調用
- 自動清理過期數據節省資源
- 人設記憶系統優化
- 資料庫索引最佳化
- API 請求限流控制
- 連接池大小動態調整
- 記憶體使用監控與優化
- 操作計時與性能分析
- 內容預先生成機制
- API 請求效能追蹤

## 性能監控
- 操作時間追蹤分析
- API 請求數量與耗時統計
- 資料庫操作統計與分析
- 記憶體使用監控
- 快取命中率追蹤
- 系統瓶頸識別
- 性能指標保存與趨勢分析
- 操作耗時異常檢測
- 資源使用報告生成

## 錯誤處理
- 完整的錯誤日誌記錄
- 自動重試機制
- 優雅的系統關閉
- 資料庫連接自動恢復
- API 調用錯誤處理
- 人設記憶存取異常處理
- 系統狀態自動回復
- 異常監控與通知
- 資源使用異常處理
- 性能異常報警

## 安全性
- API 金鑰安全管理
- 資料庫存取控制
- HTTPS 安全連接
- 資料加密存儲
- 定期安全性掃描
- 存取權限管理
- 資料備份機制
- 系統監控告警
- 性能指標安全存儲
- 敏感資訊保護

## 注意事項
1. API 限制
   - 請注意 OpenAI API 的使用限制
   - 遵守 Threads API 的使用規範
   - 控制發文頻率避免被限制
   - 監控 API 使用量與費用

2. 資料安全
   - 定期備份資料庫
   - 保護 API 金鑰
   - 注意用戶隱私
   - 人設記憶加密存儲
   - 性能指標安全保存

3. 系統維護
   - 定期檢查日誌
   - 監控系統資源使用
   - 更新依賴套件
   - 維護人設記憶資料庫
   - 性能指標趨勢分析

## 開發者
`Chiang, Chenwei`

## 授權
本專案採用 MIT 授權協議，詳情請參閱 [LICENSE](LICENSE) 文件。

MIT 授權允許您自由使用、修改和分發本專案，無論是商業還是非商業用途，但需保留原始授權和版權聲明。

### 更新日誌
#### v1.1.8 (2025.03.30)
- 全面更新系統架構文檔，增加更詳細的模組說明
- 新增數據流與組件關係圖解說明
- 細化各模組職責描述
- 優化檔案結構說明
- 重組輔助工具分類
- 增加CI/CD與部署架構說明
- 補充模組間的互動關係說明
- 完善主要特點與模組職責描述
- 優化GitHub Actions工作流程
- 增加檢查環境與初始化資料庫腳本

#### v1.1.7 (2024.03.31)
- 整合系統工具腳本到統一目錄
- 創建統一命令行工具入口
- 改進時間設定測試工具
- 將檢查文章功能移至核心代碼中
- 優化文章檢視功能到db_handler和utils
- 修復.env文件解析問題
- 改進配置文件讀取機制
- 優化性能監控模組
- 修復performance_monitor關閉時的錯誤
- 調整README.md格式和內容
- 系統架構文檔更新

#### v1.1.6 (2024.03.31)
- 優化內容生成流程，改進文章的連貫性和完整性
- 加強角色人設特性，確保文章符合Luna的性格
- 改進表情符號的使用方式，使其更自然
- 修復Threads API整合問題，採用正確的兩步驟發文流程
- 優化文章後處理機制，確保互動性和可讀性
- 改進資料庫存儲流程
- 更新所有檔案版本資訊，統一版本號
- 修正發文在奇怪位置截斷的問題
- 加強錯誤處理與日誌記錄
- 新增性能監控模組，追蹤系統性能和資源使用
- 優化記憶體使用和資料庫連接池設定
- 實現內容快取機制提高回應速度
- 加入操作時間追蹤功能
- 整合 API 請求統計和監控
- 新增資料庫操作統計功能

#### v1.1.5 (2024.03.30)
- 優化檔案結構，移除冗餘檔案
- 整合重複功能模組
- 更新系統架構說明
- 改進錯誤處理機制
- 優化記憶系統存取
- 加強系統穩定性
- 優化日誌記錄路徑
- 改進設定檔驗證
- 加強資料庫操作效能
- 改進資料備份機制

## 在 GitHub 上運行系統

本系統支援透過 GitHub Actions 自動運行，按照以下步驟設定：

1. **Fork 本專案**
   - 在 GitHub 上 Fork 此專案到您的帳戶

2. **設定 Repository Secrets**
   在專案設定中添加以下 Secrets：
   - `OPENAI_API_KEY`: 您的 OpenAI API 金鑰
   - `THREADS_APP_ID`: Threads 應用程式 ID
   - `THREADS_APP_SECRET`: Threads 應用程式密鑰
   - `THREADS_ACCESS_TOKEN`: Threads API 存取令牌
   - `THREADS_USER_ID`: Threads 用戶 ID
   - `MONGODB_URI`: MongoDB 連接字串（可使用 MongoDB Atlas 免費版）

3. **啟用 GitHub Actions**
   - 進入 Actions 標籤頁
   - 選擇並啟用 `ThreadsPoster 自動化工作流程`
   - 點擊 "Run workflow" 按鈕手動觸發首次運行

4. **檢視運行結果**
   - 在 Actions 頁面查看運行結果
   - 檢查上傳的日誌文件了解詳細運行情況

5. **自定義發文排程**
   - 編輯 `.github/workflows/main.yml` 檔案
   - 調整 `cron` 表達式來設定自訂發文頻率

### Docker 設定（本地運行）

您也可以使用 Docker 在本地運行系統：

1. **安裝 Docker**
   - 從 [Docker 官網](https://www.docker.com/) 下載並安裝

2. **創建環境變數檔案**
   ```bash
   cp .env.example .env
   # 編輯 .env 檔案填入所需的 API 金鑰和設定
   ```

3. **使用 Docker Compose 啟動系統**
   ```bash
   docker-compose up -d
   ```

4. **檢視日誌**
   ```bash
   docker-compose logs -f
   ```

5. **關閉系統**
   ```bash
   docker-compose down
   ```

### 故障排除

1. **GitHub Actions 失敗**
   - 檢查 Secrets 是否正確設定
   - 查看詳細錯誤日誌找出問題原因
   - 確認 MongoDB URI 是否允許從 GitHub Actions IP 存取

2. **MongoDB 連接問題**
   - 使用 MongoDB Atlas 時，確保網路存取控制已允許所有 IP 地址
   - 檢查連接字串格式是否正確
   - 測試 MongoDB 帳戶憑證是否有效

3. **OpenAI API 錯誤**
   - 檢查 API 金鑰是否有效
   - 確認 API 使用額度是否充足
   - 查看 OpenAI 服務狀態
