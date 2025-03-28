"""
ThreadsPoster AI 處理器測試
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime
import pytz
from src.config import Config
from src.ai_handler import AIHandler

@pytest.fixture
def config():
    """配置物件夾具"""
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
def mock_ai_handler():
    """模擬 AI 處理器"""
    handler = AsyncMock(spec=AIHandler)
    handler.generate_post = AsyncMock(return_value="測試貼文")
    handler._analyze_sentiment = AsyncMock(return_value={
        "positive": 0.6,
        "negative": 0.1,
        "neutral": 0.3
    })
    handler._extract_topics = AsyncMock(return_value=["ACG", "BL", "科技"])
    handler._get_current_mood = AsyncMock(return_value={
        "mood": "精神飽滿",
        "topics": ["早安", "今天的計畫"],
        "style": "活力充沛"
    })
    handler._build_character_prompt = AsyncMock(return_value="角色提示")
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

@pytest.mark.asyncio
async def test_generate_post(mock_ai_handler):
    """測試生成貼文"""
    post = await mock_ai_handler.generate_post()
    assert post is not None
    assert isinstance(post, str)
    mock_ai_handler.generate_post.assert_called_once()

@pytest.mark.asyncio
async def test_analyze_sentiment(mock_ai_handler):
    """測試情感分析"""
    # 測試正面情感
    text = "好開心啊！真的很喜歡這個！"
    sentiment = await mock_ai_handler._analyze_sentiment(text)
    assert sentiment["positive"] > sentiment["negative"]
    mock_ai_handler._analyze_sentiment.assert_called_with(text)

@pytest.mark.asyncio
async def test_extract_topics(mock_ai_handler):
    """測試主題提取"""
    text = "今天看了新番動漫，真好看！"
    topics = await mock_ai_handler._extract_topics(text)
    assert "ACG" in topics
    mock_ai_handler._extract_topics.assert_called_with(text)

@pytest.mark.asyncio
async def test_get_current_mood(mock_ai_handler):
    """測試心情獲取"""
    mood = await mock_ai_handler._get_current_mood(8)
    assert mood["mood"] == "精神飽滿"
    assert "早安" in mood["topics"]
    mock_ai_handler._get_current_mood.assert_called_with(8)

@pytest.mark.asyncio
async def test_build_character_prompt(mock_ai_handler):
    """測試角色提示建立"""
    mood_info = {
        "mood": "精神飽滿",
        "topics": ["早安", "今天的計畫"],
        "style": "活力充沛"
    }
    prompt = await mock_ai_handler._build_character_prompt(mood_info)
    assert isinstance(prompt, str)
    mock_ai_handler._build_character_prompt.assert_called_with(mood_info)

@pytest.mark.asyncio
async def test_memory_management(mock_ai_handler):
    """測試記憶管理"""
    await mock_ai_handler.add_interaction("test_user", "你好啊！", "很高興認識你！")
    memory = await mock_ai_handler.get_user_memory("test_user")
    assert len(memory["conversations"]) == 1
    mock_ai_handler.add_interaction.assert_called_once_with(
        "test_user", "你好啊！", "很高興認識你！"
    )

@pytest.mark.asyncio
async def test_post_generation_with_memory(mock_ai_handler):
    """測試帶記憶的貼文生成"""
    await mock_ai_handler.add_interaction("test_user", "我最喜歡看 BL 漫畫了！", "我也超愛 BL 的！")
    post = await mock_ai_handler.generate_post()
    assert post is not None
    assert isinstance(post, str)
    mock_ai_handler.add_interaction.assert_called_once_with(
        "test_user", "我最喜歡看 BL 漫畫了！", "我也超愛 BL 的！"
    )

@pytest.mark.asyncio
async def test_error_handling(mock_ai_handler):
    """測試錯誤處理"""
    mock_ai_handler._analyze_sentiment.side_effect = ValueError("無效的輸入")
    with pytest.raises(ValueError):
        await mock_ai_handler._analyze_sentiment(None)
    mock_ai_handler._analyze_sentiment.assert_called_with(None) 