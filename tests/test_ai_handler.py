"""
AI 處理器測試
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import pytz
from datetime import datetime
from src.ai_handler import AIHandler
from src.config import Config

@pytest.fixture
def config():
    """建立測試用設定"""
    return Config()

@pytest.fixture
def ai_handler(config):
    """建立測試用 AI 處理器"""
    return AIHandler(config)

@pytest.mark.asyncio
async def test_generate_response(ai_handler):
    """測試回應生成"""
    # 模擬資料庫回應
    mock_db = AsyncMock()
    mock_db.get_user_conversation_history.return_value = []
    ai_handler.db = mock_db

    # 模擬 OpenAI 回應
    mock_client = AsyncMock()
    mock_completion = AsyncMock()
    mock_completion.choices = [AsyncMock(message=AsyncMock(content="測試回應"))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    ai_handler.client = mock_client
    response = await ai_handler.generate_response(
        message="測試訊息",
        username="test_user"
    )

    assert response == "測試回應"
    assert len(response) <= ai_handler.config.MAX_RESPONSE_LENGTH

@pytest.mark.asyncio
async def test_generate_new_post(ai_handler):
    """測試新貼文生成"""
    # 模擬 OpenAI 回應
    mock_client = AsyncMock()
    mock_completion = AsyncMock()
    mock_completion.choices = [AsyncMock(message=AsyncMock(content="測試貼文"))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
    
    ai_handler.client = mock_client
    post = await ai_handler.generate_new_post()
    
    assert post == "測試貼文"
    assert len(post) <= ai_handler.config.MAX_RESPONSE_LENGTH

@pytest.mark.asyncio
async def test_error_handling(ai_handler):
    """測試錯誤處理"""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("測試錯誤"))
    
    ai_handler.client = mock_client
    response = await ai_handler.generate_response(
        message="測試訊息",
        username="test_user"
    )
    assert response is None

    post = await ai_handler.generate_new_post()
    assert post is None

@pytest.mark.asyncio
async def test_generate_response_with_history(ai_handler):
    """測試帶有歷史記錄的回應生成"""
    # 模擬資料庫回應
    mock_db = AsyncMock()
    mock_db.get_user_conversation_history.return_value = [
        {"message": "你好啊", "response": "哈囉！"},
        {"message": "今天天氣真好", "response": "是啊，適合出門玩"}
    ]
    ai_handler.db = mock_db

    # 模擬 OpenAI 回應
    mock_client = AsyncMock()
    mock_completion = AsyncMock()
    mock_completion.choices = [AsyncMock(message=AsyncMock(content="記得上次聊天說到天氣呢"))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    ai_handler.client = mock_client
    response = await ai_handler.generate_response(
        message="你還記得我們上次聊什麼嗎",
        username="test_user"
    )

    assert response == "記得上次聊天說到天氣呢"
    assert len(response) <= ai_handler.config.MAX_RESPONSE_LENGTH

@pytest.mark.asyncio
async def test_generate_response_exceeds_length(ai_handler):
    """測試超過長度限制的回應"""
    # 模擬資料庫回應
    mock_db = AsyncMock()
    mock_db.get_user_conversation_history.return_value = []
    ai_handler.db = mock_db

    # 模擬 OpenAI 回應
    mock_client = AsyncMock()
    mock_completion = AsyncMock()
    mock_completion.choices = [AsyncMock(message=AsyncMock(content="這是一個超過二十個字的測試回應，應該要被截斷"))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    ai_handler.client = mock_client
    response = await ai_handler.generate_response(
        message="測試訊息",
        username="test_user"
    )

    assert len(response) <= ai_handler.config.MAX_RESPONSE_LENGTH

@pytest.mark.asyncio
async def test_generate_response_empty_history(ai_handler):
    """測試沒有歷史記錄的回應生成"""
    # 模擬資料庫回應
    mock_db = AsyncMock()
    mock_db.get_user_conversation_history.return_value = []
    ai_handler.db = mock_db

    # 模擬 OpenAI 回應
    mock_client = AsyncMock()
    mock_completion = AsyncMock()
    mock_completion.choices = [AsyncMock(message=AsyncMock(content="第一次見面，請多指教"))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    ai_handler.client = mock_client
    response = await ai_handler.generate_response(
        message="你好",
        username="new_user"
    )

    assert response == "第一次見面，請多指教"

@pytest.mark.asyncio
async def test_generate_new_post_time_based(ai_handler):
    """測試不同時間的貼文生成"""
    test_times = [
        (5, "早安，開始新的一天"),   # 清晨
        (14, "下午茶時光"),         # 下午
        (22, "晚安，好夢")          # 深夜
    ]
    
    for hour, expected_content in test_times:
        mock_client = AsyncMock()
        mock_completion = AsyncMock()
        mock_completion.choices = [AsyncMock(message=AsyncMock(content=expected_content))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        
        ai_handler.client = mock_client
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 3, 24, hour, 0, tzinfo=pytz.UTC)
            post = await ai_handler.generate_new_post()
            assert post == expected_content

@pytest.mark.asyncio
async def test_error_handling_timeout(ai_handler):
    """測試超時錯誤處理"""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=TimeoutError("連線超時"))
    
    ai_handler.client = mock_client
    response = await ai_handler.generate_response(
        message="測試訊息",
        username="test_user"
    )
    assert response is None

@pytest.mark.asyncio
async def test_error_handling_rate_limit(ai_handler):
    """測試速率限制錯誤處理"""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("rate_limit_exceeded"))
    
    ai_handler.client = mock_client
    response = await ai_handler.generate_response(
        message="測試訊息",
        username="test_user"
    )
    assert response is None

@pytest.mark.asyncio
async def test_error_handling_invalid_response(ai_handler):
    """測試無效回應處理"""
    mock_client = AsyncMock()
    mock_completion = AsyncMock()
    mock_completion.choices = []  # 空的回應列表
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
    
    ai_handler.client = mock_client
    response = await ai_handler.generate_response(
        message="測試訊息",
        username="test_user"
    )
    assert response is None

@pytest.mark.asyncio
async def test_generate_response_special_characters(ai_handler):
    """測試特殊字元處理"""
    # 模擬資料庫回應
    mock_db = AsyncMock()
    mock_db.get_user_conversation_history.return_value = []
    ai_handler.db = mock_db

    # 模擬 OpenAI 回應
    mock_client = AsyncMock()
    mock_completion = AsyncMock()
    mock_completion.choices = [AsyncMock(message=AsyncMock(content="測試😊表情符號"))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    ai_handler.client = mock_client
    response = await ai_handler.generate_response(
        message="你好👋",
        username="test_user"
    )

    assert "😊" in response
    assert len(response) <= ai_handler.config.MAX_RESPONSE_LENGTH 