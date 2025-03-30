"""
Version: 2024.03.31 (v1.1.6)
Author: ThreadsPoster Team
Description: 資料庫類別，負責管理 MongoDB 連接
Last Modified: 2024.03.31
Changes:
- 實現基本資料庫連接和操作
- 加強錯誤處理
- 優化連接管理
- 加入更多資料庫操作方法
- 加強資料完整性檢查
- 改進資料存取效能
- 新增資料清理機制
"""

import logging
import motor.motor_asyncio
from datetime import datetime, timedelta
import pytz
from typing import Optional, Dict, Any, List
from cachetools import TTLCache, LRUCache
from src.exceptions import DatabaseError
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from contextlib import asynccontextmanager
from datetime import timezone

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, config):
        """初始化資料庫
        
        Args:
            config: 設定物件
        """
        self.config = config
        self.client = None
        self.db = None
        self.logger = logging.getLogger(__name__)
        
        # 設定連接池
        self.max_pool_size = int(os.getenv("MONGODB_MAX_POOL_SIZE", "50"))
        self.min_pool_size = int(os.getenv("MONGODB_MIN_POOL_SIZE", "10"))
        self.max_idle_time_ms = int(os.getenv("MONGODB_MAX_IDLE_TIME_MS", "10000"))
        
        # 初始化快取
        self.cache_ttl = int(os.getenv("MONGODB_CACHE_TTL", "300"))  # 5分鐘快取
        self.posts_cache = TTLCache(maxsize=1000, ttl=self.cache_ttl)
        self.count_cache = TTLCache(maxsize=100, ttl=60)  # 1分鐘快取計數
        self.post_count_cache = TTLCache(maxsize=100, ttl=3600)  # 1小時過期
        self.article_cache = LRUCache(maxsize=1000)  # 最多保存1000篇文章
        self.personality_cache = TTLCache(maxsize=10, ttl=3600)  # 人設快取
        
    async def initialize(self):
        """初始化資料庫連接"""
        try:
            # 建立資料庫連接
            self.client = motor.motor_asyncio.AsyncIOMotorClient(self.config.MONGODB_URI)
            self.db = self.client[self.config.MONGODB_DB_NAME]
            
            # 建立索引
            await self.db.articles.create_index([("created_at", -1)])
            await self.db.articles.create_index([("post_id", 1)], unique=True)
            await self.db.personality_memories.create_index([("context", 1)], unique=True)
            
            self.logger.info("資料庫連接成功")
            
        except Exception as e:
            self.logger.error(f"資料庫連接失敗：{str(e)}")
            raise DatabaseError(f"資料庫連接失敗：{str(e)}")
            
    async def close(self):
        """關閉資料庫連接"""
        if self.client:
            self.client.close()
            self.logger.info("資料庫連接已關閉")
            
    async def save_post(self, post_data: dict) -> bool:
        """儲存發文資料到資料庫
        
        Args:
            post_data: 包含發文資訊的字典
            
        Returns:
            bool: 儲存成功返回 True，失敗返回 False
        """
        try:
            if not isinstance(post_data, dict):
                raise ValueError("post_data 必須是字典類型")
                
            # 檢查必要欄位
            required_fields = ["post_id", "content", "timestamp"]
            for field in required_fields:
                if field not in post_data:
                    raise ValueError(f"缺少必要欄位：{field}")
            
            # 確保 post_id 是字串
            post_data["post_id"] = str(post_data["post_id"])
            
            # 確保時間戳記是 UTC 時間
            if isinstance(post_data["timestamp"], datetime):
                post_data["timestamp"] = post_data["timestamp"].astimezone(timezone.utc)
            
            # 插入資料
            if self.client is None:
                await self.initialize()
                
            result = await self.db.posts.insert_one(post_data)
            success = result.inserted_id is not None
            
            if success:
                self.logger.info("成功儲存發文，ID：%s", post_data["post_id"])
                # 更新快取
                self.posts_cache[post_data["post_id"]] = post_data
            else:
                self.logger.error("儲存發文失敗：無法獲取插入ID")
                
            return success
            
        except Exception as e:
            self.logger.error("儲存發文失敗：%s", str(e))
            return False
            
    async def get_post_count(self) -> int:
        """獲取今日發文數量
        
        Returns:
            int: 今日發文數量
        """
        try:
            # 檢查快取
            if "today_post_count" in self.post_count_cache:
                return self.post_count_cache["today_post_count"]
                
            # 計算今日發文數量
            today_start = datetime.now(pytz.UTC).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            today_end = today_start + timedelta(days=1)
            
            count = await self.count_articles_between(today_start, today_end)
            
            # 更新快取
            self.post_count_cache["today_post_count"] = count
            
            return count
            
        except Exception as e:
            self.logger.error(f"獲取今日發文數量時發生錯誤：{str(e)}")
            raise DatabaseError(f"獲取今日發文數量失敗：{str(e)}")
            
    async def increment_post_count(self):
        """增加發文計數"""
        try:
            # 更新快取
            if "today_post_count" in self.post_count_cache:
                self.post_count_cache["today_post_count"] += 1
            else:
                await self.get_post_count()  # 重新載入快取
                
            self.logger.info("發文計數已增加")
            
        except Exception as e:
            self.logger.error(f"增加發文計數時發生錯誤：{str(e)}")
            raise DatabaseError(f"增加發文計數失敗：{str(e)}")
            
    async def get_post(self, post_id: str) -> Optional[Dict[str, Any]]:
        """獲取指定 ID 的發文資料
        
        Args:
            post_id: 發文 ID
            
        Returns:
            Optional[Dict[str, Any]]: 發文資料，如果不存在則返回 None
        """
        try:
            # 檢查快取
            if post_id in self.posts_cache:
                return self.posts_cache[post_id]
                
            if self.client is None:
                await self.initialize()
                
            post = await self.db.posts.find_one({"post_id": post_id})
            
            if post:
                # 更新快取
                self.posts_cache[post_id] = post
                
            return post
            
        except Exception as e:
            self.logger.error("獲取發文資料失敗：%s", str(e))
            return None
            
    async def get_recent_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """獲取最近的發文列表
        
        Args:
            limit: 返回的最大數量
            
        Returns:
            List[Dict[str, Any]]: 發文列表
        """
        try:
            if self.client is None:
                await self.initialize()
                
            cursor = self.db.posts.find().sort("timestamp", -1).limit(limit)
            posts = await cursor.to_list(length=limit)
            
            # 更新快取
            for post in posts:
                self.posts_cache[post["post_id"]] = post
                
            return posts
            
        except Exception as e:
            self.logger.error("獲取最近發文列表失敗：%s", str(e))
            return []
            
    async def clear_cache(self):
        """清除所有快取"""
        self.posts_cache.clear()
        self.count_cache.clear()
        self.logger.info("快取已清除")

    async def get_personality_memory(self, context: str) -> Optional[Dict[str, Any]]:
        """獲取人設記憶
        
        Args:
            context: 人設上下文
            
        Returns:
            Optional[Dict[str, Any]]: 人設記憶，如果不存在則返回 None
        """
        try:
            # 檢查快取
            if context in self.personality_cache:
                return self.personality_cache[context]
                
            # 查詢資料庫
            memory = await self.db.personality_memories.find_one({"context": context})
            
            # 更新快取
            if memory:
                self.personality_cache[context] = memory
                
            return memory
            
        except Exception as e:
            self.logger.error(f"獲取人設記憶時發生錯誤：{str(e)}")
            raise DatabaseError(f"獲取人設記憶失敗：{str(e)}")
            
    async def save_personality_memory(self, context: str, memory: Dict[str, Any]):
        """儲存人設記憶
        
        Args:
            context: 人設上下文
            memory: 人設記憶
        """
        try:
            # 更新資料庫
            await self.db.personality_memories.update_one(
                {"context": context},
                {"$set": memory},
                upsert=True
            )
            
            # 更新快取
            self.personality_cache[context] = memory
            self.logger.info(f"人設記憶儲存成功：{context}")
            
        except Exception as e:
            self.logger.error(f"儲存人設記憶時發生錯誤：{str(e)}")
            raise DatabaseError(f"儲存人設記憶失敗：{str(e)}")
            
    async def save_article(self, article: Dict[str, Any]):
        """儲存文章
        
        Args:
            article: 文章資料
        """
        try:
            await self.db.articles.insert_one(article)
            self.article_cache[article["post_id"]] = article
            self.logger.info(f"文章儲存成功：{article['post_id']}")
        except Exception as e:
            self.logger.error(f"儲存文章時發生錯誤：{str(e)}")
            raise DatabaseError(f"儲存文章失敗：{str(e)}")
            
    async def get_article(self, post_id: str) -> Optional[Dict[str, Any]]:
        """獲取文章
        
        Args:
            post_id: 文章 ID
            
        Returns:
            Optional[Dict[str, Any]]: 文章資料，如果不存在則返回 None
        """
        try:
            # 檢查快取
            if post_id in self.article_cache:
                return self.article_cache[post_id]
                
            # 查詢資料庫
            article = await self.db.articles.find_one({"post_id": post_id})
            
            # 更新快取
            if article:
                self.article_cache[post_id] = article
                
            return article
            
        except Exception as e:
            self.logger.error(f"獲取文章時發生錯誤：{str(e)}")
            raise DatabaseError(f"獲取文章失敗：{str(e)}")
            
    async def count_articles_between(self, start_time: datetime, end_time: datetime) -> int:
        """計算指定時間範圍內的文章數量
        
        Args:
            start_time: 開始時間
            end_time: 結束時間
            
        Returns:
            int: 文章數量
        """
        try:
            count = await self.db.articles.count_documents({
                "created_at": {
                    "$gte": start_time,
                    "$lt": end_time
                }
            })
            return count
        except Exception as e:
            self.logger.error(f"計算文章數量時發生錯誤：{str(e)}")
            raise DatabaseError(f"計算文章數量失敗：{str(e)}")
            
    async def delete_oldest_articles(self, count: int) -> int:
        """刪除最舊的文章
        
        Args:
            count: 要刪除的文章數量
            
        Returns:
            int: 實際刪除的文章數量
        """
        try:
            # 獲取最舊的文章
            cursor = self.db.articles.find().sort("created_at", 1).limit(count)
            deleted_count = 0
            
            async for article in cursor:
                # 從資料庫中刪除
                result = await self.db.articles.delete_one({"_id": article["_id"]})
                if result.deleted_count > 0:
                    # 從快取中刪除
                    if article["post_id"] in self.article_cache:
                        del self.article_cache[article["post_id"]]
                    deleted_count += 1
                    
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"刪除文章時發生錯誤：{str(e)}")
            raise DatabaseError(f"刪除文章失敗：{str(e)}")
            
    async def get_user_history(self, user_id: str) -> Dict[str, Any]:
        """獲取用戶歷史記錄
        
        Args:
            user_id: 用戶 ID
            
        Returns:
            Dict[str, Any]: 用戶歷史記錄
        """
        try:
            history = await self.db.user_history.find_one({"user_id": user_id})
            return history or {"conversations": []}
        except Exception as e:
            self.logger.error(f"獲取用戶歷史記錄時發生錯誤：{str(e)}")
            raise DatabaseError(f"獲取用戶歷史記錄失敗：{str(e)}")
            
    async def save_user_history(self, user_id: str, history: Dict[str, Any]):
        """儲存用戶歷史記錄
        
        Args:
            user_id: 用戶 ID
            history: 歷史記錄
        """
        try:
            await self.db.user_history.update_one(
                {"user_id": user_id},
                {"$set": history},
                upsert=True
            )
            self.logger.info(f"用戶歷史記錄儲存成功：{user_id}")
        except Exception as e:
            self.logger.error(f"儲存用戶歷史記錄時發生錯誤：{str(e)}")
            raise DatabaseError(f"儲存用戶歷史記錄失敗：{str(e)}")