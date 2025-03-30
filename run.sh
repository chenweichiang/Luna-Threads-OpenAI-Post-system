#!/bin/bash
set -e

echo "ThreadsPoster 啟動中..."

# 確保日誌目錄存在
mkdir -p logs

# 檢查必要的環境變數
echo "檢查環境變數..."
if [ -f "src/check_env.py" ]; then
    python src/check_env.py
else
    echo "找不到環境變數檢查腳本，創建新腳本..."
    cat > src/check_env.py << 'EOF'
"""檢查環境變數是否存在並有效"""
import os
import sys
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

required_vars = [
    "OPENAI_API_KEY",
    "THREADS_ACCESS_TOKEN",
    "THREADS_USER_ID",
    "MONGODB_URI"
]

missing_vars = []
for var in required_vars:
    if not os.getenv(var):
        missing_vars.append(var)

if missing_vars:
    print(f"錯誤：缺少以下必要的環境變數: {', '.join(missing_vars)}")
    sys.exit(1)
else:
    print("環境變數檢查通過")
    sys.exit(0)
EOF
    python src/check_env.py
fi

if [ $? -ne 0 ]; then
    echo "環境變數檢查失敗！"
    exit 1
fi

# 初始化資料庫
echo "初始化資料庫..."
if [ -f "src/init_db.py" ]; then
    python src/init_db.py
else
    echo "找不到資料庫初始化腳本，創建新腳本..."
    cat > src/init_db.py << 'EOF'
"""初始化資料庫連接和集合"""
import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

async def init_db():
    # 獲取環境變數
    mongo_uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB_NAME", "threadsposter")
    collection_name = os.getenv("MONGODB_COLLECTION", "posts")
    
    if not mongo_uri:
        print("錯誤：未設定 MONGODB_URI 環境變數")
        return False
        
    try:
        # 連接 MongoDB
        client = AsyncIOMotorClient(mongo_uri)
        db = client[db_name]
        
        # 檢查連接
        await client.admin.command('ping')
        
        # 確保集合存在
        if collection_name not in await db.list_collection_names():
            await db.create_collection(collection_name)
            
        # 建立索引
        await db[collection_name].create_index("post_id", unique=True)
        await db[collection_name].create_index("created_at")
        
        print(f"成功連接到資料庫 {db_name} 並建立/確認集合 {collection_name}")
        return True
    except Exception as e:
        print(f"資料庫初始化錯誤：{str(e)}")
        return False
    finally:
        # 關閉連接
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    result = asyncio.run(init_db())
    if not result:
        exit(1)
EOF
    python src/init_db.py
fi

if [ $? -ne 0 ]; then
    echo "資料庫初始化失敗！"
    exit 1
fi

# 檢查系統資源
echo "檢查系統資源..."
if [ -f "src/check_memory.py" ]; then
    python src/check_memory.py
else
    echo "找不到記憶體檢查腳本，創建新腳本..."
    cat > src/check_memory.py << 'EOF'
"""檢查系統記憶體使用情況"""
import os
import psutil

def check_memory_usage():
    # 獲取最大允許的記憶體使用率
    max_usage = float(os.getenv("MAX_MEMORY_USAGE", "80"))
    
    # 獲取當前記憶體使用情況
    memory = psutil.virtual_memory()
    current_usage = memory.percent
    
    print(f"當前記憶體使用率: {current_usage:.1f}% (最大允許: {max_usage:.1f}%)")
    
    # 如果超過最大值，退出
    if current_usage > max_usage:
        print("警告: 記憶體使用率過高!")
        return False
    
    return True

if __name__ == "__main__":
    if not check_memory_usage():
        exit(1)
EOF
    # 安裝所需的依賴
    pip install psutil
    python src/check_memory.py
fi

if [ $? -ne 0 ]; then
    echo "系統資源不足！"
    exit 1
fi

# 執行主程式
echo "開始執行主程式..."
exec python -m src.main 