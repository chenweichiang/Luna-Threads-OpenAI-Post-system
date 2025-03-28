"""
ThreadsAPI 測試
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime
import pytz
from src.threads_api import ThreadsAPI
from src.config import Config

@pytest_asyncio.fixture
async def mock_threads_api():
    """模擬 ThreadsAPI"""
    config = Config(skip_validation=True)
    api = ThreadsAPI(config)
    api.session = AsyncMock()
    return api

@pytest.mark.asyncio
async def test_get_new_replies(mock_threads_api):
    """測試取得新回覆"""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "data": [
            {
                "id": "123",
                "username": "test_user",
                "text": "測試回覆",
                "created_at": datetime.now(pytz.UTC).isoformat()
            }
        ]
    })

    mock_threads_api.session.get = AsyncMock()
    mock_threads_api.session.get.return_value = mock_response

    replies = await mock_threads_api.get_new_replies()
    assert replies is not None
    assert len(replies) == 1

@pytest.mark.asyncio
async def test_reply_to_post(mock_threads_api):
    """測試回覆貼文"""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"success": True})
    
    mock_threads_api.session.post = AsyncMock()
    mock_threads_api.session.post.return_value = mock_response
    
    success = await mock_threads_api.reply_to_post(
        post_id="123",
        text="測試回應"
    )
    assert success is True

@pytest.mark.asyncio
async def test_create_post(mock_threads_api):
    """測試建立貼文"""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"success": True})
    
    mock_threads_api.session.post = AsyncMock()
    mock_threads_api.session.post.return_value = mock_response
    
    success = await mock_threads_api.create_post("測試貼文")
    assert success is True

@pytest.mark.asyncio
async def test_error_handling(mock_threads_api):
    """測試錯誤處理"""
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.json = AsyncMock(return_value={"error": "Internal Server Error"})
    
    mock_threads_api.session.get = AsyncMock()
    mock_threads_api.session.get.return_value = mock_response
    
    replies = await mock_threads_api.get_new_replies()
    assert len(replies) == 0

@pytest.mark.asyncio
async def test_rate_limit_handling(mock_threads_api):
    """測試速率限制處理"""
    mock_response = AsyncMock()
    mock_response.status = 429
    mock_response.json = AsyncMock(return_value={"error": "Too Many Requests"})
    
    mock_threads_api.session.post = AsyncMock()
    mock_threads_api.session.post.return_value = mock_response
    
    success = await mock_threads_api.create_post("測試貼文")
    assert success is False 