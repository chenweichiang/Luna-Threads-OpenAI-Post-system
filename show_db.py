from src.database import Database
from src.config import Config
import asyncio
import json
from datetime import datetime
import pytz

async def show_collections():
    config = Config()
    db = Database(config)
    await db.init_db()
    
    collections = ['posts', 'replies', 'conversations', 'settings', 'post_topics']
    
    for collection in collections:
        print(f'\n=== {collection} 集合的結構 ===')
        try:
            # 取得最新的一筆資料
            doc = await getattr(db.db, collection).find_one(
                sort=[('created_at', -1)] if collection != 'settings' else None
            )
            if doc:
                # 移除 _id 欄位並美化輸出
                if '_id' in doc:
                    del doc['_id']
                print(json.dumps(doc, ensure_ascii=False, indent=2, default=str))
                # 顯示文件數量
                count = await getattr(db.db, collection).count_documents({})
                print(f"\n總文件數: {count}")
            else:
                print('集合為空')
        except Exception as e:
            print(f'查詢出錯: {str(e)}')
    
    await db.client.close()

if __name__ == '__main__':
    asyncio.run(show_collections()) 