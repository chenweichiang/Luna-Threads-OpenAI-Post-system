# Luna - ThreadsPoster

<div align="center">
  <img src="docs/logo.jpg" alt="Luna" width="150">
  <p>一個專為 Threads 平台設計的 AI 自動發文系統</p>
  <p>Version: 1.1.6 (2024.03.31)</p>
</div>

## 系統概述

Luna 是一個結合最新 AI 技術的 Threads 平台自動發文系統，能夠模擬真實用戶的發文行為，自動產生並發布高品質的內容。系統完全使用官方 Threads Graph API，符合平台規範，並具有定時發文、情感分析、人設記憶等功能。

### 主要特點

- **智能內容生成**：使用 GPT-4 進行自然、連貫的文章生成
- **官方 API 整合**：完全使用 Threads Graph API，確保穩定性和合規性
- **情感分析**：自動分析生成內容的情感傾向，確保風格一致
- **智能調度**：根據最佳發文時段自動安排發文計劃
- **人設記憶系統**：維持角色一致性，模擬真實人類發文行為
- **性能監控**：內置性能追蹤，優化系統資源使用
- **高效率資料處理**：使用快取與連接池提升資料庫效能

## 系統架構

Luna 採用模組化設計，各組件之間職責明確，便於擴展和維護：

1. **主控制器 (Main Controller)**：系統核心，協調各組件運作
2. **內容生成器 (Content Generator)**：負責生成高品質的發文內容
3. **Threads API 處理器**：負責與 Threads 平台進行通信
4. **資料庫處理器**：管理資料的存儲和讀取
5. **時間控制器**：管理發文時間，優化發文效果
6. **監控系統**：監控系統運行狀態，確保穩定性
7. **性能監控器**：追蹤系統性能指標，優化資源使用

## 最新更新 (v1.1.6)

### 中文
- 優化內容生成流程，改進文章的連貫性和完整性
- 加強角色人設特性，確保文章符合Luna的性格
- 改進表情符號的使用方式
- 修復文章在奇怪位置截斷的問題
- 改進日誌記錄，顯示完整的文章內容
- 整合性能監控系統，追蹤關鍵效能指標
- 優化資料庫操作，提高讀寫效率
- 實現內容快取機制，提高回應速度
- 改進並行處理能力，更有效利用系統資源

### English
- Optimized content generation process to improve article coherence and completeness
- Enhanced character persona features to ensure articles match Luna's personality
- Improved emoji usage for more natural expression
- Fixed issues with article truncation at odd positions
- Enhanced logging to display complete article content
- Integrated performance monitoring system to track key metrics
- Optimized database operations for better read/write efficiency
- Implemented content caching mechanism to improve response speed
- Enhanced parallel processing capabilities for better resource utilization

### 日本語
- コンテンツ生成プロセスを最適化し、記事の一貫性と完全性を向上
- キャラクターの特性を強化し、Lunaのパーソナリティに合った記事を作成
- 絵文字の使用方法を改善
- 記事が不自然な位置で切れる問題を修正
- ログ記録を改善し、完全な記事内容を表示
- パフォーマンスモニタリングシステムを統合し、主要な指標を追跡
- データベース操作を最適化し、読み書き効率を向上
- コンテンツキャッシュメカニズムを実装し、応答速度を向上
- 並列処理能力を強化し、システムリソースの利用効率を向上

## 系統特色

1. **效能優化**
   - 使用快取系統減少資料庫查詢
   - 非同步處理提升響應速度
   - 智能批次處理減少 API 調用
   - 人設記憶系統優化
   - 資源使用監控與動態調整
   - 連接池管理優化資料庫操作
   - 內容預生成機制提高回應效率

2. **內容生成**
   - 基於 GPT-4 的智能內容生成
   - 主題連續性追蹤
   - 情感分析確保內容合適性
   - 人設記憶整合

3. **資料管理**
   - MongoDB 資料庫儲存
   - 自動清理過期數據
   - 高效的資料索引
   - 人設記憶存取優化

4. **錯誤處理**
   - 完整的錯誤追蹤
   - 自動重試機制
   - 優雅的錯誤恢復
   - API 調用監控

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
python src/main.py
```

2. 監控日誌：
```bash
tail -f logs/threads_poster.log
```

3. 查看性能指標：
```bash
cat logs/metrics/metrics_$(date +"%Y%m%d").json
```

## 系統設定
系統的主要設定可在 `config.py` 中調整：

```python
SYSTEM_CONFIG = {
    "timezone": "Asia/Taipei",
    "post_interval": {
        "prime_time": {
            "min": 15 * 60,  # 主要時段最小間隔（15分鐘）
            "max": 45 * 60   # 主要時段最大間隔（45分鐘）
        },
        "other_time": {
            "min": 60 * 60,  # 其他時段最小間隔（1小時）
            "max": 180 * 60  # 其他時段最大間隔（3小時）
        }
    },
    "max_daily_posts": 10,     # 每日最大發文數
    "min_daily_posts": 5,      # 每日最少發文數
    "log_level": "INFO"
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
- 性能指標追蹤和記錄
- 內容預生成機制提高回應速度
- 資源使用監控與自動調整

## 錯誤處理
- 完整的錯誤日誌記錄
- 自動重試機制
- 優雅的系統關閉
- 資料庫連接自動恢復
- API 調用錯誤處理
- 人設記憶存取異常處理

## 注意事項
- 系統使用率過高時可能導致 API 使用量增加
- 建議監控 Token 使用量，避免超出 OpenAI 配額
- 發文頻率需符合 Threads 平台政策
- 確保使用官方 API，避免違反服務條款
- 定期檢查系統日誌，及時發現異常情況
- 建議定期備份資料庫，防止資料遺失

## License
本專案採用 MIT 授權條款 - 詳情請查看 LICENSE 文件