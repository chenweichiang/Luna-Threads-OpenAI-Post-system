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
- 整合性能監控
- 優化連接池設定
- 改進快取機制
"""

import logging
import motor.motor_asyncio
from datetime import datetime, timedelta
import pytz
from typing import Optional, Dict, Any, List
import os
from cachetools import TTLCache, LRUCache
from src.exceptions import DatabaseError
from src.performance_monitor import performance_monitor, track_performance

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
        self.performance_monitor = performance_monitor
        
        # 設定連接池
        self.max_pool_size = int(os.getenv("MONGODB_MAX_POOL_SIZE", "50"))
        self.min_pool_size = int(os.getenv("MONGODB_MIN_POOL_SIZE", "10"))
        self.max_idle_time_ms = int(os.getenv("MONGODB_MAX_IDLE_TIME_MS", "10000"))
        self.server_selection_timeout_ms = int(os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "5000"))
        self.connection_timeout_ms = int(os.getenv("MONGODB_CONNECTION_TIMEOUT_MS", "30000"))
        
        # 初始化快取
        self.cache_ttl = int(os.getenv("MONGODB_CACHE_TTL", "300"))  # 5分鐘快取
        self.posts_cache = TTLCache(maxsize=1000, ttl=self.cache_ttl)
        self.count_cache = TTLCache(maxsize=100, ttl=60)  # 1分鐘快取計數
        self.post_count_cache = TTLCache(maxsize=100, ttl=3600)  # 1小時過期
        self.article_cache = LRUCache(maxsize=1000)  # 最多保存1000篇文章
        self.personality_cache = TTLCache(maxsize=10, ttl=3600)  # 人設快取
        
    @track_performance("db_initialize")
    async def initialize(self):
        """初始化資料庫連接"""
        try:
            # 建立資料庫連接
            self.client = motor.motor_asyncio.AsyncIOMotorClient(
                self.config.MONGODB_URI,
                maxPoolSize=self.max_pool_size,
                minPoolSize=self.min_pool_size,
                maxIdleTimeMS=self.max_idle_time_ms,
                serverSelectionTimeoutMS=self.server_selection_timeout_ms,
                connectTimeoutMS=self.connection_timeout_ms,
                retryWrites=True,
                w="majority"  # 確保寫入成功
            )
            self.db = self.client[self.config.MONGODB_DB_NAME]
            
            # 建立索引
            await self.db.articles.create_index([("created_at", -1)])
            await self.db.articles.create_index([("post_id", 1)], unique=True)
            await self.db.personality_memories.create_index([("context", 1)], unique=True)
            await self.db.posts.create_index([("post_id", 1)], unique=True)
            await self.db.posts.create_index([("timestamp", -1)])
            
            # 檢查連接是否成功
            await self.client.admin.command('ping')
            
            self.logger.info("資料庫連接成功")
            
            return True
            
        except Exception as e:
            self.logger.error(f"資料庫連接失敗：{str(e)}")
            raise DatabaseError(f"資料庫連接失敗：{str(e)}")
            
    async def close(self):
        """關閉資料庫連接"""
        if self.client:
            try:
                self.client.close()
                self.logger.info("資料庫連接已關閉")
            except Exception as e:
                self.logger.error(f"關閉資料庫連接時發生錯誤：{str(e)}")
                
    @track_performance("db_save_post")
    async def save_post(self, post_data: dict) -> bool:
        """儲存發文資料
        
        Args:
            post_data: 發文資料
            
        Returns:
            bool: 是否成功
        """
        try:
            self.performance_monitor.start_operation("db_save_post")
            
            # 確保必要欄位存在
            required_fields = ["post_id", "content", "timestamp"]
            for field in required_fields:
                if field not in post_data:
                    self.logger.error(f"儲存發文失敗：缺少必要欄位 {field}")
                    self.performance_monitor.record_db_operation("insert", False)
                    return False
            
            # 確保 post_id 是字串
            post_data["post_id"] = str(post_data["post_id"])
            
            # 確保時間戳記是 UTC 時間
            if isinstance(post_data["timestamp"], datetime):
                post_data["timestamp"] = post_data["timestamp"].astimezone(pytz.UTC)
            
            # 插入資料
            if self.client is None:
                await self.initialize()
                
            # 批量操作準備
            operations = []
            
            # 如果文章已存在，就更新
            operations.append(
                motor.motor_asyncio.UpdateOne(
                    {"post_id": post_data["post_id"]},
                    {"$set": post_data},
                    upsert=True
                )
            )
            
            # 執行批量操作
            result = await self.db.posts.bulk_write(operations)
            success = result.upserted_count > 0 or result.modified_count > 0
            
            if success:
                self.logger.info("成功儲存發文，ID：%s", post_data["post_id"])
                # 更新快取
                self.posts_cache[post_data["post_id"]] = post_data
                self.performance_monitor.record_db_operation("insert", True)
            else:
                self.logger.error("儲存發文失敗：無法獲取插入ID")
                self.performance_monitor.record_db_operation("insert", False)
                
            return success
            
        except Exception as e:
            self.logger.error("儲存發文失敗：%s", str(e))
            self.performance_monitor.record_db_operation("insert", False)
            return False
        finally:
            self.performance_monitor.end_operation("db_save_post")
            
    @track_performance("db_get_post_count")
    async def get_post_count(self) -> int:
        """獲取今日發文數量
        
        Returns:
            int: 今日發文數量
        """
        try:
            # 檢查快取
            if "today_post_count" in self.post_count_cache:
                self.performance_monitor.record_db_operation("query", True, True)
                return self.post_count_cache["today_post_count"]
                
            # 計算今日發文數量
            today_start = datetime.now(pytz.UTC).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            today_end = today_start + timedelta(days=1)
            
            count = await self.count_articles_between(today_start, today_end)
            
            # 更新快取
            self.post_count_cache["today_post_count"] = count
            self.performance_monitor.record_db_operation("query", True, False)
            
            return count
            
        except Exception as e:
            self.logger.error(f"獲取今日發文數量時發生錯誤：{str(e)}")
            self.performance_monitor.record_db_operation("query", False)
            raise DatabaseError(f"獲取今日發文數量失敗：{str(e)}")
            
    @track_performance("db_increment_post_count")
    async def increment_post_count(self):
        """增加發文計數"""
        try:
            # 更新快取
            if "today_post_count" in self.post_count_cache:
                self.post_count_cache["today_post_count"] += 1
            else:
                await self.get_post_count()  # 重新載入快取
                
            self.logger.info("發文計數已增加")
            self.performance_monitor.record_db_operation("update", True)
            
        except Exception as e:
            self.logger.error(f"增加發文計數時發生錯誤：{str(e)}")
            self.performance_monitor.record_db_operation("update", False)
            raise DatabaseError(f"增加發文計數失敗：{str(e)}")
            
    @track_performance("db_get_post")
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
                self.performance_monitor.record_db_operation("query", True, True)
                return self.posts_cache[post_id]
                
            if self.client is None:
                await self.initialize()
                
            post = await self.db.posts.find_one({"post_id": post_id})
            
            if post:
                # 更新快取
                self.posts_cache[post_id] = post
                self.performance_monitor.record_db_operation("query", True, False)
            else:
                self.performance_monitor.record_db_operation("query", True, False)
                
            return post
            
        except Exception as e:
            self.logger.error("獲取發文資料失敗：%s", str(e))
            self.performance_monitor.record_db_operation("query", False)
            return None
            
    @track_performance("db_get_recent_posts")
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
                
            self.performance_monitor.record_db_operation("query", True, False)
            return posts
            
        except Exception as e:
            self.logger.error("獲取最近發文列表失敗：%s", str(e))
            self.performance_monitor.record_db_operation("query", False)
            return []
            
    @track_performance("db_clear_cache")
    async def clear_cache(self):
        """清除所有快取"""
        self.posts_cache.clear()
        self.count_cache.clear()
        self.post_count_cache.clear()
        self.article_cache.clear()
        self.personality_cache.clear()
        self.logger.info("快取已清除")

    @track_performance("db_get_personality_memory")
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
                self.performance_monitor.record_db_operation("query", True, True)
                return self.personality_cache[context]
                
            # 查詢資料庫
            memory = await self.db.personality_memories.find_one({"context": context})
            
            # 更新快取
            if memory:
                self.personality_cache[context] = memory
                self.performance_monitor.record_db_operation("query", True, False)
            else:
                self.performance_monitor.record_db_operation("query", True, False)
                
            return memory
            
        except Exception as e:
            self.logger.error(f"獲取人設記憶時發生錯誤：{str(e)}")
            self.performance_monitor.record_db_operation("query", False)
            raise DatabaseError(f"獲取人設記憶失敗：{str(e)}")
            
    @track_performance("db_save_personality_memory")
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
            self.performance_monitor.record_db_operation("update", True)
            
        except Exception as e:
            self.logger.error(f"儲存人設記憶時發生錯誤：{str(e)}")
            self.performance_monitor.record_db_operation("update", False)
            raise DatabaseError(f"儲存人設記憶失敗：{str(e)}")
            
    @track_performance("db_save_article")
    async def save_article(self, article: Dict[str, Any]):
        """儲存文章
        
        Args:
            article: 文章資料
        """
        try:
            await self.db.articles.insert_one(article)
            self.article_cache[article["post_id"]] = article
            self.logger.info(f"文章儲存成功：{article['post_id']}")
            self.performance_monitor.record_db_operation("insert", True)
        except Exception as e:
            self.logger.error(f"儲存文章時發生錯誤：{str(e)}")
            self.performance_monitor.record_db_operation("insert", False)
            raise DatabaseError(f"儲存文章失敗：{str(e)}")
            
    @track_performance("db_get_article")
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
                self.performance_monitor.record_db_operation("query", True, True)
                return self.article_cache[post_id]
                
            # 查詢資料庫
            article = await self.db.articles.find_one({"post_id": post_id})
            
            # 更新快取
            if article:
                self.article_cache[post_id] = article
                self.performance_monitor.record_db_operation("query", True, False)
            else:
                self.performance_monitor.record_db_operation("query", True, False)
                
            return article
            
        except Exception as e:
            self.logger.error(f"獲取文章時發生錯誤：{str(e)}")
            self.performance_monitor.record_db_operation("query", False)
            raise DatabaseError(f"獲取文章失敗：{str(e)}")
            
    @track_performance("db_count_articles")
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
            self.performance_monitor.record_db_operation("query", True)
            return count
        except Exception as e:
            self.logger.error(f"計算文章數量時發生錯誤：{str(e)}")
            self.performance_monitor.record_db_operation("query", False)
            raise DatabaseError(f"計算文章數量失敗：{str(e)}")
            
    @track_performance("db_delete_oldest_articles")
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
            
            # 收集要刪除的 IDs
            article_ids = []
            post_ids = []
            async for article in cursor:
                article_ids.append(article["_id"])
                post_ids.append(article["post_id"])
            
            # 批量刪除
            if article_ids:
                result = await self.db.articles.delete_many({"_id": {"$in": article_ids}})
                deleted_count = result.deleted_count
                
                # 從快取中刪除
                for post_id in post_ids:
                    if post_id in self.article_cache:
                        del self.article_cache[post_id]
                
                self.performance_monitor.record_db_operation("update", True)
                return deleted_count
            return 0
            
        except Exception as e:
            self.logger.error(f"刪除文章時發生錯誤：{str(e)}")
            self.performance_monitor.record_db_operation("update", False)
            raise DatabaseError(f"刪除文章失敗：{str(e)}")
            
    @track_performance("db_get_user_history")
    async def get_user_history(self, user_id: str) -> Dict[str, Any]:
        """獲取用戶歷史記錄
        
        Args:
            user_id: 用戶 ID
            
        Returns:
            Dict[str, Any]: 用戶歷史記錄
        """
        try:
            history = await self.db.user_history.find_one({"user_id": user_id})
            if history:
                self.performance_monitor.record_db_operation("query", True)
            else:
                self.performance_monitor.record_db_operation("query", True)
            return history or {"conversations": []}
        except Exception as e:
            self.logger.error(f"獲取用戶歷史記錄時發生錯誤：{str(e)}")
            self.performance_monitor.record_db_operation("query", False)
            raise DatabaseError(f"獲取用戶歷史記錄失敗：{str(e)}")
            
    @track_performance("db_save_user_history")
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
            self.performance_monitor.record_db_operation("update", True)
        except Exception as e:
            self.logger.error(f"儲存用戶歷史記錄時發生錯誤：{str(e)}")
            self.performance_monitor.record_db_operation("update", False)
            raise DatabaseError(f"儲存用戶歷史記錄失敗：{str(e)}")
            
    @track_performance("db_cleanup")
    async def cleanup_old_data(self, days: int = 30):
        """清理舊資料
        
        Args:
            days: 保留的天數，預設30天
        """
        try:
            cutoff_date = datetime.now(pytz.UTC) - timedelta(days=days)
            
            # 刪除舊文章
            result = await self.db.articles.delete_many({"created_at": {"$lt": cutoff_date}})
            
            # 清理快取中可能的舊資料
            await self.clear_cache()
            
            self.logger.info(f"已清理 {result.deleted_count} 筆舊文章資料")
            self.performance_monitor.record_db_operation("update", True)
            
            return result.deleted_count
        except Exception as e:
            self.logger.error(f"清理舊資料時發生錯誤：{str(e)}")
            self.performance_monitor.record_db_operation("update", False)
            raise DatabaseError(f"清理舊資料失敗：{str(e)}")
            
    async def get_database_stats(self) -> Dict[str, Any]:
        """獲取資料庫統計資訊
        
        Returns:
            Dict[str, Any]: 資料庫統計資訊
        """
        try:
            stats = {}
            
            # 文章數量
            stats["articles_count"] = await self.db.articles.count_documents({})
            
            # 用戶數量
            stats["users_count"] = await self.db.user_history.count_documents({})
            
            # 文章內存佔用
            stats["cache"] = {
                "posts_cache_size": len(self.posts_cache),
                "article_cache_size": len(self.article_cache),
                "personality_cache_size": len(self.personality_cache)
            }
            
            # 性能監控器指標
            stats["performance"] = self.performance_monitor.summary()
            
            return stats
        except Exception as e:
            self.logger.error(f"獲取資料庫統計資訊時發生錯誤：{str(e)}")
            return {"error": str(e)}