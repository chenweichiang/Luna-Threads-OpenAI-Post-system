"""
Version: 2024.03.30
Author: ThreadsPoster Team
Description: 異常處理模組，定義系統使用的自定義異常
Last Modified: 2024.03.30
Changes:
- 新增自定義異常類型
- 優化異常處理邏輯
- 改進錯誤訊息
"""

class ThreadsBotError(Exception):
    """基礎異常類別"""
    pass

class APIError(ThreadsBotError):
    """API 相關錯誤"""
    pass

class DatabaseError(ThreadsBotError):
    """資料庫相關錯誤"""
    pass

class AIError(ThreadsBotError):
    """AI 處理相關錯誤"""
    pass

class ConfigError(ThreadsBotError):
    """配置相關錯誤"""
    pass

class ValidationError(ThreadsBotError):
    """資料驗證錯誤"""
    pass

class ThreadsAPIError(Exception):
    """Threads API 錯誤"""
    pass 