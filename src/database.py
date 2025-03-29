"""
ThreadsPoster 資料庫處理模組
處理與 MongoDB 的所有互動
"""

import logging
import pytz
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union
import motor.motor_asyncio
import mongomock_motor
import os
from pymongo.errors import PyMongoError
from src.config import Config
from src.exceptions import DatabaseError
from pymongo import ReturnDocument
import asyncio
from functools import wraps
from pymongo import UpdateOne
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import timezone

logger = logging.getLogger(__name__)

def with_retry(retries=3, delay=1):
    """資料庫操作重試裝飾器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < retries - 1:
                        delay_time = delay * (2 ** attempt)  # 指數退避
                        logger.warning(f"操作失敗，{delay_time} 秒後重試第 {attempt + 1} 次: {str(e)}")
                        await asyncio.sleep(delay_time)
            logger.error(f"操作失敗，已重試 {retries} 次: {str(last_error)}")
            raise last_error
        return wrapper
    return decorator

class Database:
    """資料庫處理類別"""
    
    def __init__(self, config: Config):
        """初始化資料庫處理器
        
        Args:
            config: 設定物件
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 初始化 MongoDB 客戶端
        self.client = AsyncIOMotorClient(self.config.MONGODB_URI)
        self.db = self.client[self.config.MONGODB_DB_NAME]
        self.posts = self.db[self.config.MONGODB_COLLECTION]
        self._initialized = False
        
    async def initialize(self):
        """初始化資料庫連接"""
        if self._initialized:
            return
            
        try:
            # 建立索引
            await self.posts.create_index([("post_id", 1)], unique=True)
            await self.posts.create_index([("created_at", -1)])
            
            self._initialized = True
            self.logger.info("資料庫初始化完成")
            
        except Exception as e:
            self.logger.error(f"資料庫初始化失敗：{str(e)}")
            raise DatabaseError("資料庫初始化失敗") from e
            
    async def close(self):
        """關閉資料庫連接"""
        if hasattr(self, 'client'):
            self.client.close()
            self.logger.info("MongoDB 連接已關閉")
            
    async def save_article(self, post_id: str, content: str, topics: List[str], sentiment: Dict[str, float]) -> bool:
        """儲存文章
        
        Args:
            post_id: 文章ID
            content: 文章內容
            topics: 主題列表
            sentiment: 情感分析結果
            
        Returns:
            bool: 是否儲存成功
        """
        try:
            now = datetime.now(pytz.UTC)
            document = {
                "post_id": post_id,
                "content": content,
                "topics": topics,
                "sentiment": sentiment,
                "created_at": now
            }
            
            await self.posts.insert_one(document)
            self.logger.info(f"文章儲存成功，ID: {post_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"儲存文章失敗：{str(e)}")
            return False
            
    async def get_today_posts_count(self) -> int:
        """獲取今日發文數量
        
        Returns:
            int: 今日發文數量
        """
        try:
            # 取得今日開始時間（台北時間）
            tz = pytz.timezone('Asia/Taipei')
            today_start = datetime.now(tz).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            
            # 轉換為 UTC 時間進行查詢
            today_start_utc = today_start.astimezone(pytz.UTC)
            
            # 查詢今日發文數量
            count = await self.posts.count_documents({
                "created_at": {"$gte": today_start_utc}
            })
            
            return count
            
        except Exception as e:
            self.logger.error(f"獲取今日發文數量失敗：{str(e)}")
            return 0
            
    async def clear_today_posts(self) -> bool:
        """清除今日發文記錄
        
        Returns:
            bool: 是否清除成功
        """
        try:
            # 取得今日開始時間（台北時間）
            tz = pytz.timezone('Asia/Taipei')
            today_start = datetime.now(tz).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            
            # 轉換為 UTC 時間進行刪除
            today_start_utc = today_start.astimezone(pytz.UTC)
            
            # 刪除今日發文記錄
            result = await self.posts.delete_many({
                "created_at": {"$gte": today_start_utc}
            })
            
            self.logger.info(f"已清除今日 {result.deleted_count} 篇貼文記錄")
            return True
            
        except Exception as e:
            self.logger.error(f"清除今日發文記錄失敗：{str(e)}")
            return False

    async def init_indexes(self):
        """初始化索引"""
        try:
            await self.conversations.create_index([("user_id", 1)])
            await self.posts.create_index([("post_id", 1)], unique=True)
            await self.posts.create_index([("timestamp", -1)])
        except Exception as e:
            self.logger.error(f"創建索引時發生錯誤：{str(e)}")

    async def get_user_history(self, user_id: str) -> Dict:
        """獲取用戶的對話歷史"""
        try:
            # 獲取最近的對話記錄
            history = await self.conversations.find_one(
                {"user_id": user_id},
                sort=[("last_interaction", -1)]
            )
            
            if not history:
                return {
                    "user_id": user_id,
                    "conversations": [],
                    "last_interaction": None
                }
                
            # 清理過期的對話記錄
            await self._cleanup_old_conversations(user_id)
            
            return history
            
        except PyMongoError as e:
            raise DatabaseError(f"獲取用戶歷史記錄時發生錯誤: {str(e)}")
            
    async def update_user_history(self, user_id: str, conversation_data: Dict) -> bool:
        """更新用戶的對話歷史"""
        try:
            current_time = datetime.now(self.timezone)
            
            # 準備新的對話記錄
            new_conversation = {
                "timestamp": current_time,
                "reply": conversation_data.get('last_reply', ''),
                "response": conversation_data.get('last_response', '')
            }
            
            # 更新資料庫
            result = await self.conversations.update_one(
                {"user_id": user_id},
                {
                    "$push": {
                        "conversations": {
                            "$each": [new_conversation],
                            "$slice": -self.config.MEMORY_CONFIG['max_history']
                        }
                    },
                    "$set": {
                        "last_interaction": current_time
                    }
                },
                upsert=True
            )
            
            return result.acknowledged
            
        except PyMongoError as e:
            raise DatabaseError(f"更新用戶歷史記錄時發生錯誤: {str(e)}")
            
    async def _cleanup_old_conversations(self, user_id: str):
        """清理過期的對話記錄"""
        try:
            cutoff_date = datetime.now(self.timezone) - timedelta(
                days=self.config.MEMORY_CONFIG['retention_days']
            )
            
            # 刪除過期的對話記錄
            await self.conversations.update_one(
                {"user_id": user_id},
                {
                    "$pull": {
                        "conversations": {
                            "timestamp": {"$lt": cutoff_date}
                        }
                    }
                }
            )
            
        except PyMongoError as e:
            raise DatabaseError(f"清理過期對話記錄時發生錯誤: {str(e)}")
            
    async def get_conversation_summary(self, user_id: str) -> str:
        """獲取對話摘要用於 AI 生成"""
        try:
            history = await self.get_user_history(user_id)
            if not history or not history.get('conversations'):
                return "這是第一次對話。"
                
            conversations = history['conversations']
            summary = []
            
            for conv in conversations[-3:]:  # 只取最近3次對話
                summary.append(f"用戶: {conv['reply']}")
                summary.append(f"回應: {conv['response']}")
                
            return "\n".join(summary)
            
        except Exception as e:
            raise DatabaseError(f"獲取對話摘要時發生錯誤: {str(e)}")

    async def save_conversation(self, user_id: str, message: str, response: str) -> bool:
        """保存對話記錄"""
        try:
            document = {
                "user_id": user_id,
                "message": message,
                "response": response,
                "timestamp": datetime.now(self.timezone)
            }
            result = await self.conversations.insert_one(document)
            return result.acknowledged
        except Exception as e:
            self.logger.error(f"保存對話記錄時發生錯誤：{str(e)}")
            return False

    async def get_user_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """獲取用戶對話歷史"""
        try:
            cursor = self.conversations.find(
                {"user_id": user_id},
                sort=[("timestamp", -1)],
                limit=limit
            )
            return await cursor.to_list(length=limit)
        except Exception as e:
            self.logger.error(f"獲取用戶對話歷史時發生錯誤：{str(e)}")
            return []

    @with_retry(retries=3, delay=1)
    async def save_post(self, post_id: str, content: str, topics: List[str], sentiment: Dict[str, float]) -> bool:
        """儲存發文記錄
        
        Args:
            post_id: 貼文 ID
            content: 貼文內容
            topics: 貼文主題列表
            sentiment: 情感分析結果
            
        Returns:
            bool: 是否成功
        """
        try:
            # 準備文章資料
            post_data = {
                "post_id": post_id,
                "content": content,
                "topics": topics,
                "sentiment": sentiment,
                "created_at": datetime.now(self.timezone)
            }
            
            # 儲存文章
            result = await self.posts.insert_one(post_data)
            
            if result.inserted_id:
                self.logger.info(f"文章儲存成功，ID: {post_id}")
                
                # 更新主題使用時間
                update_ops = []
                for topic in topics:
                    update_ops.append(
                        UpdateOne(
                            {"topic": topic},
                            {
                                "$set": {"last_used": datetime.now(self.timezone)},
                                "$inc": {"usage_count": 1}
                            },
                            upsert=True
                        )
                    )
                
                if update_ops:
                    await self.post_topics.bulk_write(update_ops)
                    
                return True
            else:
                self.logger.error("文章儲存失敗")
                return False
                
        except Exception as e:
            self.logger.error(f"儲存貼文記錄失敗: {str(e)}")
            return False
            
    @with_retry(retries=3, delay=1)
    async def get_post(self, post_id: str) -> Optional[Dict[str, Any]]:
        """獲取貼文記錄
        
        Args:
            post_id: 貼文 ID
            
        Returns:
            Optional[Dict[str, Any]]: 貼文資料或 None
        """
        try:
            post = await self.posts.find_one({"post_id": post_id})
            if post:
                return {
                    "post_id": post["post_id"],
                    "content": post["content"],
                    "topics": post["topics"],
                    "sentiment": post["sentiment"],
                    "created_at": post["created_at"]
                }
            return None
        except Exception as e:
            self.logger.error(f"獲取貼文記錄失敗: {str(e)}")
            return None

    async def get_post_history(self, limit: int = 5) -> List[Dict]:
        """獲取貼文歷史"""
        try:
            cursor = self.posts.find(
                sort=[("timestamp", -1)],
                limit=limit
            )
            return await cursor.to_list(length=limit)
        except Exception as e:
            self.logger.error(f"獲取貼文歷史時發生錯誤：{str(e)}")
            return []

    async def has_replied_to_post(self, post_id: str) -> bool:
        """檢查是否已回覆過貼文"""
        try:
            count = await self.posts.count_documents({
                "post_id": post_id,
                "is_reply": True
            })
            return count > 0
        except Exception as e:
            logging.error(f"檢查貼文回覆狀態時發生錯誤：{str(e)}")
            return False

    async def get_user_interaction_summary(self, user_id: str) -> Dict:
        """獲取用戶互動摘要"""
        try:
            pipeline = [
                {"$match": {"user_id": user_id}},
                {"$group": {
                    "_id": None,
                    "interaction_count": {"$sum": 1},
                    "first_interaction": {"$min": "$timestamp"},
                    "last_interaction": {"$max": "$timestamp"}
                }}
            ]
            
            result = await self.conversations.aggregate(pipeline).to_list(length=1)
            if not result:
                return {
                    "interaction_count": 0,
                    "interaction_frequency": 0,
                    "first_interaction": None,
                    "last_interaction": None
                }
                
            summary = result[0]
            first_time = summary["first_interaction"]
            last_time = summary["last_interaction"]
            duration = (last_time - first_time).total_seconds()
            
            return {
                "interaction_count": summary["interaction_count"],
                "interaction_frequency": summary["interaction_count"] / duration if duration > 0 else 0,
                "first_interaction": first_time,
                "last_interaction": last_time
            }
        except Exception as e:
            logging.error(f"獲取用戶互動摘要時發生錯誤：{str(e)}")
            return {
                "interaction_count": 0,
                "interaction_frequency": 0,
                "first_interaction": None,
                "last_interaction": None
            }

    async def get_last_post_time(self) -> Optional[datetime]:
        """獲取最後一次發文時間"""
        try:
            last_post = await self.posts.find_one(
                sort=[("created_at", -1)]
            )
            return last_post["created_at"] if last_post else None
        except Exception as e:
            self.logger.error(f"獲取最後發文時間失敗: {str(e)}")
            return None

    async def update_last_post_time(self, timestamp: datetime) -> bool:
        """更新最後發文時間"""
        try:
            result = await self.posts.update_one(
                {"_id": "last_post_time"},
                {"$set": {"timestamp": timestamp}},
                upsert=True
            )
            return result.acknowledged
        except Exception as e:
            self.logger.error(f"更新最後發文時間失敗: {str(e)}")
            return False

    async def get_last_check_time(self) -> datetime:
        """獲取最後檢查時間"""
        try:
            last_check = await self.posts.find_one({"_id": "last_check_time"})
            return last_check["timestamp"] if last_check else None
        except Exception as e:
            self.logger.error(f"獲取最後檢查時間失敗: {str(e)}")
            return None

    async def update_last_check_time(self, timestamp: datetime) -> bool:
        """更新最後檢查時間"""
        try:
            result = await self.posts.update_one(
                {"_id": "last_check_time"},
                {"$set": {"timestamp": timestamp}},
                upsert=True
            )
            return result.acknowledged
        except Exception as e:
            self.logger.error(f"更新最後檢查時間失敗: {str(e)}")
            return False

    async def save_reply(self, reply_id: str, post_id: str, content: str, username: str) -> bool:
        """儲存回覆記錄"""
        try:
            result = await self.replies.insert_one({
                "reply_id": reply_id,
                "post_id": post_id,
                "content": content,
                "username": username,
                "created_at": datetime.now(self.timezone),
                "is_processed": False
            })
            self.logger.info(f"已儲存回覆記錄，ID: {reply_id}")
            return True
        except Exception as e:
            self.logger.error(f"儲存回覆記錄失敗: {str(e)}")
            return False

    async def add_interaction(self, user_id: str, content: str, is_bot: bool) -> bool:
        """添加互動記錄
        
        Args:
            user_id: 用戶 ID
            content: 互動內容
            is_bot: 是否為機器人的回應
            
        Returns:
            bool: 是否成功
        """
        try:
            interaction = {
                "user_id": user_id,
                "content": content,
                "is_bot": is_bot,
                "timestamp": datetime.utcnow()
            }
            await self.conversations.insert_one(interaction)
            return True
        except Exception as e:
            self.logger.error(f"添加互動記錄失敗：{str(e)}")
            return False
            
    async def get_user_interactions(self, user_id: str, limit: int = 10) -> List[Dict]:
        """獲取用戶互動記錄
        
        Args:
            user_id: 用戶 ID
            limit: 記錄數量限制
            
        Returns:
            List[Dict]: 互動記錄列表
        """
        try:
            cursor = self.conversations.find(
                {"user_id": user_id}
            ).sort("timestamp", -1).limit(limit)
            
            interactions = []
            async for doc in cursor:
                interactions.append(doc)
            return interactions
        except Exception as e:
            self.logger.error(f"獲取用戶互動記錄失敗：{str(e)}")
            return []
            
    async def cleanup_old_records(self, days: int = 30) -> bool:
        """清理舊記錄"""
        try:
            cutoff = datetime.now(self.timezone) - timedelta(days=days)
            
            # 清理舊貼文
            posts_result = await self.posts.delete_many({
                "created_at": {"$lt": cutoff}
            })
            
            # 清理舊回覆
            replies_result = await self.replies.delete_many({
                "created_at": {"$lt": cutoff}
            })
            
            self.logger.info(f"已清理 {posts_result.deleted_count} 條舊貼文和 {replies_result.deleted_count} 條舊回覆")
            return True
        except Exception as e:
            self.logger.error(f"清理舊記錄失敗: {str(e)}")
            return False

    @with_retry()
    async def get_unprocessed_replies(self) -> List[Dict]:
        """獲取未處理的回覆（使用批量查詢）"""
        try:
            cursor = self.replies.find(
                {"is_processed": False},
                projection={
                    "reply_id": 1,
                    "post_id": 1,
                    "content": 1,
                    "username": 1,
                    "created_at": 1,
                    "_id": 0
                }
            ).sort("created_at", 1).limit(50)  # 限制批次處理數量
            
            return await cursor.to_list(length=50)
        except Exception as e:
            self.logger.error(f"獲取未處理回覆失敗: {str(e)}")
            return []

    @with_retry()
    async def mark_replies_processed(self, reply_ids: List[str]) -> bool:
        """批量標記回覆為已處理"""
        if not reply_ids:
            return True
            
        try:
            result = await self.replies.update_many(
                {"reply_id": {"$in": reply_ids}},
                {"$set": {"is_processed": True}}
            )
            return result.modified_count == len(reply_ids)
        except Exception as e:
            self.logger.error(f"批量標記回覆狀態失敗: {str(e)}")
            return False

    @with_retry()
    async def get_user_reply_history(self, username: str, limit: int = 10) -> List[Dict]:
        """獲取用戶回覆歷史（使用快取）"""
        cache_key = f"reply_history:{username}"
        
        # 檢查快取
        if cache_key in self._cache:
            cache_time, cache_data = self._cache[cache_key]
            if (datetime.now() - cache_time).total_seconds() < self._cache_timeout:
                return cache_data
        
        try:
            cursor = self.replies.find(
                {"username": username},
                projection={
                    "content": 1,
                    "created_at": 1,
                    "post_id": 1,
                    "_id": 0
                }
            ).sort("created_at", -1).limit(limit)
            
            history = await cursor.to_list(length=limit)
            
            # 更新快取
            self._cache[cache_key] = (datetime.now(), history)
            
            return history
        except Exception as e:
            self.logger.error(f"獲取用戶回覆歷史失敗: {str(e)}")
            return []

    async def cleanup_cache(self):
        """清理過期快取"""
        current_time = datetime.now()
        expired_keys = [
            key for key, (cache_time, _) in self._cache.items()
            if (current_time - cache_time).total_seconds() > self._cache_timeout
        ]
        for key in expired_keys:
            del self._cache[key]

    async def save_setting(self, key: str, value: Any) -> bool:
        """儲存系統設定"""
        try:
            result = await self.settings.update_one(
                {"key": key},
                {"$set": {"value": value}},
                upsert=True
            )
            self.logger.info(f"已儲存系統設定: {key}")
            return True
        except Exception as e:
            self.logger.error(f"儲存系統設定失敗: {str(e)}")
            return False

    async def get_setting(self, key: str, default: Any = None) -> Any:
        """獲取系統設定"""
        try:
            doc = await self.settings.find_one({"key": key})
            return doc["value"] if doc else default
        except Exception as e:
            self.logger.error(f"獲取系統設定失敗: {str(e)}")
            return default

    async def extract_topics(self, content: str) -> List[str]:
        """從文章內容中提取主題"""
        topics = []
        keywords = self.config.KEYWORDS
        
        # 檢查興趣相關關鍵字
        for interest in keywords["興趣"]:
            if interest in content:
                topics.append(interest)
                
        # 檢查情緒相關關鍵字
        for emotion in keywords["情緒"]:
            if emotion in content:
                topics.append(f"情緒_{emotion}")
                
        # 檢查回應相關關鍵字
        for response in keywords["回應"]:
            if response in content:
                topics.append(f"回應_{response}")
                
        return list(set(topics))  # 去重

    async def get_recent_topics(self, limit: int = 5) -> List[str]:
        """獲取最近使用的主題"""
        try:
            cursor = self.post_topics.find(
                sort=[("last_used", -1)],
                limit=limit
            )
            topics = await cursor.to_list(length=limit)
            return [topic["topic"] for topic in topics]
        except Exception as e:
            self.logger.error(f"獲取最近主題失敗: {str(e)}")
            return []

    async def get_similar_posts(self, content: str, limit: int = 3) -> List[Dict]:
        """獲取相似的歷史貼文"""
        try:
            # 提取當前內容的主題
            current_topics = await self.extract_topics(content)
            
            if not current_topics:
                return []
            
            # 使用主題和全文搜索找相似貼文
            cursor = self.posts.find(
                {
                    "topics": {"$in": current_topics},
                    "created_at": {
                        "$gte": datetime.now(self.timezone) - timedelta(days=7)
                    }
                },
                sort=[("created_at", -1)],
                limit=limit
            )
            
            return await cursor.to_list(length=limit)
        except Exception as e:
            self.logger.error(f"獲取相似貼文失敗: {str(e)}")
            return []

    async def is_content_similar(self, content: str) -> bool:
        """檢查內容是否與最近的貼文過於相似"""
        try:
            # 獲取最近24小時內的貼文
            recent_posts = await self.posts.find({
                "created_at": {
                    "$gte": datetime.now(self.timezone) - timedelta(hours=24)
                }
            }).to_list(length=10)
            
            # 提取當前內容的主題
            current_topics = await self.extract_topics(content)
            
            for post in recent_posts:
                # 檢查主題重疊度
                post_topics = post.get("topics", [])
                common_topics = set(current_topics) & set(post_topics)
                
                # 如果主題重疊超過50%，認為內容過於相似
                if len(common_topics) >= len(current_topics) * 0.5:
                    return True
                    
                # 檢查內容相似度（簡單的文字匹配）
                if len(content) > 0 and len(post["content"]) > 0:
                    # 計算重疊字符比例
                    common_chars = sum(1 for c in content if c in post["content"])
                    similarity = common_chars / len(content)
                    if similarity > 0.6:  # 如果相似度超過60%
                        return True
                        
            return False
        except Exception as e:
            self.logger.error(f"檢查內容相似度失敗: {str(e)}")
            return False

    async def get_topic_suggestions(self) -> List[str]:
        """獲取建議的主題"""
        try:
            # 獲取最近較少使用的主題
            current_time = datetime.now(self.timezone)
            cursor = self.post_topics.find({
                "last_used": {
                    "$lte": current_time - timedelta(hours=12)
                }
            }).sort([
                ("use_count", 1),
                ("last_used", 1)
            ]).limit(5)
            
            topics = await cursor.to_list(length=5)
            return [topic["topic"] for topic in topics]
        except Exception as e:
            self.logger.error(f"獲取主題建議失敗: {str(e)}")
            return []

    async def get_recent_posts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """獲取最近的貼文
        
        Args:
            limit: 返回的貼文數量限制
            
        Returns:
            List[Dict]: 最近的貼文列表
        """
        try:
            posts = []
            cursor = self.db.posts.find().sort('created_at', -1).limit(limit)
            async for post in cursor:
                posts.append({
                    'id': str(post['_id']),
                    'content': post['content'],
                    'created_at': post['created_at']
                })
            return posts
        except Exception as e:
            self.logger.error(f"獲取最近貼文失敗: {str(e)}")
            return []

    async def check_daily_post_limit(self) -> bool:
        """檢查是否達到每日發文上限
        
        Returns:
            bool: True 表示已達到上限，False 表示未達到上限
        """
        try:
            # 獲取今日開始時間（台北時區）
            tz = timezone(timedelta(hours=8))
            today = datetime.now(tz).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            
            # 查詢今日發文數量
            count = await self.posts.count_documents({
                "created_at": {"$gte": today}
            })
            
            # 檢查是否達到上限（預設為 10 篇）
            limit_reached = count >= 10
            if limit_reached:
                self.logger.info(f"今日已發布 {count} 篇文章，達到上限")
            else:
                self.logger.debug(f"今日已發布 {count} 篇文章")
            return limit_reached
            
        except Exception as e:
            self.logger.error(f"檢查每日發文限制時發生錯誤: {e}")
            return True  # 發生錯誤時，為安全起見返回已達上限