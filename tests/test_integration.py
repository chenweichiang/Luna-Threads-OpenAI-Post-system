"""
ThreadsPoster 整合測試
測試整個系統的功能整合
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock
import pytz
from datetime import datetime, timedelta
from src.main import ThreadsPoster
import asyncio

from src.config import Config
from src.threads_api import ThreadsAPI
from src.database import Database
from src.ai_handler import AIHandler

@pytest_asyncio.fixture
async def mock_ai_handler():
    """模擬 AI 處理器"""
    handler = AsyncMock(spec=AIHandler)
    handler.character_profile = {
        "基本資料": {
            "年齡": 28,
            "性別": "女性",
            "國籍": "台灣",
            "興趣": ["ACG文化", "電腦科技", "BL作品"],
            "個性特徵": ["喜歡說曖昧的話", "了解科技", "善於互動"]
        },
        "回文規則": {
            "字數限制": "不超過20個字，以短句回覆",
            "時間規律": {
                "白天": "1-5分鐘內回覆",
                "深夜": "5-30分鐘或不回覆"
            }
        }
    }
    return handler

@pytest_asyncio.fixture
async def mock_threads_api():
    """模擬 Threads API"""
    api = AsyncMock(spec=ThreadsAPI)
    api.base_url = "https://api.threads.net/v1"
    api.headers = {
        "Authorization": "Bearer test_token",
        "Content-Type": "application/json"
    }
    return api

@pytest_asyncio.fixture
async def mock_db():
    """模擬資料庫"""
    db = AsyncMock(spec=Database)
    db.is_connected = True
    db._db = MagicMock()
    db._users = db._db.users
    return db

@pytest.fixture
def sample_threads_replies():
    """測試用的回覆資料"""
    return [
        {
            "id": "123",
            "username": "test_user",
            "text": "測試訊息",
            "created_at": datetime.now(pytz.UTC).isoformat()
        }
    ]

@pytest.fixture
def error_responses():
    """測試用的錯誤回應"""
    return {
        "rate_limit": {"status": 429, "json": {"error": "rate limit"}},
        "server_error": {"status": 500, "json": {"error": "server error"}}
    }

@pytest.mark.asyncio
async def test_full_reply_flow(mock_ai_handler, mock_threads_api, mock_db, sample_threads_replies):
    """測試完整的回覆流程"""
    bot = ThreadsPoster()
    bot._test_mode = True
    bot.ai_handler = mock_ai_handler
    bot.threads_api = mock_threads_api
    bot.db = mock_db

    # 模擬取得新回覆
    mock_threads_api.get_new_replies = AsyncMock(return_value=sample_threads_replies)
    mock_ai_handler.generate_response = AsyncMock(return_value="測試回應")
    mock_threads_api.reply_to_post = AsyncMock(return_value=True)
    mock_db.get_user_conversation_history = AsyncMock(return_value=[])
    mock_db.update_user_history = AsyncMock(return_value=True)

    await bot.process_new_replies()

    # 驗證資料庫更新
    mock_db.update_user_history.assert_called_once()
    mock_threads_api.reply_to_post.assert_called_once()

@pytest.mark.asyncio
async def test_new_post_generation(mock_ai_handler, mock_threads_api, mock_db):
    """測試新貼文生成流程"""
    bot = ThreadsPoster()
    bot._test_mode = True
    bot.ai_handler = mock_ai_handler
    bot.threads_api = mock_threads_api
    bot.db = mock_db

    # 設定最後發文時間為3小時前
    bot.last_post_time = datetime.now(pytz.UTC) - timedelta(hours=3)

    # 模擬 AI 生成貼文
    mock_ai_handler.generate_new_post = AsyncMock(return_value="新的測試貼文")
    mock_threads_api.create_post = AsyncMock(return_value=True)

    await bot.generate_new_post()
    
    # 驗證最後發文時間已更新
    assert (datetime.now(pytz.UTC) - bot.last_post_time).total_seconds() < 60
    mock_threads_api.create_post.assert_called_once_with("新的測試貼文")

@pytest.mark.asyncio
async def test_error_recovery(mock_ai_handler, mock_threads_api, mock_db):
    """測試錯誤恢復流程"""
    bot = ThreadsPoster()
    bot._test_mode = True
    bot.ai_handler = mock_ai_handler
    bot.threads_api = mock_threads_api
    bot.db = mock_db

    # 模擬連續的 API 錯誤後成功
    mock_threads_api.create_post = AsyncMock(side_effect=[False, False, True])
    mock_ai_handler.generate_new_post = AsyncMock(return_value="測試貼文")

    await bot.generate_new_post()
    
    # 驗證重試次數和最終成功
    assert mock_threads_api.create_post.call_count == 3
    assert bot.last_post_time is not None

@pytest.mark.asyncio
async def test_concurrent_operations(mock_ai_handler, mock_threads_api, mock_db, sample_threads_replies):
    """測試並發操作"""
    bot = ThreadsPoster()
    bot._test_mode = True
    bot.ai_handler = mock_ai_handler
    bot.threads_api = mock_threads_api
    bot.db = mock_db

    # 模擬 API 回應
    mock_threads_api.get_new_replies = AsyncMock(return_value=sample_threads_replies)
    mock_ai_handler.generate_response = AsyncMock(return_value="測試回應")
    mock_threads_api.reply_to_post = AsyncMock(return_value=True)
    mock_threads_api.create_post = AsyncMock(return_value=True)
    mock_ai_handler.generate_new_post = AsyncMock(return_value="新貼文")
    mock_db.update_user_history = AsyncMock(return_value=True)

    # 同時執行多個操作
    await asyncio.gather(
        bot.process_new_replies(),
        bot.generate_new_post()
    )

    # 驗證所有操作都被執行
    mock_threads_api.reply_to_post.assert_called_once()
    mock_threads_api.create_post.assert_called_once()
    mock_db.update_user_history.assert_called_once()

@pytest.mark.asyncio
async def test_memory_system(mock_ai_handler, mock_threads_api, mock_db):
    """測試記憶系統"""
    bot = ThreadsPoster()
    bot._test_mode = True
    bot.ai_handler = mock_ai_handler
    bot.threads_api = mock_threads_api
    bot.db = mock_db

    user_id = "test_user"
    
    # 模擬歷史對話
    mock_db.get_user_conversation_history = AsyncMock(return_value=[
        {
            "message": "你還記得我們之前聊什麼嗎",
            "response": "記得，我們聊到天氣",
            "timestamp": datetime.now(pytz.UTC)
        }
    ])
    
    # 模擬新的對話
    mock_threads_api.get_new_replies = AsyncMock(return_value=[{
        "id": "789",
        "username": user_id,
        "text": "對啊，那天天氣真好",
        "created_at": datetime.now(pytz.UTC).isoformat()
    }])
    
    mock_ai_handler.generate_response = AsyncMock(return_value="是的，那天陽光普照")
    mock_threads_api.reply_to_post = AsyncMock(return_value=True)
    mock_db.update_user_history = AsyncMock(return_value=True)

    await bot.process_new_replies()

    # 驗證記憶系統功能
    mock_db.get_user_conversation_history.assert_called_with(user_id)
    mock_db.update_user_history.assert_called_once()
    mock_threads_api.reply_to_post.assert_called_once() 