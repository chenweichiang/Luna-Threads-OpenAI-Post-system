"""
共享測試夾具
"""

import pytest
from unittest.mock import Mock, AsyncMock
import mongomock_motor
import pytz
from datetime import datetime
from src.config import Config
from src.ai_handler import AIHandler
from src.database import Database
from src.threads_api import ThreadsAPI
import os
import logging
from pathlib import Path

@pytest.fixture
def config():
    """測試用設定"""
    return Config(
        MONGODB_URI="mongodb://localhost:27017",
        MONGODB_DB_NAME="test_db",
        MONGODB_COLLECTION="test_conversations",
        SYSTEM_CONFIG={
            'timezone': 'Asia/Taipei',
            'log_level': 'DEBUG'
        },
        MEMORY_CONFIG={
            'max_history': 10,
            'retention_days': 7
        },
        skip_validation=True
    )

@pytest.fixture
def database(config):
    """測試用資料庫"""
    db = Database(config, is_test=True)
    return db

@pytest.fixture
def ai_handler(database):
    """測試用 AI 處理器"""
    handler = AIHandler(database)
    return handler

@pytest.fixture
def threads_api(config):
    """建立測試用 Threads API 客戶端"""
    api = ThreadsAPI(config)
    return api

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
async def mock_db(database):
    """預先填充測試資料的資料庫"""
    # 插入測試對話記錄
    conversation = {
        "user_id": "test_user",
        "conversations": [
            {
                "timestamp": datetime.now(pytz.timezone('Asia/Taipei')),
                "reply": "你好啊",
                "response": "哈囉！"
            }
        ],
        "last_interaction": datetime.now(pytz.timezone('Asia/Taipei'))
    }
    await database.conversations.insert_one(conversation)
    
    # 插入測試貼文
    post = {
        "post_id": "test_post_1",
        "content": "測試貼文",
        "user_id": "test_user",
        "is_reply": False,
        "timestamp": datetime.now(pytz.timezone('Asia/Taipei'))
    }
    await database.posts.insert_one(post)
    
    return database

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

def pytest_configure(config):
    """配置測試環境"""
    # 設定測試環境變數
    os.environ["OPENAI_API_KEY"] = "test_api_key"
    os.environ["THREADS_ACCESS_TOKEN"] = "test_access_token"
    os.environ["THREADS_APP_ID"] = "test_app_id"
    os.environ["THREADS_APP_SECRET"] = "test_app_secret"
    os.environ["TIMEZONE"] = "Asia/Taipei"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    # 設定測試日誌
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 創建測試目錄
    Path("tests/data").mkdir(parents=True, exist_ok=True)
    Path("tests/logs").mkdir(parents=True, exist_ok=True)

@pytest.fixture(autouse=True)
async def setup_test_env():
    """設置測試環境"""
    # 設置日誌級別
    logging.basicConfig(level=logging.DEBUG)
    
    # 設置測試環境變數
    os.environ['OPENAI_API_KEY'] = 'test_key'
    os.environ['THREADS_APP_ID'] = 'test_app_id'
    os.environ['THREADS_APP_SECRET'] = 'test_app_secret'
    os.environ['THREADS_ACCESS_TOKEN'] = 'test_access_token'
    yield
    # 測試結束後的清理工作

def cleanup_test_files():
    """清理測試檔案"""
    test_files = [
        "tests/data/test_memory.json",
        "tests/logs/test_metrics.json"
    ]
    
    for file_path in test_files:
        try:
            Path(file_path).unlink(missing_ok=True)
        except Exception as e:
            logging.warning(f"清理測試檔案失敗：{str(e)}")

@pytest.fixture
def test_data():
    """測試資料夾具"""
    return {
        "user_id": "test_user",
        "text": "測試訊息",
        "topics": ["ACG", "BL"],
        "sentiment": {
            "positive": 0.6,
            "negative": 0.1,
            "neutral": 0.3
        }
    }

@pytest.fixture
def test_config():
    """測試配置夾具"""
    return {
        "memory": {
            "retention_days": 7,
            "max_records": 50,
            "summary_length": 3
        },
        "character": {
            "name": "測試角色",
            "age": 25,
            "gender": "女性",
            "interests": ["測試"],
            "personality": ["活潑"]
        },
        "api": {
            "max_retries": 3,
            "timeout": 30,
            "batch_size": 10
        }
    } 