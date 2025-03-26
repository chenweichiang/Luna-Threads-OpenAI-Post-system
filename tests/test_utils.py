"""工具函數測試"""

import unittest
import json
import pytz
from datetime import datetime
from unittest.mock import patch
from src.utils import (
    validate_environment,
    get_current_time,
    format_time,
    sanitize_text,
    safe_json_loads,
    get_posting_probability,
    get_suggested_topics
)
from src.exceptions import ValidationError
from src.config import Config

class TestUtils(unittest.TestCase):
    """工具函數測試類"""

    def setUp(self):
        """設置測試環境"""
        self.config_patcher = patch('src.config.Config')
        self.mock_config = self.config_patcher.start()
        self.mock_config.return_value.TIMEZONE = pytz.timezone('Asia/Taipei')
        
    def tearDown(self):
        """清理測試環境"""
        self.config_patcher.stop()
        
    def test_sanitize_text(self):
        """測試文本清理功能"""
        text = "  Hello\n\nWorld\t!"
        max_length = 10
        
        result = sanitize_text(text, max_length)
        self.assertEqual(result, "Hello")
        
        # 測試沒有長度限制的情況
        result = sanitize_text(text)
        self.assertEqual(result, "Hello World!")

    def test_safe_json_loads(self):
        """測試安全的 JSON 解析功能"""
        valid_json = '{"key": "value"}'
        result = safe_json_loads(valid_json)
        self.assertEqual(result, {"key": "value"})
        
        invalid_json = 'invalid json'
        result = safe_json_loads(invalid_json)
        self.assertEqual(result, {})

    def test_get_current_time(self):
        """測試獲取當前時間功能"""
        result = get_current_time()
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.tzinfo, pytz.UTC)

    def test_format_time(self):
        """測試時間格式化功能"""
        dt = datetime(2024, 3, 15, 12, 0, 0, tzinfo=pytz.UTC)
        result = format_time(dt)
        self.assertEqual(result, "2024-03-15T12:00:00+00:00")

if __name__ == '__main__':
    unittest.main()