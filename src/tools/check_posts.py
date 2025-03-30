"""
Version: 2024.03.31 (v1.1.6)
Author: ThreadsPoster Team
Description: 檢查最新文章工具
Last Modified: 2024.03.31
Changes:
- 實現檢查最新文章功能
- 加強錯誤處理
- 修正導入路徑問題
"""

import asyncio
import json
import os
import sys

# 添加專案根目錄到路徑，以便能夠導入相關模組
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from src.config import Config
from src.db_handler import DatabaseHandler

async def get_posts():
    """獲取最近的3篇文章"""
    config = Config()
    db = DatabaseHandler(config)
    await db.initialize()
    
    try:
        posts = await db.database.db.posts.find().sort('timestamp', -1).limit(3).to_list(length=3)
        print(f"找到 {len(posts)} 篇文章")
        for post in posts:
            print(f'文章ID: {post.get("post_id", "未知")}\n內容: {post.get("content", "無內容")}\n')
    except Exception as e:
        print(f"錯誤: {str(e)}")
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(get_posts()) 