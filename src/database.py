"""
ThreadsPoster 資料庫處理模組
處理與 MongoDB 的所有互動
"""

import logging
import pytz
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError
from src.config import Config
from src.exceptions import DatabaseError

logger = logging.getLogger(__name__)

class Database:
    """資料庫類別"""
    def __init__(self, config, test_mode: bool = False):
        """初始化資料庫連接
        
        Args:
            config: 設定物件
            test_mode: 是否為測試模式
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._client = None
        self._db = None
        self._conversations = None
        self._posts = None
        self._users = None
        self._system = None
        self._test_mode = test_mode
        self.timezone = config.TIMEZONE
        if not test_mode:
            self.connect()

    def connect(self):
        """連接到 MongoDB 資料庫"""
        if self._client is None:
            try:
                if self._test_mode:
                    import mongomock
                    self._client = mongomock.MongoClient()
                else:
                    self._client = AsyncIOMotorClient(self.config.MONGODB_URI)
                    
                self._db = self._client[self.config.MONGODB_DB_NAME]
                
                # 初始化集合
                self._conversations = self._db.conversations
                self._posts = self._db.posts
                self._users = self._db.users
                self._system = self._db.system
                
                self.logger.info("成功連接到 MongoDB")
            except Exception as e:
                self.logger.error(f"連接 MongoDB 失敗: {str(e)}")
                if not self._test_mode:
                    raise DatabaseError("無法連接到資料庫")

    @property
    def client(self):
        """獲取資料庫客戶端"""
        return self._client
    
    @client.setter
    def client(self, value):
        """設置資料庫客戶端"""
        self._client = value
    
    @property
    def db(self):
        """獲取資料庫實例"""
        return self._db
    
    @db.setter
    def db(self, value):
        """設置資料庫實例"""
        self._db = value
    
    @property
    def conversations(self):
        """獲取對話集合"""
        if self._db is None:
            return None
        return self._db.conversations
    
    @conversations.setter
    def conversations(self, value):
        """設置對話集合"""
        if self._db is not None:
            self._db.conversations = value
    
    @property
    def posts(self):
        """獲取貼文集合"""
        if self._db is None:
            return None
        return self._db.posts
    
    @posts.setter
    def posts(self, value):
        """設置貼文集合"""
        if self._db is not None:
            self._db.posts = value

    @property
    def users_collection(self):
        """獲取用戶集合"""
        return self._users

    def _ensure_timezone(self, dt: Optional[datetime]) -> Optional[datetime]:
        """確保時間有正確的時區資訊
        
        Args:
            dt: 時間物件
            
        Returns:
            datetime: 帶有時區資訊的時間物件
        """
        if dt is None:
            return None
            
        if dt.tzinfo is None:
            return self.timezone.localize(dt)
        return dt.astimezone(self.timezone)

    async def get_user_history(self, user_id):
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
            raise Exception(f"獲取用戶歷史記錄時發生錯誤: {str(e)}")
            
    async def update_user_history(self, user_id: str, message: str, response: str) -> bool:
        """更新用戶的對話歷史

        Args:
            user_id (str): 用戶ID
            message (str): 用戶的訊息
            response (str): 系統的回應

        Returns:
            bool: 更新是否成功
        """
        try:
            conversation = {
                "message": message,
                "response": response,
                "timestamp": self._ensure_timezone(datetime.now())
            }
            
            result = await self._users.update_one(
                {"user_id": user_id},
                {
                    "$push": {"conversations": conversation},
                    "$set": {"last_updated": self._ensure_timezone(datetime.now())}
                },
                upsert=True
            )
            
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            self.logger.error(f"更新用戶歷史時發生錯誤: {str(e)}")
            return False
            
    async def _cleanup_old_conversations(self, user_id):
        """清理過期的對話記錄"""
        try:
            cutoff_date = self._ensure_timezone(
                datetime.now() - timedelta(days=self.config.MEMORY_CONFIG['retention_days'])
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
            raise Exception(f"清理過期對話記錄時發生錯誤: {str(e)}")
            
    async def get_conversation_summary(self, user_id):
        """獲取對話摘要用於 AI 生成"""
        try:
            history = await self.get_user_history(user_id)
            if not history:
                return []
                
            conversations = history.get("conversations", [])
            # 只返回最近的 5 筆對話
            return conversations[-5:]
            
        except Exception as e:
            self.logger.error(f"獲取對話摘要時發生錯誤: {str(e)}")
            return []
            
    async def save_conversation(self, user_id: str, message: str, response: str):
        """儲存對話記錄"""
        try:
            conversation = {
                "message": message,
                "response": response,
                "timestamp": datetime.now(pytz.UTC)
            }
            
            await self.conversations.update_one(
                {"user_id": user_id},
                {
                    "$push": {"conversations": conversation},
                    "$set": {"last_interaction": datetime.now(pytz.UTC)}
                },
                upsert=True
            )
            
        except Exception as e:
            self.logger.error(f"儲存對話記錄時發生錯誤: {str(e)}")
            
    async def get_user_conversation_history(self, user_id: str) -> List[Dict[str, Any]]:
        """獲取用戶的對話歷史

        Args:
            user_id (str): 用戶ID

        Returns:
            List[Dict[str, Any]]: 對話歷史列表
        """
        try:
            history = await self.get_user_history(user_id)
            return history.get("conversations", [])
        except Exception as e:
            self.logger.error(f"獲取用戶對話歷史時發生錯誤: {str(e)}")
            return []
            
    async def save_post(self, post_id: str, content: str, post_type: str, reply_to: str = None):
        """儲存貼文"""
        try:
            post_data = {
                "post_id": post_id,
                "content": content,
                "type": post_type,
                "reply_to": reply_to,
                "created_at": datetime.now(pytz.UTC)
            }
            
            await self.posts.insert_one(post_data)
            
        except Exception as e:
            self.logger.error(f"儲存貼文時發生錯誤: {str(e)}")
            
    async def get_post_history(self, limit: int = 5) -> List[Dict]:
        """獲取貼文歷史"""
        try:
            cursor = self.posts.find().sort("created_at", -1).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            self.logger.error(f"獲取貼文歷史時發生錯誤: {str(e)}")
            return []
            
    async def has_replied_to_post(self, post_id: str) -> bool:
        """檢查是否已經回覆過貼文"""
        try:
            count = await self.posts.count_documents({
                "reply_to": post_id
            })
            return count > 0
        except Exception as e:
            self.logger.error(f"檢查貼文回覆時發生錯誤: {str(e)}")
            return False
            
    async def get_user_interaction_summary(self, user_id: str) -> Dict:
        """獲取用戶互動摘要"""
        try:
            user_data = await self._users.find_one({"user_id": user_id})
            if not user_data:
                return {
                    "total_interactions": 0,
                    "last_interaction": None,
                    "common_topics": [],
                    "sentiment": "neutral"
                }
                
            conversations = user_data.get("conversations", [])
            
            return {
                "total_interactions": len(conversations),
                "last_interaction": user_data.get("last_updated"),
                "common_topics": self._extract_topics(conversations),
                "sentiment": self._analyze_sentiment(conversations)
            }
            
        except Exception as e:
            self.logger.error(f"獲取用戶互動摘要時發生錯誤: {str(e)}")
            return {
                "total_interactions": 0,
                "last_interaction": None,
                "common_topics": [],
                "sentiment": "neutral"
            }
            
    def _extract_topics(self, conversations: List[Dict]) -> List[str]:
        """從對話中提取主題"""
        # TODO: 實作主題提取邏輯
        return []
        
    def _analyze_sentiment(self, conversations: List[Dict]) -> str:
        """分析對話情感"""
        # TODO: 實作情感分析邏輯
        return "neutral"
        
    async def save_reply(self, reply_data: Dict) -> bool:
        """儲存回覆"""
        try:
            await self.posts.insert_one({
                **reply_data,
                "created_at": datetime.now(pytz.UTC)
            })
            return True
        except Exception as e:
            self.logger.error(f"儲存回覆時發生錯誤: {str(e)}")
            return False
            
    async def get_last_post_time(self) -> Optional[datetime]:
        """獲取最後發文時間"""
        try:
            system_info = await self._system.find_one({"_id": "system_info"})
            if not system_info or "last_post_time" not in system_info:
                return None
            return self._ensure_timezone(system_info["last_post_time"])
        except Exception as e:
            self.logger.error(f"獲取最後發文時間時發生錯誤: {str(e)}")
            return None
            
    async def update_last_post_time(self, time: datetime):
        """更新最後發文時間
        
        Args:
            time: 時間
        """
        try:
            time = self._ensure_timezone(time)
            await self._system.update_one(
                {"_id": "system_info"},
                {"$set": {"last_post_time": time}},
                upsert=True
            )
        except Exception as e:
            self.logger.error(f"更新最後發文時間時發生錯誤: {str(e)}")
            
    async def get_last_check_time(self) -> Optional[datetime]:
        """獲取最後檢查時間"""
        try:
            system_info = await self._system.find_one({"_id": "system_info"})
            if not system_info or "last_check_time" not in system_info:
                return None
            return self._ensure_timezone(system_info["last_check_time"])
        except Exception as e:
            self.logger.error(f"獲取最後檢查時間時發生錯誤: {str(e)}")
            return None
            
    async def update_last_check_time(self, time: datetime):
        """更新最後檢查時間
        
        Args:
            time: 時間
        """
        try:
            time = self._ensure_timezone(time)
            await self._system.update_one(
                {"_id": "system_info"},
                {"$set": {"last_check_time": time}},
                upsert=True
            )
        except Exception as e:
            self.logger.error(f"更新最後檢查時間時發生錯誤: {str(e)}")
            
    async def close(self):
        """關閉資料庫連接"""
        if self._client:
            await self._client.close()