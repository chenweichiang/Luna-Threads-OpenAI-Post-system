"""
Version: 2024.03.30
Author: ThreadsPoster Team
Description: 設定檔管理模組，負責處理所有系統設定和配置
Last Modified: 2024.03.30
Changes:
- 優化設定檔結構
- 新增人設記憶相關設定
- 改進設定檔讀取機制
- 優化日誌路徑設定
- 加強設定檔驗證
"""

import os
import json
import pytz
import logging
from dotenv import load_dotenv
from typing import Dict, Any, List, Union, Optional
from datetime import datetime, time

logger = logging.getLogger(__name__)

class Config:
    """設定檔類別"""
    
    # 版本資訊
    VERSION = "1.1.4"
    LAST_UPDATED = "2024/03/30"
    
    def __init__(self, **kwargs):
        """初始化配置"""
        # 載入環境變數
        load_dotenv()
        
        # 輔助函數：清理環境變數值中的註釋
        def clean_env(env_name, default_value):
            value = os.getenv(env_name, default_value)
            if isinstance(value, str) and '#' in value:
                value = value.split('#')[0].strip()
            return value
        
        # 基本設定
        self.TIMEZONE = pytz.timezone("Asia/Taipei")  # 直接使用固定時區
        self.LOG_LEVEL = kwargs.get("LOG_LEVEL", os.getenv("LOG_LEVEL", "INFO"))
        
        # 日誌配置
        self.LOG_DIR = "logs"
        self.LOG_FILE = "threads_poster.log"
        self.LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        self.LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
        self.LOG_BACKUP_COUNT = 5
        
        # 處理日誌路徑
        log_path = kwargs.get("LOG_PATH", os.getenv("LOG_PATH", "logs/threads_poster.log"))
        self.LOG_PATH = os.path.join(os.getcwd(), log_path)
        
        # 發文時間設定
        self.PRIME_POST_START = int(kwargs.get("PRIME_POST_START", clean_env("PRIME_POST_START", "20")))  # 晚上8點
        self.PRIME_POST_END = int(kwargs.get("PRIME_POST_END", clean_env("PRIME_POST_END", "2")))      # 凌晨2點
        self.MIN_POSTS_PER_DAY = int(kwargs.get("MIN_POSTS_PER_DAY", clean_env("MIN_POSTS_PER_DAY", "5")))  # 每日最少5篇
        self.MAX_POSTS_PER_DAY = int(kwargs.get("MAX_POSTS_PER_DAY", clean_env("MAX_POSTS_PER_DAY", "40")))  # 每日最多40篇
        self.PRIME_TIME_POST_RATIO = float(kwargs.get("PRIME_TIME_POST_RATIO", clean_env("PRIME_TIME_POST_RATIO", "0.7")))  # 黃金時段發文比例

        # 情緒/心情模式時間段設定
        self.MOOD_MORNING_START = int(kwargs.get("MOOD_MORNING_START", clean_env("MOOD_MORNING_START", "5")))
        self.MOOD_MORNING_END = int(kwargs.get("MOOD_MORNING_END", clean_env("MOOD_MORNING_END", "11")))
        self.MOOD_NOON_START = int(kwargs.get("MOOD_NOON_START", clean_env("MOOD_NOON_START", "11")))
        self.MOOD_NOON_END = int(kwargs.get("MOOD_NOON_END", clean_env("MOOD_NOON_END", "14")))
        self.MOOD_AFTERNOON_START = int(kwargs.get("MOOD_AFTERNOON_START", clean_env("MOOD_AFTERNOON_START", "14")))
        self.MOOD_AFTERNOON_END = int(kwargs.get("MOOD_AFTERNOON_END", clean_env("MOOD_AFTERNOON_END", "18")))
        self.MOOD_EVENING_START = int(kwargs.get("MOOD_EVENING_START", clean_env("MOOD_EVENING_START", "18")))
        self.MOOD_EVENING_END = int(kwargs.get("MOOD_EVENING_END", clean_env("MOOD_EVENING_END", "22")))

        # API 設定
        self.API_BASE_URL = kwargs.get("API_BASE_URL", clean_env("THREADS_API_BASE_URL", "https://graph.threads.net/v1.0"))
        self.THREADS_ACCESS_TOKEN = kwargs.get("THREADS_ACCESS_TOKEN", clean_env("THREADS_ACCESS_TOKEN", "your_access_token_here"))
        self.THREADS_APP_ID = kwargs.get("THREADS_APP_ID", clean_env("THREADS_APP_ID", "your_app_id_here"))
        self.THREADS_APP_SECRET = kwargs.get("THREADS_APP_SECRET", clean_env("THREADS_APP_SECRET", "your_app_secret_here"))
        self.OPENAI_API_KEY = kwargs.get("OPENAI_API_KEY", clean_env("OPENAI_API_KEY", "your_openai_api_key_here"))
        self.OPENAI_MODEL = kwargs.get("OPENAI_MODEL", clean_env("OPENAI_MODEL", "gpt-4-turbo-preview"))
        self.MODEL_NAME = kwargs.get("MODEL_NAME", clean_env("MODEL_NAME", "gpt-4-turbo-preview"))
        
        # Threads API 設定
        self.THREADS_REDIRECT_URI = kwargs.get("THREADS_REDIRECT_URI", clean_env("THREADS_REDIRECT_URI", ""))
        self.THREADS_SCOPES = kwargs.get("THREADS_SCOPES", clean_env("THREADS_SCOPES", "")).split(",")
        self.THREADS_USER_ID = kwargs.get("THREADS_USER_ID", clean_env("THREADS_USER_ID", ""))

        # MongoDB 設定
        self.MONGODB_URI = kwargs.get("MONGODB_URI", clean_env("MONGODB_URI", "mongodb://localhost:27017"))
        self.MONGODB_DB_NAME = kwargs.get("MONGODB_DB_NAME", clean_env("MONGODB_DB_NAME", "threads_poster"))
        self.MONGODB_COLLECTION = kwargs.get("MONGODB_COLLECTION", clean_env("MONGODB_COLLECTION", "posts"))

        # 系統運行參數
        self.CHECK_INTERVAL = int(kwargs.get("CHECK_INTERVAL", clean_env("CHECK_INTERVAL", "60")))  # 檢查新回覆的間隔（秒）
        self.RETRY_INTERVAL = int(kwargs.get("RETRY_INTERVAL", clean_env("RETRY_INTERVAL", "300")))  # 重試間隔（秒）
        self.MAX_RETRIES = int(kwargs.get("MAX_RETRIES", clean_env("MAX_RETRIES", "3")))  # 最大重試次數
        self.RETRY_DELAY = int(kwargs.get("RETRY_DELAY", clean_env("RETRY_DELAY", "5")))  # 重試延遲（秒）
        self.MAX_RESPONSE_LENGTH = int(kwargs.get("MAX_RESPONSE_LENGTH", clean_env("MAX_RESPONSE_LENGTH", "500")))  # 回覆最大長度

        # 記憶系統設定
        self.MEMORY_CONFIG = kwargs.get("MEMORY_CONFIG", {
            'max_history': int(clean_env("MEMORY_MAX_HISTORY", "10")),
            'retention_days': int(clean_env("MEMORY_RETENTION_DAYS", "7")),
            'max_records': int(clean_env("MEMORY_MAX_RECORDS", "50"))
        })

        # 系統設定
        self.SYSTEM_CONFIG = kwargs.get("SYSTEM_CONFIG", {
            "timezone": clean_env("TIMEZONE", "Asia/Taipei"),
            "post_interval": {
                "prime_time": {
                    "min": int(clean_env("PRIME_TIME_MIN_INTERVAL", "900")),  # 主要時段最小間隔（15分鐘）
                    "max": int(clean_env("PRIME_TIME_MAX_INTERVAL", "2700"))   # 主要時段最大間隔（45分鐘）
                },
                "other_time": {
                    "min": int(clean_env("OTHER_TIME_MIN_INTERVAL", "3600")),  # 其他時段最小間隔（1小時）
                    "max": int(clean_env("OTHER_TIME_MAX_INTERVAL", "10800"))  # 其他時段最大間隔（3小時）
                }
            },
            "max_daily_posts": 40,    # 每日最大發文數
            "min_daily_posts": self.MIN_POSTS_PER_DAY,     # 每日最少發文數
            "log_level": clean_env("LOG_LEVEL", "DEBUG")
        })
        
        # 角色設定
        self.CHARACTER_CONFIG = {
            "基本資料": {
                "年齡": 20,
                "性別": "女性",
                "國籍": "台灣",
                "興趣": ["ACG文化", "電腦科技", "遊戲"],
                "個性特徵": [
                    "活潑開朗",
                    "了解科技",
                    "善於互動",
                    "喜歡分享"
                ]
            },
            "回文規則": {
                "字數限制": 20,
                "時間規律": {
                    "白天": "1-5分鐘內回覆",
                    "深夜": "5-30分鐘或不回覆"
                }
            },
            "記憶系統": {
                "功能": "系統要能記憶回過誰怎樣的對話並根據當下的回文以及過去的記憶進行回文",
                "記錄內容": [
                    "與每個用戶的互動歷史",
                    "對話內容和語氣",
                    "每次互動後更新記憶"
                ]
            },
            "mood_patterns": {
                "morning": {
                    "mood": "精神飽滿",
                    "topics": ["早安", "今天的計畫"],
                    "style": "活力充沛"
                },
                "noon": {
                    "mood": "悠閒放鬆",
                    "topics": ["午餐", "休息", "工作"],
                    "style": "輕鬆愉快"
                },
                "afternoon": {
                    "mood": "專注認真",
                    "topics": ["工作", "興趣", "學習"],
                    "style": "認真思考"
                },
                "evening": {
                    "mood": "放鬆愉快",
                    "topics": ["晚餐", "娛樂", "心情"],
                    "style": "溫柔體貼"
                },
                "night": {
                    "mood": "安靜思考",
                    "topics": ["星空", "音樂", "夢想"],
                    "style": "溫柔安靜"
                }
            }
        }
        
        # 關鍵字配置
        self.KEYWORDS = {
            "科技": [
                "新科技", "AI", "程式設計", "遊戲開發", "手機", "電腦", "智慧家電",
                "科技新聞", "程式", "coding", "開發", "軟體", "硬體", "技術"
            ],
            "動漫": [
                "動畫", "漫畫", "輕小說", "Cosplay", "同人創作", "聲優",
                "二次元", "動漫", "アニメ", "コスプレ", "同人誌", "漫展"
            ],
            "遊戲": [
                "電玩", "手遊", "主機遊戲", "遊戲實況", "電競", "RPG",
                "策略遊戲", "解謎遊戲", "音樂遊戲", "格鬥遊戲", "開放世界"
            ],
            "生活": [
                "美食", "旅遊", "時尚", "音樂", "電影", "寵物", "攝影",
                "咖啡", "下午茶", "美妝", "穿搭", "健身", "運動"
            ],
            "心情": [
                "工作", "學習", "戀愛", "友情", "家庭", "夢想", "目標",
                "心情", "感受", "情緒", "想法", "生活", "日常"
            ]
        }
        
        # 情感詞彙設定
        self.SENTIMENT_WORDS = {
            "正面": [
                "開心", "興奮", "期待", "喜歡", "讚賞", "感動", "溫暖", "愉快", "滿意",
                "好棒", "太棒", "超棒", "厲害", "amazing", "溫馨", "可愛", "美", "精彩",
                "享受", "舒服", "順手", "方便", "貼心", "實用", "棒", "讚", "喜愛",
                "期待", "驚喜", "幸福", "快樂", "甜蜜", "療癒", "放鬆", "愛"
            ],
            "中性": [
                "理解", "思考", "觀察", "好奇", "平靜", "普通", "一般", "還好",
                "正常", "習慣", "知道", "了解", "覺得", "認為", "想", "猜",
                "可能", "也許", "或許", "應該", "大概", "差不多"
            ],
            "負面": [
                "生氣", "難過", "失望", "煩惱", "焦慮", "疲倦", "無聊", "不滿",
                "討厭", "糟糕", "可惡", "麻煩", "困擾", "痛苦", "悲傷", "憤怒",
                "厭煩", "煩躁", "不爽", "不開心", "不好", "不行", "不可以"
            ]
        }
        
        if not kwargs.get("skip_validation", False):
            self.validate()
    
    def validate(self):
        """驗證設定"""
        required_settings = [
            ("API_BASE_URL", "Threads API base URL"),
            ("THREADS_ACCESS_TOKEN", "Threads access token"),
            ("THREADS_APP_ID", "Threads app ID"),
            ("THREADS_APP_SECRET", "Threads app secret"),
            ("OPENAI_API_KEY", "OpenAI API key"),
            ("OPENAI_MODEL", "OpenAI model name")
        ]
        
        for setting, name in required_settings:
            if not getattr(self, setting):
                logger.error(f"缺少必要設定: {name}")
                raise ValueError(f"Missing required setting: {name}")
    
    def get_mood_pattern(self, hour: int) -> Dict[str, Union[str, List[str]]]:
        """根據時間獲取心情模式
        
        Args:
            hour: 當前小時
            
        Returns:
            Dict: 心情模式設定
        """
        if self.MOOD_MORNING_START <= hour < self.MOOD_MORNING_END:
            return self.CHARACTER_CONFIG["mood_patterns"]["morning"]
        elif self.MOOD_NOON_START <= hour < self.MOOD_NOON_END:
            return self.CHARACTER_CONFIG["mood_patterns"]["noon"]
        elif self.MOOD_AFTERNOON_START <= hour < self.MOOD_AFTERNOON_END:
            return self.CHARACTER_CONFIG["mood_patterns"]["afternoon"]
        elif self.MOOD_EVENING_START <= hour < self.MOOD_EVENING_END:
            return self.CHARACTER_CONFIG["mood_patterns"]["evening"]
        else:
            return self.CHARACTER_CONFIG["mood_patterns"]["night"]
            
    def get_memory_config(self) -> Dict[str, Any]:
        """獲取記憶系統設定"""
        return self.MEMORY_CONFIG
        
    def get_character_config(self) -> Dict[str, Any]:
        """獲取角色設定"""
        return self.CHARACTER_CONFIG
        
    def get_openai_config(self) -> Dict[str, Any]:
        """獲取 OpenAI 設定"""
        return self.OPENAI_CONFIG
        
    def get_keywords(self) -> Dict[str, list]:
        """獲取關鍵字設定"""
        return self.KEYWORDS
        
    def get_sentiment_words(self) -> Dict[str, list]:
        """獲取情感詞彙設定"""
        return self.SENTIMENT_WORDS

    def is_prime_time(self, hour: int = None) -> bool:
        """檢查指定時間是否為主要發文時段
        
        Args:
            hour: 要檢查的小時，如果不指定則使用當前時間
            
        Returns:
            bool: 是否為主要發文時段
        """
        if hour is None:
            hour = datetime.now(self.TIMEZONE).hour
            
        if self.PRIME_POST_START <= self.PRIME_POST_END:
            return self.PRIME_POST_START <= hour <= self.PRIME_POST_END
        else:  # 跨越午夜的情況
            return hour >= self.PRIME_POST_START or hour <= self.PRIME_POST_END

    def get_post_schedule(self) -> Dict[str, Any]:
        """獲取發文排程設定
        
        Returns:
            Dict[str, Any]: 發文排程設定
        """
        return {
            "prime_time": {
                "start": self.PRIME_POST_START,
                "end": self.PRIME_POST_END
            },
            "posts_per_day": {
                "min": self.MIN_POSTS_PER_DAY,
                "max": self.MAX_POSTS_PER_DAY
            },
            "prime_time_ratio": self.PRIME_TIME_POST_RATIO
        }

    def to_dict(self) -> Dict[str, Any]:
        """將配置轉換為字典格式
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        return {
            key: value for key, value in self.__dict__.items()
            if not key.startswith('_')
        }
        
    def from_dict(self, config_dict: Dict[str, Any]):
        """從字典載入配置
        
        Args:
            config_dict: 配置字典
        """
        for key, value in config_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)
                
    def save_to_file(self, filepath: str):
        """儲存配置到檔案
        
        Args:
            filepath: 檔案路徑
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=4, ensure_ascii=False)
            
    def load_from_file(self, filepath: str):
        """從檔案載入配置
        
        Args:
            filepath: 檔案路徑
        """
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
                self.from_dict(config_dict)

# 創建全局配置實例
config = Config()