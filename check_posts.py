import asyncio
import json
from src.config import Config
from src.db_handler import DatabaseHandler

async def get_posts():
    config = Config()
    db = DatabaseHandler(config)
    await db.initialize()
    
    try:
        posts = await db.database.db.posts.find().sort('timestamp', -1).limit(3).to_list(length=3)
        for post in posts:
            print(f'文章ID: {post.get("post_id", "未知")}\n內容: {post.get("content", "無內容")}\n')
    except Exception as e:
        print(f"錯誤: {str(e)}")
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(get_posts()) 