"""
Version: 2024.03.30
Author: ThreadsPoster Team
Description: 異常處理模組，定義系統使用的自定義異常
Last Modified: 2024.03.30
Changes:
- 新增自定義異常類型
- 優化異常處理邏輯
- 改進錯誤訊息
- 加強異常追蹤
- 優化錯誤分類
"""

class ThreadsBotError(Exception):
    """基礎異常類別"""
    
    def __init__(self, message: str, *args, **kwargs):
        """初始化異常
        
        Args:
            message: 錯誤訊息
            *args: 位置參數
            **kwargs: 關鍵字參數
        """
        super().__init__(message, *args)
        self.message = message
        for key, value in kwargs.items():
            setattr(self, key, value)
            
    def __str__(self) -> str:
        """返回錯誤訊息"""
        return self.message

class APIError(ThreadsBotError):
    """API 相關錯誤"""
    
    def __init__(self, message: str, status_code: int = None, response_text: str = None):
        """初始化 API 錯誤
        
        Args:
            message: 錯誤訊息
            status_code: HTTP 狀態碼
            response_text: 回應內容
        """
        super().__init__(message, status_code=status_code, response_text=response_text)
        self.status_code = status_code
        self.response_text = response_text

class DatabaseError(ThreadsBotError):
    """資料庫相關錯誤"""
    
    def __init__(self, message: str, collection: str = None, operation: str = None):
        """初始化資料庫錯誤
        
        Args:
            message: 錯誤訊息
            collection: 集合名稱
            operation: 操作類型
        """
        super().__init__(message, collection=collection, operation=operation)
        self.collection = collection
        self.operation = operation

class AIError(ThreadsBotError):
    """AI 處理相關錯誤"""
    
    def __init__(self, message: str, model: str = None, error_type: str = None, details: dict = None):
        """初始化 AI 錯誤
        
        Args:
            message: 錯誤訊息
            model: AI 模型名稱
            error_type: 錯誤類型
            details: 詳細錯誤資訊
        """
        super().__init__(message, model=model, error_type=error_type, details=details)
        self.model = model
        self.error_type = error_type
        self.details = details or {}
        
    def get_error_details(self) -> dict:
        """獲取詳細錯誤資訊
        
        Returns:
            dict: 錯誤詳細資訊
        """
        return {
            "message": self.message,
            "model": self.model,
            "error_type": self.error_type,
            "details": self.details
        }

class ContentGeneratorError(ThreadsBotError):
    """內容生成相關錯誤"""
    
    def __init__(self, message: str, model: str = None, prompt: str = None):
        """初始化內容生成錯誤
        
        Args:
            message: 錯誤訊息
            model: 模型名稱
            prompt: 提示詞
        """
        super().__init__(message, model=model, prompt=prompt)
        self.model = model
        self.prompt = prompt

class ConfigError(ThreadsBotError):
    """配置相關錯誤"""
    
    def __init__(self, message: str, config_key: str = None):
        """初始化配置錯誤
        
        Args:
            message: 錯誤訊息
            config_key: 配置項目
        """
        super().__init__(message, config_key=config_key)
        self.config_key = config_key

class ValidationError(ThreadsBotError):
    """資料驗證錯誤"""
    
    def __init__(self, message: str, field: str = None, value: str = None):
        """初始化驗證錯誤
        
        Args:
            message: 錯誤訊息
            field: 欄位名稱
            value: 欄位值
        """
        super().__init__(message, field=field, value=value)
        self.field = field
        self.value = value

class ThreadsAPIError(APIError):
    """Threads API 錯誤"""
    
    def __init__(self, message: str, status_code: int = None, response_text: str = None, endpoint: str = None):
        """初始化 Threads API 錯誤
        
        Args:
            message: 錯誤訊息
            status_code: HTTP 狀態碼
            response_text: 回應內容
            endpoint: API 端點
        """
        super().__init__(message, status_code=status_code, response_text=response_text)
        self.endpoint = endpoint 