# ThreadsPoster 貢獻指南

感謝您對 ThreadsPoster 專案的關注！這份文件將幫助您了解如何參與貢獻。

## 開發環境設置

1. 克隆儲存庫：
```bash
git clone https://github.com/chenweichiang/Luna-Threads-OpenAI-Post-system.git
cd Luna-Threads-OpenAI-Post-system
```

2. 創建並啟用虛擬環境：
```bash
python -m venv venv
source venv/bin/activate  # 在 Windows 上使用: venv\Scripts\activate
```

3. 安裝依賴：
```bash
pip install -r requirements.txt
```

4. 設置環境變數：
```bash
cp .env.example .env
# 編輯 .env 文件填入必要的 API 金鑰和設定
```

## 程式碼風格指南

本專案遵循以下程式碼風格規範：

1. **命名規則**
   - 類名：駝峰式 (例如: `TimeController`)
   - 方法/函數：小寫_連接 (例如: `get_next_post_time`)
   - 常量：大寫_連接 (例如: `MAX_POSTS_PER_DAY`)
   - 私有方法：以下劃線開頭 (例如: `_update_next_post_time`)

2. **文檔規範**
   - 所有公共方法必須有文檔字符串 (docstring)
   - 每個模組頂部必須包含版本、作者、描述等標準標頭
   - 描述參數和返回值
   - 說明函數用途和行為

3. **日誌規範**
   - 使用標準化格式 `【類別】具體訊息`
   - 使用分隔線區分主要流程
   - 使用適當的日誌級別 (INFO, ERROR, DEBUG)

4. **Python 風格**
   - 遵循 PEP 8 規範
   - 使用 4 個空格縮進
   - 行長度限制在 120 字元以內

## 提交變更流程

1. **創建分支**：
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **進行更改**：
   - 實現新功能或修復
   - 添加或更新測試
   - 更新文檔

3. **更新版權和標頭**：
   ```bash
   ./update_copyright.py
   ```

4. **提交您的更改**：
   ```bash
   git add .
   git commit -m "描述您的更改"
   ```

5. **推送到您的分支**：
   ```bash
   git push origin feature/your-feature-name
   ```

6. **創建 Pull Request**：
   - 在 GitHub 界面中創建一個 Pull Request
   - 描述您的更改和實現方法
   - 等待審核和反饋

## 測試

請確保您的代碼包含適當的測試：

1. 運行測試：
   ```bash
   python -m unittest discover -s tests
   ```

2. 檢查代碼覆蓋率：
   ```bash
   coverage run -m unittest discover -s tests
   coverage report
   ```

## 版本控制

1. 版本號格式：`主版本.次版本.修訂版本`
2. 更新 `CHANGELOG.md` 記錄所有變更
3. 在提交訊息中參考相關的問題編號

## 問題報告

如果您發現了 bug 或有功能請求，請遵循以下步驟：

1. 檢查現有問題，避免重複
2. 使用問題模板提供詳細信息
3. 包括重現步驟、期望行為和實際行為
4. 如可能，提供日誌、截圖或示例代碼

## 行為準則

參與本專案的所有貢獻者都應遵循以下基本準則：

1. 使用包容性語言
2. 尊重不同觀點和經驗
3. 優雅地接受建設性批評
4. 專注於對社區最有利的事情

## 許可證

通過貢獻您的代碼，您同意您的貢獻將在 [MIT 許可證](LICENSE) 下提供。 