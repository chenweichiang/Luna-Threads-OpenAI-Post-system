"""
Threads API 測試
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock
import aiohttp
from src.threads_api import ThreadsAPI
from src.config import Config

@pytest_asyncio.fixture
async def mock_threads_api():
    """建立模擬 Threads API 客戶端"""
    config = Config()
    api = ThreadsAPI(config)
    api.base_url = "https://graph.threads.net/v1.0"
    api.headers = {
        "Authorization": "Bearer test_token",
        "Content-Type": "application/json"
    }
    return api

@pytest.mark.asyncio
async def test_get_new_replies():
    """測試取得新回覆"""
    config = Config()
    api = ThreadsAPI(config)
    
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "data": [
            {
                "id": "123",
                "username": "test_user",
                "text": "測試回覆",
                "created_time": "2024-03-15T12:00:00+00:00",
                "media_type": "TEXT",
                "permalink": "https://threads.net/p/123"
            }
        ]
    })

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()

    with patch('aiohttp.ClientSession', return_value=mock_session):
        result = await api.get_new_replies()
        assert len(result) == 1
        assert result[0]["id"] == "123"
        assert result[0]["username"] == "test_user"
        mock_session.get.assert_called_once()

@pytest.mark.asyncio
async def test_reply_to_post():
    """測試回覆貼文"""
    config = Config()
    api = ThreadsAPI(config)
    
    # 模擬發布限制回應
    mock_limit_response = MagicMock()
    mock_limit_response.status = 200
    mock_limit_response.json = AsyncMock(return_value={
        "data": [{
            "reply_quota_usage": 10,
            "reply_config": {
                "quota_total": 1000,
                "quota_duration": 86400
            }
        }]
    })
    
    # 模擬回覆貼文回應
    mock_reply_response = MagicMock()
    mock_reply_response.status = 200
    mock_reply_response.json = AsyncMock(return_value={"id": "321"})

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_limit_response)
    mock_session.post = AsyncMock(return_value=mock_reply_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()

    with patch('aiohttp.ClientSession', return_value=mock_session):
        result = await api.reply_to_post("123", "測試回覆")
        assert result is True
        mock_session.post.assert_called_once()

@pytest.mark.asyncio
async def test_create_post():
    """測試建立貼文"""
    config = Config()
    api = ThreadsAPI(config)
    
    # 模擬發布限制回應
    mock_limit_response = MagicMock()
    mock_limit_response.status = 200
    mock_limit_response.json = AsyncMock(return_value={
        "data": [{
            "quota_usage": 10,
            "config": {
                "quota_total": 250,
                "quota_duration": 86400
            }
        }]
    })
    
    # 模擬建立貼文回應
    mock_post_response = MagicMock()
    mock_post_response.status = 200
    mock_post_response.json = AsyncMock(return_value={"id": "789"})

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_limit_response)
    mock_session.post = AsyncMock(return_value=mock_post_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()

    with patch('aiohttp.ClientSession', return_value=mock_session):
        result = await api.create_post("測試貼文")
        assert result is True
        mock_session.post.assert_called_once()

@pytest.mark.asyncio
async def test_error_handling():
    """測試錯誤處理"""
    config = Config()
    api = ThreadsAPI(config)
    
    mock_session = MagicMock()
    mock_session.get = AsyncMock(side_effect=aiohttp.ClientError("測試錯誤"))
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()

    with patch('aiohttp.ClientSession', return_value=mock_session):
        result = await api.get_new_replies()
        assert result == []
        mock_session.get.assert_called_once()

@pytest.mark.asyncio
async def test_rate_limit_handling():
    """測試速率限制處理"""
    config = Config()
    api = ThreadsAPI(config)
    
    mock_response = MagicMock()
    mock_response.status = 429
    mock_response.json = AsyncMock(return_value={"error": "rate_limit_exceeded"})

    mock_session = MagicMock()
    mock_session.post = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()

    with patch('aiohttp.ClientSession', return_value=mock_session):
        result = await api.create_post("測試貼文")
        assert result is False
        mock_session.post.assert_called_once()

@pytest.mark.asyncio
async def test_auth_error_handling():
    """測試認證錯誤處理"""
    config = Config()
    api = ThreadsAPI(config)
    
    mock_response = MagicMock()
    mock_response.status = 401
    mock_response.json = AsyncMock(return_value={"error": "invalid_token"})

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()

    with patch('aiohttp.ClientSession', return_value=mock_session):
        result = await api.get_new_replies()
        assert result == []
        mock_session.get.assert_called_once()

@pytest.mark.asyncio
async def test_publishing_limit():
    """測試發布限制檢查"""
    config = Config()
    api = ThreadsAPI(config)
    
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "data": [{
            "quota_usage": 250,
            "config": {
                "quota_total": 250,
                "quota_duration": 86400
            }
        }]
    })

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()

    with patch('aiohttp.ClientSession', return_value=mock_session):
        result = await api.create_post("測試貼文")
        assert result is False  # 因為已達到每日發文限制 