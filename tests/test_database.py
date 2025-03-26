"""資料庫模組測試"""

import unittest
import mongomock
import pytz
from datetime import datetime
from unittest.mock import Mock, patch
from src.database import Database
from src.config import Config
import pytest

class TestDatabase(unittest.TestCase):
    """資料庫測試類"""

    def setUp(self):
        """設置測試環境"""
        self.config = Config()
        self.mock_client = mongomock.MongoClient()
        self.mock_db = self.mock_client[self.config.MONGODB_DB_NAME]
        
        # 設置資料庫實例
        self.db = Database(self.config)
        self.db.client = self.mock_client
        self.db.db = self.mock_db
        self.db.conversations = self.mock_db.conversations
        self.db.posts = self.mock_db.posts

    def test_save_conversation(self):
        """測試保存對話功能"""
        # 準備測試數據
        user_id = "test_user"
        message = "test message"
        response = "test response"

        # 執行測試
        self.db.save_conversation(user_id, message, response)

        # 驗證結果
        saved_conversation = self.mock_db.conversations.find_one({
            "user_id": user_id,
            "message": message,
            "response": response
        })
        self.assertIsNotNone(saved_conversation)

    @pytest.mark.asyncio
    async def test_get_user_conversation_history(self):
        """測試獲取用戶對話歷史功能"""
        # 準備測試數據
        user_id = "test_user"
        test_data = [
            {
                "user_id": user_id,
                "message": "msg1",
                "response": "resp1",
                "timestamp": datetime.now(pytz.UTC)
            },
            {
                "user_id": user_id,
                "message": "msg2",
                "response": "resp2",
                "timestamp": datetime.now(pytz.UTC)
            }
        ]
        self.mock_db.conversations.insert_many(test_data)

        # 執行測試
        result = await self.db.get_user_conversation_history(user_id)

        # 驗證結果
        assert len(result) == 2
        assert result[0]["message"] == "msg1"
        assert result[1]["message"] == "msg2"

    def test_save_post(self):
        """測試保存貼文功能"""
        # 準備測試數據
        post_id = "test_post"
        content = "test content"
        post_type = "post"
        reference_id = None

        # 執行測試
        self.db.save_post(post_id, content, post_type, reference_id)

        # 驗證結果
        saved_post = self.mock_db.posts.find_one({"post_id": post_id})
        self.assertIsNotNone(saved_post)
        self.assertEqual(saved_post["content"], content)

    def test_has_replied_to_post(self):
        """測試檢查貼文回覆狀態功能"""
        # 準備測試數據
        post_id = "test_post"
        self.mock_db.posts.insert_one({
            "post_id": "reply1",
            "content": "test reply",
            "post_type": "reply",
            "reference_id": post_id,
            "timestamp": datetime.now(pytz.UTC)
        })

        # 執行測試
        result = self.db.has_replied_to_post(post_id)

        # 驗證結果
        self.assertTrue(result)

    def test_get_user_interaction_summary(self):
        """測試獲取用戶互動摘要"""
        # 準備測試數據
        user_id = "test_user"
        timestamp1 = datetime(2024, 1, 1, 12, 0, tzinfo=pytz.UTC)
        timestamp2 = datetime(2024, 1, 2, 12, 0, tzinfo=pytz.UTC)
        
        # 插入測試對話
        self.db.conversations.insert_many([
            {
                "user_id": user_id,
                "message": "測試訊息1",
                "timestamp": timestamp1,
                "response": "測試回應1"
            },
            {
                "user_id": user_id,
                "message": "測試訊息2", 
                "timestamp": timestamp2,
                "response": "測試回應2"
            }
        ])
        
        # 獲取互動摘要
        summary = self.db.get_user_interaction_summary(user_id)
        
        # 驗證結果
        assert summary["user_id"] == user_id
        assert summary["total_interactions"] == 2
        assert summary["last_interaction"].replace(tzinfo=pytz.UTC) == timestamp2

if __name__ == '__main__':
    unittest.main()