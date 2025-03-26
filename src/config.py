"""
ThreadsPoster 設定檔
包含所有系統配置和環境變數
"""

import os
import pytz
from dotenv import load_dotenv
from typing import Dict, Any

class Config:
    """設定檔類別"""
    
    def __init__(self):
        """初始化設定"""
        # 載入環境變數
        load_dotenv()
        
        # API 設定
        self.API_CONFIG = {
            "access_token": os.getenv("THREADS_ACCESS_TOKEN"),
            "app_id": os.getenv("THREADS_APP_ID"),
            "app_secret": os.getenv("THREADS_APP_SECRET"),
            "base_url": "https://graph.threads.net/v1.0",
            "user_id": os.getenv("THREADS_USER_ID", "me")
        }
        
        # API 權限
        self.API_PERMISSIONS = [
            "threads_basic",             # 基本權限
            "threads_content_publish",   # 發布貼文權限
            "threads_manage_replies",    # 管理回覆權限
            "threads_read_replies"       # 讀取回覆權限
        ]
        
        # 時區設定
        self.TIMEZONE = os.getenv("TIMEZONE", "Asia/Taipei")
        try:
            self.TIMEZONE = pytz.timezone(self.TIMEZONE)
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f"無效的時區設定: {self.TIMEZONE}")
        
        # 角色設定
        self.CHARACTER = {
            "基本資料": {
                "年齡": 28,
                "性別": "女性",
                "國籍": "台灣",
                "興趣": ["ACG文化", "電腦科技", "BL作品"],
                "個性特徵": [
                    "喜歡說曖昧的話",
                    "了解科技",
                    "善於互動"
                ]
            },
            "回文規則": {
                "字數限制": 25,
                "時間規律": {
                    "白天": {
                        "回覆機率": 0.8,
                        "延遲時間": [60, 300]  # 1-5分鐘
                    },
                    "深夜": {
                        "回覆機率": 0.2,
                        "延遲時間": [300, 1800]  # 5-30分鐘
                    }
                }
            }
        }
        
        # OpenAI 設定
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        if not self.OPENAI_API_KEY:
            raise ValueError("未設定 OPENAI_API_KEY 環境變數")
            
        self.OPENAI_MODEL = "gpt-4-0125-preview"
        self.OPENAI_CONFIG = {
            "temperature": 0.7,
            "max_tokens": 150,
            "top_p": 0.9,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.5
        }
        
        # 角色配置
        self.CHARACTER_CONFIG = {
            "基本資料": {
                "年齡": self.CHARACTER["基本資料"]["年齡"],
                "性別": self.CHARACTER["基本資料"]["性別"],
                "國籍": self.CHARACTER["基本資料"]["國籍"],
                "興趣": self.CHARACTER["基本資料"]["興趣"],
                "個性特徵": self.CHARACTER["基本資料"]["個性特徵"]
            },
            "回文規則": {
                "字數限制": "不超過25個字，以完整句子回覆",
                "時間規律": {
                    "白天": "1-5分鐘內回覆",
                    "深夜": "5-30分鐘或不回覆",
                    "說明": "根據不同的時間點回文會有一定的規律不會隨時都回文章"
                },
                "主動發文": "角色會自己主動發新的文章，根據當下的想法跟心情"
            }
        }
        
        # 系統限制
        self.LIMITS = {
            "text": {
                "max_length": 500
            }
        }
        
        self._validate_config()
    
    def _validate_config(self):
        """驗證配置"""
        if not self.API_CONFIG["access_token"]:
            raise ValueError('未設定 API_CONFIG["access_token"]')
        if not self.API_CONFIG["user_id"]:
            raise ValueError('未設定 API_CONFIG["user_id"]')
        if not self.API_CONFIG["app_id"]:
            raise ValueError('未設定 API_CONFIG["app_id"]')
        if not self.API_CONFIG["app_secret"]:
            raise ValueError('未設定 API_CONFIG["app_secret"]')
        if not isinstance(self.TIMEZONE, pytz.tzinfo.BaseTzInfo):
            raise ValueError('無效的時區設定')

# 創建全局配置實例
config = Config()