"""
Version: 2024.03.30
Author: ThreadsPoster Team
Description: 重試機制模組，負責處理系統的錯誤恢復和重試邏輯
Last Modified: 2024.03.30
Changes:
- 實現基本重試功能
- 加強錯誤處理
- 改進日誌記錄
- 優化重試策略
- 新增斷路器模式
- 新增速率限制器
"""

import asyncio
import logging
from typing import Callable, Any, Optional, Dict
from functools import wraps
import time
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

class RetryError(Exception):
    """重試錯誤"""
    pass

async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Any:
    """使用指數退避的重試機制
    
    Args:
        func: 要重試的函數
        max_retries: 最大重試次數
        initial_delay: 初始延遲時間（秒）
        max_delay: 最大延遲時間（秒）
        backoff_factor: 退避因子
        exceptions: 要捕捉的異常類型
        
    Returns:
        Any: 函數執行結果
        
    Raises:
        RetryError: 重試失敗
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await func()
        except exceptions as e:
            last_exception = e
            if attempt == max_retries - 1:
                raise RetryError(f"重試 {max_retries} 次後仍然失敗：{str(e)}")
                
            delay = min(delay * backoff_factor, max_delay)
            logger.warning(f"嘗試第 {attempt + 1} 次失敗，{delay} 秒後重試：{str(e)}")
            await asyncio.sleep(delay)
            
    raise RetryError(f"重試失敗：{str(last_exception)}")

def with_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """重試裝飾器
    
    Args:
        max_retries: 最大重試次數
        initial_delay: 初始延遲時間（秒）
        max_delay: 最大延遲時間（秒）
        backoff_factor: 退避因子
        exceptions: 要捕捉的異常類型
        
    Returns:
        Callable: 裝飾器函數
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            return await retry_with_backoff(
                lambda: func(*args, **kwargs),
                max_retries=max_retries,
                initial_delay=initial_delay,
                max_delay=max_delay,
                backoff_factor=backoff_factor,
                exceptions=exceptions
            )
        return wrapper
    return decorator

class CircuitBreaker:
    """斷路器模式實現"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
        half_open_timeout: float = 30.0
    ):
        """初始化斷路器
        
        Args:
            failure_threshold: 失敗閾值
            reset_timeout: 重置超時時間（秒）
            half_open_timeout: 半開狀態超時時間（秒）
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_timeout = half_open_timeout
        
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED"
        
    def record_failure(self):
        """記錄失敗"""
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"斷路器開啟：失敗次數達到 {self.failures}")
            
    def record_success(self):
        """記錄成功"""
        self.failures = 0
        self.state = "CLOSED"
        
    def can_execute(self) -> bool:
        """檢查是否可以執行
        
        Returns:
            bool: 是否可以執行
        """
        if self.state == "CLOSED":
            return True
            
        if self.state == "OPEN":
            if time.time() - self.last_failure_time >= self.reset_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
            
        # HALF_OPEN state
        if time.time() - self.last_failure_time >= self.half_open_timeout:
            return True
        return False
        
    def __call__(self, func: Callable) -> Callable:
        """裝飾器實現
        
        Args:
            func: 要保護的函數
            
        Returns:
            Callable: 包裝後的函數
        """
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            if not self.can_execute():
                raise RetryError("斷路器開啟，拒絕執行")
                
            try:
                result = await func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise
                
        return wrapper

class RateLimiter:
    """速率限制器"""
    
    def __init__(
        self,
        max_requests: int = 60,
        time_window: float = 60.0
    ):
        """初始化速率限制器
        
        Args:
            max_requests: 時間窗口內的最大請求數
            time_window: 時間窗口大小（秒）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        
    async def acquire(self):
        """獲取執行許可
        
        如果超過速率限制，會等待直到可以執行
        """
        now = time.time()
        
        # 清理過期的請求記錄
        self.requests = [ts for ts in self.requests if now - ts <= self.time_window]
        
        if len(self.requests) >= self.max_requests:
            # 計算需要等待的時間
            wait_time = self.requests[0] + self.time_window - now
            if wait_time > 0:
                logger.warning(f"達到速率限制，等待 {wait_time:.2f} 秒")
                await asyncio.sleep(wait_time)
                
        self.requests.append(now)
        
    def __call__(self, func: Callable) -> Callable:
        """裝飾器實現
        
        Args:
            func: 要限制的函數
            
        Returns:
            Callable: 包裝後的函數
        """
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            await self.acquire()
            return await func(*args, **kwargs)
        return wrapper 