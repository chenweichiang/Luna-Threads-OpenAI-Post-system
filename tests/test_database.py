"""資料庫模組測試"""

import pytest
import mongomock_motor
import pytz
from datetime import datetime
from src.database import Database
from src.config import Config
from unittest.mock import AsyncMock, patch

@pytest.fixture
async def database():
    """資料庫夾具"""
    config = Config(skip_validation=True)
    db = Database(config, is_test=True)
    await db.init_indexes()
    return db

@pytest.fixture
def mock_database():
    """模擬資料庫"""
    db = AsyncMock(spec=Database)
    
    # 模擬集合
    db.conversations = AsyncMock()
    db.posts = AsyncMock()
    
    # 模擬方法
    db.save_conversation = AsyncMock(return_value=True)
    db.get_user_conversation_history = AsyncMock(return_value=[
        {
            "message": "test message",
            "response": "test response",
            "timestamp": datetime.now(pytz.UTC)
        }
    ])
    db.save_post = AsyncMock(return_value=True)
    db.has_replied_to_post = AsyncMock(return_value=False)
    db.get_user_interaction_summary = AsyncMock(return_value={
        "total_interactions": 1,
        "topics": ["ACG", "BL"],
        "sentiment": {
            "positive": 0.6,
            "negative": 0.1,
            "neutral": 0.3
        }
    })
    db.cleanup_old_records = AsyncMock(return_value=True)
    
    return db

@pytest.mark.asyncio
async def test_save_conversation(mock_database):
    """測試保存對話功能"""
    # 準備測試數據
    user_id = "test_user"
    message = "test message"
    response = "test response"
    
    # 執行測試
    result = await mock_database.save_conversation(user_id, message, response)
    assert result is True
    mock_database.save_conversation.assert_called_once_with(user_id, message, response)

@pytest.mark.asyncio
async def test_get_user_conversation_history(mock_database):
    """測試獲取用戶對話歷史功能"""
    # 準備測試數據
    user_id = "test_user"
    
    # 執行測試
    history = await mock_database.get_user_conversation_history(user_id)
    assert len(history) == 1
    assert history[0]["message"] == "test message"
    mock_database.get_user_conversation_history.assert_called_once_with(user_id)

@pytest.mark.asyncio
async def test_save_post(mock_database):
    """測試保存貼文功能"""
    # 準備測試數據
    post_id = "test_post"
    content = "test content"
    user_id = "test_user"
    is_reply = False
    
    # 執行測試
    result = await mock_database.save_post(post_id, content, user_id, is_reply)
    assert result is True
    mock_database.save_post.assert_called_once_with(post_id, content, user_id, is_reply)

@pytest.mark.asyncio
async def test_has_replied_to_post(mock_database):
    """測試檢查貼文回覆狀態功能"""
    # 準備測試數據
    post_id = "test_post"
    
    # 執行測試
    result = await mock_database.has_replied_to_post(post_id)
    assert result is False
    mock_database.has_replied_to_post.assert_called_once_with(post_id)

@pytest.mark.asyncio
async def test_get_user_interaction_summary(mock_database):
    """測試獲取用戶互動摘要"""
    # 準備測試數據
    user_id = "test_user"
    
    # 執行測試
    summary = await mock_database.get_user_interaction_summary(user_id)
    assert summary["total_interactions"] == 1
    assert "ACG" in summary["topics"]
    mock_database.get_user_interaction_summary.assert_called_once_with(user_id)

@pytest.mark.asyncio
async def test_cleanup_old_records(mock_database):
    """測試清理舊記錄功能"""
    # 執行測試
    result = await mock_database.cleanup_old_records()
    assert result is True
    mock_database.cleanup_old_records.assert_called_once()