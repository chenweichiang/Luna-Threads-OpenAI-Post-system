"""
Version: 2024.03.30
Author: ThreadsPoster Team
Description: 資料庫處理器，負責管理與資料庫的所有互動
Last Modified: 2024.03.30
Changes:
- 改進資料庫連接管理
- 加強錯誤處理
- 優化快取機制
- 統一日誌路徑
"""

import logging
import motor.motor_asyncio
from datetime import datetime, timedelta
import pytz
from typing import Optional, Dict, Any, List
from cachetools import TTLCache, LRUCache
from src.exceptions import DatabaseError

class DatabaseHandler:
    """資料庫處理器類別"""
    
    def __init__(self, mongodb_uri: str, database: str):
        """初始化資料庫處理器
        
        Args:
            mongodb_uri: MongoDB 連接字串
            database: 資料庫名稱
        """
        self.mongodb_uri = mongodb_uri
        self.database_name = database
        self.client = None
        self.db = None
        self.logger = logging.getLogger(__name__)
        
        # 初始化快取
        self.post_count_cache = TTLCache(maxsize=100, ttl=3600)  # 1小時過期
        self.article_cache = LRUCache(maxsize=1000)  # 最多保存1000篇文章
        self.personality_cache = TTLCache(maxsize=10, ttl=3600)  # 人設快取
        
    async def connect(self):
        """連接到資料庫"""
        try:
            self.client = motor.motor_asyncio.AsyncIOMotorClient(self.mongodb_uri)
            self.db = self.client[self.database_name]
            
            # 建立索引
            await self.db.posts.create_index([("post_id", 1)], unique=True)
            await self.db.posts.create_index([("created_at", -1)])
            await self.db.post_counts.create_index([("date", 1)], unique=True)
            
            # 測試連接
            await self.client.admin.command('ping')
            self.logger.info("資料庫連接成功")
            
        except Exception as e:
            self.logger.error(f"資料庫連接失敗：{str(e)}")
            raise DatabaseError(f"資料庫連接失敗：{str(e)}")
            
    async def close(self):
        """關閉資料庫連接"""
        if self.client:
            self.client.close()
            self.logger.info("資料庫連接已關閉")
            
    async def get_today_posts_count(self) -> int:
        """獲取今日發文數量
        
        Returns:
            int: 今日發文數量
        """
        try:
            # 檢查快取
            cache_key = datetime.now(pytz.UTC).strftime("%Y-%m-%d")
            if cache_key in self.post_count_cache:
                return self.post_count_cache[cache_key]
                
            # 計算今日開始和結束時間
            now = datetime.now(pytz.UTC)
            today = now.strftime("%Y-%m-%d")
            
            # 從計數集合中獲取今日計數
            count_doc = await self.db.post_counts.find_one({"date": today})
            count = count_doc["count"] if count_doc else 0
            
            # 更新快取
            self.post_count_cache[cache_key] = count
            return count
            
        except Exception as e:
            self.logger.error(f"獲取今日發文數量時發生錯誤：{str(e)}")
            raise DatabaseError(f"獲取今日發文數量失敗：{str(e)}")
            
    async def increment_post_count(self):
        """增加今日發文數量"""
        try:
            # 清除快取
            cache_key = datetime.now(pytz.UTC).strftime("%Y-%m-%d")
            if cache_key in self.post_count_cache:
                del self.post_count_cache[cache_key]
                
            # 更新計數集合
            today = datetime.now(pytz.UTC).strftime("%Y-%m-%d")
            result = await self.db.post_counts.update_one(
                {"date": today},
                {"$inc": {"count": 1}},
                upsert=True
            )
            
            if result.acknowledged:
                self.logger.info("發文計數已更新")
            else:
                raise DatabaseError("更新發文計數失敗")
            
        except Exception as e:
            self.logger.error(f"增加發文數量時發生錯誤：{str(e)}")
            raise DatabaseError(f"增加發文數量失敗：{str(e)}")
            
    async def save_article(self, article: Dict[str, Any]):
        """儲存文章
        
        Args:
            article: 文章資訊
        """
        try:
            # 更新資料庫
            result = await self.db.articles.insert_one(article)
            
            # 更新快取
            self.article_cache[str(result.inserted_id)] = article
            self.logger.info(f"文章儲存成功：{result.inserted_id}")
            
        except Exception as e:
            self.logger.error(f"儲存文章時發生錯誤：{str(e)}")
            raise DatabaseError(f"儲存文章失敗：{str(e)}")
            
    async def get_user_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """獲取用戶發文歷史
        
        Args:
            days: 要查詢的天數
            
        Returns:
            List[Dict[str, Any]]: 發文歷史列表
        """
        try:
            # 計算時間範圍
            now = datetime.now(pytz.UTC)
            start_date = now - timedelta(days=days)
            
            # 查詢資料庫
            cursor = self.db.articles.find({
                "created_at": {
                    "$gte": start_date,
                    "$lt": now
                }
            }).sort("created_at", -1)
            
            return await cursor.to_list(length=None)
            
        except Exception as e:
            self.logger.error(f"獲取用戶歷史時發生錯誤：{str(e)}")
            raise DatabaseError(f"獲取用戶歷史失敗：{str(e)}")
            
    async def reset_daily_post_count(self):
        """重置今日發文計數"""
        try:
            # 清除快取
            cache_key = datetime.now(pytz.UTC).strftime("%Y-%m-%d")
            if cache_key in self.post_count_cache:
                del self.post_count_cache[cache_key]
                
            # 計算今日開始和結束時間
            now = datetime.now(pytz.UTC)
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            # 刪除今日的記錄
            await self.db.posts.delete_many({
                "created_at": {
                    "$gte": start_of_day,
                    "$lt": end_of_day
                }
            })
            self.logger.info("今日發文計數已重置")
            
        except Exception as e:
            self.logger.error(f"重置發文計數時發生錯誤：{str(e)}")
            raise DatabaseError(f"重置發文計數失敗：{str(e)}")
            
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
            
    async def get_user_interactions(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """獲取用戶互動歷史
        
        Args:
            user_id: 用戶 ID
            limit: 返回的記錄數量
            
        Returns:
            List[Dict[str, Any]]: 互動歷史列表
        """
        try:
            cursor = self.db.interactions.find(
                {"user_id": user_id}
            ).sort("timestamp", -1).limit(limit)
            
            return await cursor.to_list(length=None)
            
        except Exception as e:
            self.logger.error(f"獲取用戶互動歷史時發生錯誤：{str(e)}")
            raise DatabaseError(f"獲取用戶互動歷史失敗：{str(e)}")
            
    async def save_user_interaction(self, interaction: Dict[str, Any]):
        """儲存用戶互動
        
        Args:
            interaction: 互動資訊
        """
        try:
            await self.db.interactions.insert_one(interaction)
            self.logger.info(f"用戶互動儲存成功：{interaction['user_id']}")
            
        except Exception as e:
            self.logger.error(f"儲存用戶互動時發生錯誤：{str(e)}")
            raise DatabaseError(f"儲存用戶互動失敗：{str(e)}")
            
    async def get_mood_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """獲取情緒歷史
        
        Args:
            days: 要查詢的天數
            
        Returns:
            List[Dict[str, Any]]: 情緒歷史列表
        """
        try:
            # 計算時間範圍
            now = datetime.now(pytz.UTC)
            start_date = now - timedelta(days=days)
            
            cursor = self.db.moods.find({
                "timestamp": {
                    "$gte": start_date,
                    "$lt": now
                }
            }).sort("timestamp", -1)
            
            return await cursor.to_list(length=None)
            
        except Exception as e:
            self.logger.error(f"獲取情緒歷史時發生錯誤：{str(e)}")
            raise DatabaseError(f"獲取情緒歷史失敗：{str(e)}")
            
    async def save_mood(self, mood: Dict[str, Any]):
        """儲存情緒記錄
        
        Args:
            mood: 情緒資訊
        """
        try:
            await self.db.moods.insert_one(mood)
            self.logger.info("情緒記錄儲存成功")
            
        except Exception as e:
            self.logger.error(f"儲存情緒記錄時發生錯誤：{str(e)}")
            raise DatabaseError(f"儲存情緒記錄失敗：{str(e)}")