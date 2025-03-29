"""
Version: 2024.03.30
Author: ThreadsPoster Team
Description: 資料庫處理器，負責管理資料庫操作的高層邏輯
Last Modified: 2024.03.30
Changes:
- 優化資料庫操作邏輯
- 加強錯誤處理機制
- 改進資料庫連接管理
"""

import logging
import motor.motor_asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from src.config import Config

logger = logging.getLogger(__name__)

class DBHandler:
    def __init__(self, config: Config):
        """初始化資料庫處理器"""
        self.config = config
        self.client = None
        self.db = None
        self.collection = None
        self.database = None  # Database 實例

    async def initialize(self):
        """初始化資料庫連接"""
        try:
            # 初始化 MongoDB 連接
            self.client = motor.motor_asyncio.AsyncIOMotorClient(self.config.MONGODB_URI)
            self.db = self.client[self.config.MONGODB_DB_NAME]
            self.collection = self.db[self.config.MONGODB_COLLECTION]
            
            # 初始化 Database 實例
            from src.database import Database
            self.database = Database(self.config)
            await self.database.initialize()
            
            logger.info("資料庫連接成功")
        except Exception as e:
            logger.error(f"資料庫連接失敗: {e}")
            raise

    async def close(self):
        """關閉資料庫連接"""
        if self.client:
            self.client.close()
            if self.database:
                await self.database.close()
            logger.info("資料庫連接已關閉")

    async def get_today_posts_count(self) -> int:
        """獲取今日發文數量"""
        try:
            today = datetime.now(self.config.TIMEZONE).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            tomorrow = today + timedelta(days=1)
            
            count = await self.collection.count_documents({
                "created_at": {"$gte": today, "$lt": tomorrow}
            })
            return count
        except Exception as e:
            logger.error(f"獲取今日發文數量失敗: {e}")
            return 0

    async def save_article(
        self,
        post_id: str,
        content: str,
        topics: List[str],
        sentiment: Dict[str, float]
    ) -> bool:
        """儲存文章到資料庫"""
        try:
            article = {
                "post_id": post_id,
                "content": content,
                "topics": topics,
                "sentiment": sentiment,
                "created_at": datetime.now(self.config.TIMEZONE)
            }
            await self.collection.insert_one(article)
            logger.info(f"文章儲存成功: {post_id}")
            return True
        except Exception as e:
            logger.error(f"文章儲存失敗: {e}")
            return False

    async def get_recent_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """獲取最近的文章"""
        try:
            cursor = self.collection.find().sort("created_at", -1).limit(limit)
            posts = await cursor.to_list(length=limit)
            return posts
        except Exception as e:
            logger.error(f"獲取最近文章失敗: {e}")
            return []

    async def get_post_by_id(self, post_id: str) -> Optional[Dict[str, Any]]:
        """根據 ID 獲取文章"""
        try:
            post = await self.collection.find_one({"post_id": post_id})
            return post
        except Exception as e:
            logger.error(f"獲取文章失敗: {e}")
            return None

    async def reset_today_posts(self) -> bool:
        """重置今日發文計數"""
        try:
            today = datetime.now(self.config.TIMEZONE).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            tomorrow = today + timedelta(days=1)
            
            result = await self.collection.delete_many({
                "created_at": {"$gte": today, "$lt": tomorrow}
            })
            logger.info(f"重置今日發文計數成功，刪除 {result.deleted_count} 篇文章")
            return True
        except Exception as e:
            logger.error(f"重置今日發文計數失敗: {e}")
            return False 