"""
共享測試夾具
"""

import pytest
from unittest.mock import Mock, AsyncMock
import mongomock
import pytz
from datetime import datetime
from src.config import Config
from src.ai_handler import AIHandler
from src.database import Database
from src.threads_api import ThreadsAPI

@pytest.fixture
def config():
    """建立測試用設定"""
    config = Config()
    # 覆寫設定值以供測試使用
    config.MONGODB_URI = "mongodb://localhost:27017"
    config.MONGODB_DB_NAME = "test_db"
    config.MONGODB_COLLECTION = "test_collection"
    config.CHECK_INTERVAL = 1
    config.ERROR_WAIT_TIME = 1
    config.MAX_RETRIES = 2
    return config

@pytest.fixture
def mock_mongo_client():
    """建立模擬 MongoDB 客戶端"""
    return mongomock.MongoClient()

@pytest.fixture
def mock_openai_response():
    """建立模擬 OpenAI 回應"""
    mock = Mock()
    mock.choices = [Mock(message=Mock(content="測試回應"))]
    return mock

@pytest.fixture
def mock_threads_response():
    """建立模擬 Threads API 回應"""
    mock = AsyncMock()
    mock.status = 200
    mock.json.return_value = {"success": True}
    return mock

@pytest.fixture
def mock_db(config):
    """建立模擬資料庫"""
    # 初始化資料庫實例（測試模式）
    database = Database(config, test_mode=True)
    database.connect()
    
    # 預先插入測試資料
    current_time = datetime.now(pytz.UTC)
    
    # 插入對話資料
    conversations_data = [
        {
            "user_id": "test_user",
            "message": "測試訊息1",
            "response": "測試回應1",
            "timestamp": current_time
        },
        {
            "user_id": "test_user",
            "message": "測試訊息2",
            "response": "測試回應2",
            "timestamp": current_time
        }
    ]
    database.conversations.insert_many(conversations_data)
    
    # 插入貼文資料
    posts_data = [
        {
            "post_id": "post1",
            "content": "測試貼文1",
            "post_type": "post",
            "timestamp": current_time
        },
        {
            "post_id": "reply1",
            "content": "測試回覆1",
            "post_type": "reply",
            "reference_id": "post1",
            "timestamp": current_time
        }
    ]
    database.posts.insert_many(posts_data)
    
    return database

@pytest.fixture
def mock_ai_handler(config):
    """建立模擬 AI 處理器"""
    ai_handler = AIHandler(config)
    return ai_handler

@pytest.fixture
def mock_threads_api(config):
    """建立模擬 Threads API 處理器"""
    threads_api = ThreadsAPI(config)
    return threads_api

@pytest.fixture
def sample_conversation_history():
    """建立範例對話歷史"""
    return [
        {
            "message": "你好啊",
            "response": "哈囉！",
            "timestamp": datetime.now(pytz.UTC)
        },
        {
            "message": "今天天氣真好",
            "response": "是啊，適合出門玩",
            "timestamp": datetime.now(pytz.UTC)
        }
    ]

@pytest.fixture
def sample_threads_replies():
    """建立範例 Threads 回覆"""
    return [
        {
            "id": "123",
            "username": "test_user",
            "text": "測試回覆1",
            "created_at": datetime.now(pytz.UTC).isoformat()
        },
        {
            "id": "456",
            "username": "test_user2",
            "text": "測試回覆2",
            "created_at": datetime.now(pytz.UTC).isoformat()
        }
    ]

@pytest.fixture
def error_responses():
    """建立錯誤回應範例"""
    return {
        "rate_limit": {
            "status": 429,
            "json": {"error": "Too Many Requests"}
        },
        "auth_error": {
            "status": 401,
            "json": {"error": "Unauthorized"}
        },
        "server_error": {
            "status": 500,
            "json": {"error": "Internal Server Error"}
        }
    } 