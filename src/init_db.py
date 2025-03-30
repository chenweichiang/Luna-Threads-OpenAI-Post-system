"""初始化資料庫連接和集合"""
import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

async def init_db():
    # 獲取環境變數
    mongo_uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB", "threadsposter")
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