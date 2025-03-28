"""
ThreadsPoster 測試
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
import pytz
from src.config import Config
from src.threads_poster import ThreadsPoster

@pytest_asyncio.fixture
async def config():
    """設定檔"""
    config = Config()
    config.POST_INTERVAL_HOURS = 3
    return config

@pytest_asyncio.fixture
async def mock_api():
    """模擬 API"""
    mock = AsyncMock()
    
    # 設定基本回應
    mock.get_user_info = AsyncMock(return_value={
        "username": "test_user",
        "id": "123456789"
    })
    
    mock.get_publishing_limit = AsyncMock(return_value={
        "quota_usage": 0,
        "quota_total": 250
    })
    
    mock.get_new_replies = AsyncMock(return_value=[{
        "id": "reply1",
        "username": "test_user",
        "text": "test message",
        "created_at": datetime.now(pytz.UTC).isoformat()
    }])
    
    mock.reply_to_post = AsyncMock(return_value=True)
    mock.create_post = AsyncMock(return_value=True)
    
    return mock

@pytest_asyncio.fixture
async def mock_ai_handler():
    """模擬 AI 處理器"""
    mock = AsyncMock()
    mock.generate_response = AsyncMock(return_value="測試回應")
    mock.generate_new_post = AsyncMock(return_value="測試貼文")
    return mock

@pytest_asyncio.fixture
async def mock_db():
    """模擬資料庫"""
    mock = AsyncMock()
    mock.connect = AsyncMock()
    mock.get_user_conversation_history = AsyncMock(return_value=[])
    mock.update_user_history = AsyncMock(return_value=True)
    return mock

@pytest_asyncio.fixture
async def poster(config, mock_api, mock_ai_handler, mock_db):
    """ThreadsPoster 實例"""
    with patch("src.threads_poster.ThreadsAPI", return_value=mock_api), \
         patch("src.threads_poster.AIHandler", return_value=mock_ai_handler), \
         patch("src.threads_poster.Database", return_value=mock_db):
        
        poster = ThreadsPoster()
        poster._test_mode = True
        await poster.initialize()
        return poster

@pytest.mark.asyncio
async def test_initialize(poster, mock_db, mock_api):
    """測試初始化"""
    mock_db.connect.assert_awaited_once()
    mock_api.get_user_info.assert_awaited_once()
    mock_api.get_publishing_limit.assert_awaited_once()

@pytest.mark.asyncio
async def test_should_reply_now(poster):
    """測試回覆時間判斷"""
    with patch("datetime.datetime") as mock_datetime:
        # 測試白天時間（80% 機率回覆）
        mock_datetime.now.return_value = datetime(2024, 3, 27, 14, 0)
        result = await poster._should_reply_now()
        assert isinstance(result, bool)
        
        # 測試深夜時間（20% 機率回覆）
        mock_datetime.now.return_value = datetime(2024, 3, 27, 2, 0)
        result = await poster._should_reply_now()
        assert isinstance(result, bool)

@pytest.mark.asyncio
async def test_generate_reply(poster, mock_db, mock_ai_handler):
    """測試回覆生成"""
    username = "test_user"
    message = "test message"
    
    response = await poster._generate_reply(username, message)
    
    mock_db.get_user_conversation_history.assert_awaited_once_with(username)
    mock_ai_handler.generate_response.assert_awaited_once()
    mock_db.update_user_history.assert_awaited_once()
    assert response == "測試回應"

@pytest.mark.asyncio
async def test_process_new_replies(poster, mock_api, mock_ai_handler):
    """測試處理新回覆"""
    # 設定 _should_reply_now 永遠返回 True
    with patch.object(poster, "_should_reply_now", AsyncMock(return_value=True)):
        await poster.process_new_replies()
        
        mock_api.get_new_replies.assert_awaited_once()
        mock_ai_handler.generate_response.assert_awaited_once()
        mock_api.reply_to_post.assert_awaited_once()

@pytest.mark.asyncio
async def test_generate_new_post(poster, mock_api, mock_ai_handler):
    """測試生成新貼文"""
    # 設定上次發文時間為超過間隔時間
    poster.last_post_time = datetime.now(pytz.UTC) - timedelta(hours=4)
    
    await poster.generate_new_post()
    
    mock_ai_handler.generate_new_post.assert_awaited_once()
    mock_api.create_post.assert_awaited_once()
    assert (datetime.now(pytz.UTC) - poster.last_post_time).total_seconds() < 60

@pytest.mark.asyncio
async def test_run(poster):
    """測試主程序運行"""
    # 模擬運行一次後結束
    with patch.object(poster, "process_new_replies", AsyncMock()) as mock_process, \
         patch.object(poster, "generate_new_post", AsyncMock()) as mock_generate, \
         patch("asyncio.sleep", AsyncMock(side_effect=KeyboardInterrupt("Stop"))):
        
        with pytest.raises(KeyboardInterrupt):
            await poster.run()
        
        mock_process.assert_awaited_once()
        mock_generate.assert_awaited_once() 