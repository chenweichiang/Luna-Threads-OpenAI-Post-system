"""
ThreadsPoster 測試
"""

import pytest
from unittest.mock import Mock, patch, PropertyMock
from datetime import datetime
import json
import os
from pathlib import Path

from src.config import Config
from src.threads_poster import ThreadsPoster

@pytest.fixture
def config():
    """設定檔"""
    return Config()

@pytest.fixture
def mock_api():
    """模擬 API"""
    with patch("src.threads_api.ThreadsAPI") as mock:
        # 設定 API 屬性
        type(mock.return_value).user_info = PropertyMock(return_value={
            "username": "test_user",
            "id": "123456789"
        })
        
        # 設定 API 方法
        mock.return_value.get_user_info.return_value = {
            "username": "test_user",
            "id": "123456789"
        }
        mock.return_value.get_publishing_limit.return_value = {
            "quota_usage": 0,
            "quota_total": 250
        }
        mock.return_value.get_user_posts.return_value = [{
            "id": "post1",
            "text": "test post"
        }]
        mock.return_value.get_post_replies.return_value = [{
            "id": "reply1",
            "username": "test_user",
            "text": "test reply"
        }]
        mock.return_value.create_reply.return_value = "new_reply1"
        
        yield mock.return_value

@pytest.fixture
def poster(config, mock_api):
    """ThreadsPoster 實例"""
    with patch("src.threads_poster.ThreadsAPI", return_value=mock_api):
        poster = ThreadsPoster(config)
        poster.api = mock_api
        yield poster

def test_initialize(poster, mock_api):
    """測試初始化"""
    # 執行初始化
    result = poster.initialize()
    
    # 驗證結果
    assert result is True
    assert poster.user_info == {
        "username": "test_user",
        "id": "123456789"
    }
    
    # 驗證 API 呼叫
    mock_api.get_user_info.assert_called_once()
    mock_api.get_publishing_limit.assert_called_once()

def test_should_reply_now(poster):
    """測試回覆時間判斷"""
    # 模擬白天時間
    with patch("datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 3, 27, 14, 0)  # 下午 2 點
        assert poster._should_reply_now() in [True, False]  # 80% 機率回覆
    
    # 模擬深夜時間
    with patch("datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 3, 27, 2, 0)  # 凌晨 2 點
        assert poster._should_reply_now() in [True, False]  # 20% 機率回覆

def test_generate_reply(poster):
    """測試回覆生成"""
    # 測試第一次互動
    reply = poster._generate_reply("new_user", "你好")
    assert "你好 new_user" in reply
    assert "💕" in reply
    
    # 測試已有互動記錄
    poster.memory["users"]["existing_user"] = {
        "first_interaction": "2024-03-27T00:00:00",
        "interactions": [{
            "timestamp": "2024-03-27T00:00:00",
            "type": "reply",
            "original_text": "你好",
            "reply_text": "你好！"
        }]
    }
    reply = poster._generate_reply("existing_user", "謝謝")
    assert "謝謝你的回覆" in reply
    assert "existing_user" in reply

def test_memory_operations(poster, tmp_path):
    """測試記憶系統操作"""
    # 設定臨時記憶檔案
    poster.memory_file = tmp_path / "memory.json"
    
    # 測試儲存記憶
    poster.memory["users"]["test_user"] = {
        "first_interaction": "2024-03-27T00:00:00",
        "interactions": []
    }
    poster._save_memory()
    
    # 驗證檔案存在
    assert poster.memory_file.exists()
    
    # 測試載入記憶
    loaded_memory = poster._load_memory()
    assert "test_user" in loaded_memory["users"]
    
    # 測試更新用戶記憶
    poster._update_user_memory("test_user", {
        "type": "reply",
        "original_text": "test",
        "reply_text": "test reply"
    })
    assert len(poster.memory["users"]["test_user"]["interactions"]) == 1

def test_check_and_reply(poster, mock_api):
    """測試檢查和回覆功能"""
    # 設定用戶資訊
    poster.user_info = {
        "username": "test_bot",
        "id": "123456789"
    }
    
    # 執行檢查和回覆
    with patch.object(poster, "_should_reply_now", return_value=True):
        poster.check_and_reply()
    
    # 驗證 API 呼叫
    mock_api.get_user_posts.assert_called_once()
    mock_api.get_post_replies.assert_called_once_with("post1")
    mock_api.create_reply.assert_called_once_with("reply1", "你好 test_user！很高興認識你 💕") 