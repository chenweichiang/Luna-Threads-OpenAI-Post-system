#!/bin/bash
set -e

echo "ThreadsPoster 啟動中..."

# 確保日誌目錄存在
mkdir -p logs

# 檢查必要的環境變數
echo "檢查環境變數..."
python src/check_env.py
if [ $? -ne 0 ]; then
    echo "環境變數檢查失敗！"
    exit 1
fi

# 初始化資料庫
echo "初始化資料庫..."
python src/init_db.py
if [ $? -ne 0 ]; then
    echo "資料庫初始化失敗！"
    exit 1
fi

# 檢查系統資源
echo "檢查系統資源..."
python src/check_memory.py
if [ $? -ne 0 ]; then
    echo "系統資源不足！"
    exit 1
fi

# 執行主程式
echo "開始執行主程式..."
exec python -m src.main 