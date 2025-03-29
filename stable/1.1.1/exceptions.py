"""自定義異常類別"""

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