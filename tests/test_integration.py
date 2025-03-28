"""
ThreadsPoster 整合測試
測試整個系統的功能整合
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytz
from datetime import datetime, timedelta
from src.main import ThreadsPoster
import asyncio
from src.config import Config

@pytest_asyncio.fixture
async def mock_ai_handler():
    """模擬 AI 處理器"""
    handler = AsyncMock()
    handler.generate_response = AsyncMock(return_value="測試回應")
    handler.generate_post = AsyncMock(return_value="新的測試貼文")
    handler.generate_new_post = AsyncMock(return_value="新的測試貼文")
    handler.add_interaction = AsyncMock()
    handler.get_user_memory = AsyncMock(return_value={
        "conversations": [
            {
                "reply": "你好啊！",
                "response": "很高興認識你！",
                "timestamp": datetime.now(pytz.UTC)
            }
        ]
    })
    return handler

@pytest_asyncio.fixture
async def mock_threads_api():
    """模擬 Threads API"""
    api = AsyncMock()
    api.get_new_replies = AsyncMock(return_value=[{
        "id": "123",
        "username": "test_user",
        "text": "測試訊息",
        "created_at": datetime.now(pytz.UTC).isoformat()
    }])
    api.reply_to_post = AsyncMock(return_value=True)
    api.create_post = AsyncMock(return_value=True)
    api._session = None
    return api

@pytest_asyncio.fixture
async def mock_db():
    """模擬資料庫"""
    db = AsyncMock()
    db.get_user_conversation_history = AsyncMock(return_value=[{
        "message": "你還記得我們之前聊什麼嗎",
        "response": "記得，我們聊到天氣",
        "timestamp": datetime.now(pytz.UTC)
    }])
    db.update_user_history = AsyncMock()
    return db

@pytest_asyncio.fixture
async def mock_config():
    """模擬配置"""
    config = Config(skip_validation=True)
    config.POST_INTERVAL_HOURS = 1
    config.TIMEZONE = "Asia/Taipei"
    config.LOG_LEVEL = "DEBUG"
    config.OPENAI_MODEL = "gpt-3.5-turbo"
    config.VERSION = "1.0.0"
    config.LAST_UPDATED = "2024-03-24"
    return config

@pytest.mark.asyncio
async def test_full_reply_flow(mock_ai_handler, mock_threads_api, mock_db, mock_config):
    """測試完整的回覆流程"""
    bot = ThreadsPoster()
    bot.config = mock_config
    bot.ai_handler = mock_ai_handler
    bot.api = mock_threads_api
    bot.db = mock_db
    bot._test_mode = True

    await bot.process_new_replies()

    mock_threads_api.get_new_replies.assert_called_once()
    mock_ai_handler.generate_response.assert_called_once_with(
        user_id="test_user",
        message="測試訊息",
        history=[{
            "message": "你還記得我們之前聊什麼嗎",
            "response": "記得，我們聊到天氣",
            "timestamp": mock_db.get_user_conversation_history.return_value[0]["timestamp"]
        }]
    )
    mock_threads_api.reply_to_post.assert_called_once_with(
        post_id="123",
        text="測試回應"
    )

@pytest.mark.asyncio
async def test_new_post_generation(mock_ai_handler, mock_threads_api, mock_db, mock_config):
    """測試新貼文生成流程"""
    bot = ThreadsPoster()
    bot.config = mock_config
    bot.ai_handler = mock_ai_handler
    bot.api = mock_threads_api
    bot.db = mock_db
    bot._test_mode = True
    bot.last_post_time = datetime.now(pytz.UTC) - timedelta(hours=3)

    await bot.generate_new_post()

    mock_ai_handler.generate_new_post.assert_called_once()
    mock_threads_api.create_post.assert_called_once_with("新的測試貼文")

@pytest.mark.asyncio
async def test_error_recovery(mock_ai_handler, mock_threads_api, mock_db, mock_config):
    """測試錯誤恢復流程"""
    bot = ThreadsPoster()
    bot.config = mock_config
    bot.ai_handler = mock_ai_handler
    bot.api = mock_threads_api
    bot.db = mock_db
    bot._test_mode = True

    # 模擬連續的 API 錯誤後成功
    mock_threads_api.create_post.side_effect = [False, False, True]

    await bot.generate_new_post()

    assert mock_threads_api.create_post.call_count == 3
    mock_ai_handler.generate_new_post.assert_called_once()

@pytest.mark.asyncio
async def test_concurrent_operations(mock_ai_handler, mock_threads_api, mock_db, mock_config):
    """測試並發操作"""
    bot = ThreadsPoster()
    bot.config = mock_config
    bot.ai_handler = mock_ai_handler
    bot.api = mock_threads_api
    bot.db = mock_db
    bot._test_mode = True

    await asyncio.gather(
        bot.process_new_replies(),
        bot.generate_new_post()
    )

    mock_threads_api.get_new_replies.assert_called_once()
    mock_ai_handler.generate_response.assert_called_once()
    mock_threads_api.create_post.assert_called_once()

@pytest.mark.asyncio
async def test_memory_system(mock_ai_handler, mock_threads_api, mock_db, mock_config):
    """測試記憶系統"""
    bot = ThreadsPoster()
    bot.config = mock_config
    bot.ai_handler = mock_ai_handler
    bot.api = mock_threads_api
    bot.db = mock_db
    bot._test_mode = True

    await bot.process_new_replies()

    mock_db.get_user_conversation_history.assert_called_once_with("test_user")
    mock_db.update_user_history.assert_called_once()

@pytest.mark.asyncio
async def test_run(mock_ai_handler, mock_threads_api, mock_db, mock_config):
    """測試主程式運行"""
    bot = ThreadsPoster()
    bot.config = mock_config
    bot.ai_handler = mock_ai_handler
    bot.api = mock_threads_api
    bot.db = mock_db
    bot._test_mode = True

    # 模擬一個短暫的運行
    async def mock_sleep(*args, **kwargs):
        await asyncio.sleep(0.1)
        raise KeyboardInterrupt()

    with patch('asyncio.sleep', mock_sleep):
        # 測試正常運行和鍵盤中斷
        await bot.run()

    # 驗證是否調用了必要的方法
    assert mock_threads_api.get_new_replies.called
    assert mock_ai_handler.generate_new_post.called
    mock_ai_handler.add_interaction.assert_called()
    mock_db.update_user_history.assert_called() 