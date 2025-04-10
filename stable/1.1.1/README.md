![Luna](luna.png)

# ThreadsPoster - Threads 自動回覆與內容發布系統

這是一個由生成式工具所生成的AI系統，作者想要在2025年AI元年用創作的手法打造的一虛擬少女Luna，在虛擬的世界中擁有人類思考模式的少女，喜努哀樂生活面貌都會隨著時間在Threads社群網路上逐漸被人們發現，透過Threads與Luna對話會影響Luna在虛擬世界中的生活，快來跟Luna對話吧！

This is an AI system generated by generative tools. The author aims to create a virtual girl named Luna in the AI era of 2025 using creative methods. Luna, a girl with human-like thinking patterns in the virtual world, will gradually reveal her joys, efforts, sorrows, and daily life on the Threads social network. Through conversations with Luna on Threads, you can influence her life in the virtual world. Come and chat with Luna!

これは生成型ツールによって生成されたAIシステムです。作者は2025年のAI元年に、創作的なアプローチで仮想少女Lunaを作り出すことを目指しています。仮想世界で人間のような思考パターンを持つ少女Lunaの喜怒哀楽や生活の様子は、Threadsソーシャルネットワーク上で徐々に人々に発見されていきます。ThreadsでLunaと対話することで、仮想世界での彼女の生活に影響を与えることができます。さあ、Lunaと話してみましょう！

[![Version](https://img.shields.io/badge/version-1.1.1-blue.svg)](https://github.com/chenweichiang/AI-Tools-ThreadsPoster)
[![Last Updated](https://img.shields.io/badge/last%20updated-2025.03.29-green.svg)](https://github.com/chenweichiang/AI-Tools-ThreadsPoster)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](https://github.com/chenweichiang/AI-Tools-ThreadsPoster/blob/main/LICENSE)
[![Author](https://img.shields.io/badge/author-Chiang%2C%20Chenwei-orange.svg)](https://github.com/chenweichiang)

[繁體中文](#繁體中文) | [English](#english) | [日本語](#日本語)

---

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

## 功能清單

### ✅ 已完成功能
- 基礎系統架構建立
- OpenAI 整合與內容生成
- MongoDB 資料庫整合
- 自動發文系統
- 動態時間管理
- 情感分析系統
- 記憶系統
- 主題連續性追蹤
- 自動添加表情符號
- 多語言支援（中、英、日）
- 錯誤處理與重試機制
- 系統日誌記錄
- GitHub Actions 自動部署

### 📝 待完成功能
- 用戶互動分析報表
- 內容生成質量評估系統
- 自動化測試套件
- 多角色支援
- 圖片生成與發布
- API 使用量監控儀表板
- 即時系統狀態監控
- 備份與還原機制
- 管理員控制面板
- 自動更新系統

## 系統架構
```
src/
├── main.py          # 主程式入口
├── config.py        # 設定檔
├── database.py      # 資料庫處理
├── threads_api.py   # Threads API 介面
├── ai_handler.py    # AI 內容生成
└── exceptions.py    # 異常處理
```

## 技術特點
1. **效能優化**
   - 使用快取系統減少資料庫查詢
   - 非同步處理提升響應速度
   - 智能批次處理減少 API 調用

2. **內容生成**
   - 基於 GPT-4 的智能內容生成
   - 主題連續性追蹤
   - 情感分析確保內容合適性

3. **資料管理**
   - MongoDB 資料庫儲存
   - 自動清理過期數據
   - 高效的資料索引

4. **錯誤處理**
   - 完整的錯誤追蹤
   - 自動重試機制
   - 優雅的錯誤恢復

## 安裝需求
- Python 3.8+
- MongoDB 4.4+
- OpenAI API 金鑰
- Threads API 存取權限

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
python -m src.database_init
```

## 使用方法
1. 啟動系統：
```bash
python -m src.main
```

2. 監控日誌：
```bash
tail -f threads_poster.log
```

## 系統設定
系統的主要設定可在 `config.py` 中調整：

```python
SYSTEM_CONFIG = {
    "timezone": "Asia/Taipei",
    "post_interval": 3600,     # 發文間隔（秒）
    "reply_interval": 300,     # 回覆間隔（秒）
    "max_daily_posts": 10,     # 每日最大發文數
    "max_daily_replies": 50    # 每日最大回覆數
}
```

## 角色設定
```json
{
  "基本資料": {
    "年齡": 28,
    "性別": "女性",
    "國籍": "台灣",
    "興趣": ["ACG文化", "電腦科技", "BL作品"],
    "個性特徵": [
      "喜歡說曖昧的話",
      "了解科技",
      "善於互動"
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

## 錯誤處理
- 完整的錯誤日誌記錄
- 自動重試機制
- 優雅的系統關閉
- 資料庫連接自動恢復
- API 調用錯誤處理

## 注意事項
1. API 限制
   - 請注意 OpenAI API 的使用限制
   - 遵守 Threads API 的使用規範
   - 控制發文頻率避免被限制

2. 資料安全
   - 定期備份資料庫
   - 保護 API 金鑰
   - 注意用戶隱私

3. 系統維護
   - 定期檢查日誌
   - 監控系統資源使用
   - 更新依賴套件

## 開發者
`Chiang, Chenwei`

## 授權
本專案採用 MIT 授權條款。詳見 [LICENSE](LICENSE) 文件。

---

# English

## Threads Auto Reply and Content Publishing System

Version: 1.1.0
Last Updated: 2025-03-29

### System Overview
This is an OpenAI-based Threads auto-reply and content publishing system. The system automatically generates and publishes content based on configured character personalities, simulating real user interactions. The system runs in a cloud environment and uses GitHub Actions for automated deployment and operation.

### Main Features
- Auto-generate character-based posts
- Smart analysis and reply to user interactions
- Auto-adjust posting frequency and style based on time
- Memory system for interaction history tracking
- Support multiple topics: ACG, Tech, BL, etc.
- Auto-add appropriate emojis

### Technical Features
- Content generation using OpenAI GPT-3.5
- Python async programming
- MongoDB for interaction records
- GitHub Actions automation
- Complete error handling and retry mechanism
- Smart text sanitization and formatting

### System Requirements
- Python 3.9+
- OpenAI API key
- MongoDB database
- Threads API access

### Installation
1. Clone the repository:
```bash
git clone https://github.com/chenweichiang/AI-Tools-ThreadsPoster.git
cd ThreadsPoster
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env file with your API keys and settings
```

### Usage
1. Start the system:
```bash
python src/main.py
```

2. Monitor logs:
```bash
tail -f logs/threadsposter.log
```

### Configuration
System configurations are located in the `config` directory:
- `character_config.json`: Character settings
- `posting_rules.json`: Posting rules
- `interaction_rules.json`: Interaction rules
- `keywords.json`: Keyword configurations

### Development Info
- Language: Python
- Code Style: PEP 8
- Testing: pytest
- Version Control: Git
- CI/CD: GitHub Actions

### Update Log
#### 1.1.0 (2025-03-29)
- Improved text processing system
- Optimized abbreviation handling
- Enhanced emotional expression diversity
- Improved tech product terminology
- Expanded ACG terminology

#### 1.0.0 (2025-03-29)
- Initial release
- Basic auto-posting functionality
- Character memory system
- Multi-topic content generation
- Complete error handling
- Smart text processing system

---

# 日本語

## Threads 自動返信・コンテンツ配信システム

Version: 1.1.0
Last Updated: 2025-03-29

### システム概要
OpenAIベースのThreads自動返信・コンテンツ配信システムです。設定されたキャラクター性格に基づいて自動的にコンテンツを生成・配信し、実際のユーザーとの対話をシミュレートします。クラウド環境で動作し、GitHub Actionsを使用して自動デプロイと運用を行います。

### 主な機能
- キャラクター設定に基づく投稿の自動生成
- ユーザーとの対話を分析し自動返信
- 時間帯に応じた投稿頻度とスタイルの自動調整
- 対話履歴の記録と追跡システム
- 多様なトピックに対応：ACG、テクノロジー、BL等
- 適切な絵文字の自動追加

### 技術的特徴
- OpenAI GPT-3.5によるコンテンツ生成
- Python非同期プログラミング
- MongoDBによる対話記録の保存
- GitHub Actionsによる自動化
- 完全なエラー処理とリトライ機構
- スマートなテキスト処理とフォーマット

### システム要件
- Python 3.9+
- OpenAI APIキー
- MongoDBデータベース
- Threads APIアクセス権限

### インストール方法
1. リポジトリのクローン：
```bash
git clone https://github.com/chenweichiang/AI-Tools-ThreadsPoster.git
cd ThreadsPoster
```

2. 依存関係のインストール：
```bash
pip install -r requirements.txt
```

3. 環境変数の設定：
```bash
cp .env.example .env
# .envファイルを編集し、必要なAPIキーと設定を入力
```

### 使用方法
1. システムの起動：
```bash
python src/main.py
```

2. ログの監視：
```bash
tail -f logs/threadsposter.log
```

### 設定説明
システム設定は `config` ディレクトリにあります：
- `character_config.json`: キャラクター設定
- `posting_rules.json`: 投稿ルール
- `interaction_rules.json`: 対話ルール
- `keywords.json`: キーワード設定

### 開発情報
- 開発言語：Python
- コードスタイル：PEP 8
- テストフレームワーク：pytest
- バージョン管理：Git
- CI/CD：GitHub Actions

### 更新履歴
#### 1.1.0 (2025-03-29)
- テキスト処理システムの改善
- 略語と不完全な単語の処理を最適化
- 感情表現の多様性を強化
- 技術製品関連用語の改善
- ACG関連用語の拡充

#### 1.0.0 (2025-03-29)
- 初期バージョンリリース
- 基本的な自動投稿機能の実装
- キャラクターメモリーシステムの追加
- 多様なトピックのコンテンツ生成
- 完全なエラー処理機構
- スマートテキスト処理システム

---

## License | 授權協議 | ライセンス
MIT License

## Author | 作者 | 作者
Chiang, Chenwei