"""工具函數測試"""

import unittest
import json
import pytz
from datetime import datetime
from unittest.mock import patch, MagicMock
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
        """測試前的設置"""
        self.test_config = Config(skip_validation=True)
        self.test_config.TIMEZONE = "Asia/Taipei"
        self.test_config.POSTING_TIMEZONE = pytz.timezone(self.test_config.TIMEZONE)
        self.test_config.CHARACTER_PROFILE = {
            'posting_schedule': {
                'morning': {
                    'probability': 0.8,
                    'topics': ['早安', '今日計畫']
                },
                'afternoon': {
                    'probability': 0.6,
                    'topics': ['下午茶', '工作分享']
                },
                'evening': {
                    'probability': 0.9,
                    'topics': ['晚安', '今日回顧']
                }
            }
        }

    def test_sanitize_text(self):
        """測試文本清理功能"""
        # 測試空字符串
        self.assertEqual(sanitize_text(""), "")
        
        # 測試去除空白
        self.assertEqual(sanitize_text("  test  "), "test")
        
        # 測試長度限制
        long_text = "a" * 200
        result = sanitize_text(long_text)
        self.assertTrue(len(result) <= 20)  # 根據角色設定的字數限制

        # 測試特殊字符
        special_text = "Hello\n\tWorld!"
        result = sanitize_text(special_text)
        self.assertEqual(result, "Hello World!")

    def test_safe_json_loads(self):
        """測試安全 JSON 解析功能"""
        # 測試有效的 JSON
        valid_json = '{"key": "value"}'
        result = safe_json_loads(valid_json)
        self.assertEqual(result, {"key": "value"})

        # 測試無效的 JSON
        invalid_json = 'invalid json'
        result = safe_json_loads(invalid_json)
        self.assertIsNone(result)

    def test_get_current_time(self):
        """測試獲取當前時間功能"""
        # 模擬一個固定的時間點（UTC 時間 14:30）
        mock_now = datetime(2024, 3, 24, 14, 30, tzinfo=pytz.UTC)
        
        with patch('src.utils.config', self.test_config), \
             patch('src.utils.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            current_time = get_current_time()
            # 台北時間應該是 UTC+8，所以 14:30 UTC = 22:30 台北時間
            self.assertEqual(current_time.hour, 22)
            self.assertEqual(current_time.minute, 30)
            self.assertEqual(str(current_time.tzinfo), "Asia/Taipei")

    def test_format_time(self):
        """測試時間格式化功能"""
        # 建立一個固定的時間點
        test_time = datetime(2024, 3, 24, 14, 30, tzinfo=pytz.UTC)
        formatted = format_time(test_time)
        self.assertEqual(formatted, "2024-03-24 14:30:00")

    def test_get_posting_probability(self):
        """測試獲取發文機率功能"""
        with patch('src.utils.config', self.test_config):
            # 測試早上時段 (9-12)
            mock_time = datetime(2024, 3, 24, 2, 0, tzinfo=pytz.UTC)  # UTC 2:00 = 台北 10:00
            with patch('src.utils.datetime') as mock_datetime:
                mock_datetime.now.return_value = mock_time
                self.assertEqual(get_posting_probability(), 0.8)

            # 測試下午時段 (14-18)
            mock_time = datetime(2024, 3, 24, 7, 0, tzinfo=pytz.UTC)  # UTC 7:00 = 台北 15:00
            with patch('src.utils.datetime') as mock_datetime:
                mock_datetime.now.return_value = mock_time
                self.assertEqual(get_posting_probability(), 0.6)

            # 測試晚上時段 (19-23)
            mock_time = datetime(2024, 3, 24, 12, 0, tzinfo=pytz.UTC)  # UTC 12:00 = 台北 20:00
            with patch('src.utils.datetime') as mock_datetime:
                mock_datetime.now.return_value = mock_time
                self.assertEqual(get_posting_probability(), 0.9)

            # 測試深夜時段 (其他時間)
            mock_time = datetime(2024, 3, 24, 16, 0, tzinfo=pytz.UTC)  # UTC 16:00 = 台北 0:00
            with patch('src.utils.datetime') as mock_datetime:
                mock_datetime.now.return_value = mock_time
                self.assertEqual(get_posting_probability(), 0)

    def test_get_suggested_topics(self):
        """測試獲取建議主題功能"""
        with patch('src.utils.config', self.test_config):
            # 測試早上時段
            mock_time = datetime(2024, 3, 24, 2, 0, tzinfo=pytz.UTC)  # UTC 2:00 = 台北 10:00
            with patch('src.utils.datetime') as mock_datetime:
                mock_datetime.now.return_value = mock_time
                self.assertEqual(get_suggested_topics(), ['早安', '今日計畫'])

            # 測試下午時段
            mock_time = datetime(2024, 3, 24, 7, 0, tzinfo=pytz.UTC)  # UTC 7:00 = 台北 15:00
            with patch('src.utils.datetime') as mock_datetime:
                mock_datetime.now.return_value = mock_time
                self.assertEqual(get_suggested_topics(), ['下午茶', '工作分享'])

            # 測試晚上時段
            mock_time = datetime(2024, 3, 24, 12, 0, tzinfo=pytz.UTC)  # UTC 12:00 = 台北 20:00
            with patch('src.utils.datetime') as mock_datetime:
                mock_datetime.now.return_value = mock_time
                self.assertEqual(get_suggested_topics(), ['晚安', '今日回顧'])

            # 測試深夜時段
            mock_time = datetime(2024, 3, 24, 16, 0, tzinfo=pytz.UTC)  # UTC 16:00 = 台北 0:00
            with patch('src.utils.datetime') as mock_datetime:
                mock_datetime.now.return_value = mock_time
                self.assertEqual(get_suggested_topics(), [])

if __name__ == '__main__':
    unittest.main()