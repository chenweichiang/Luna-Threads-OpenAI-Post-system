"""
Version: 2024.03.30
Author: ThreadsPoster Team
Description: 時間控制器類別，負責管理發文時間
Last Modified: 2024.03.30
Changes:
- 實現基本時間控制功能
- 加強時間計算邏輯
- 改進日誌記錄
"""

import logging
import random
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any

class TimeController:
    """時間控制器類別"""
    
    def __init__(self, timezone: str, post_interval: Dict[str, Dict[str, int]]):
        """初始化時間控制器
        
        Args:
            timezone: 時區
            post_interval: 發文間隔設定
                {
                    "prime_time": {
                        "min": 最小間隔（秒）,
                        "max": 最大間隔（秒）
                    },
                    "other_time": {
                        "min": 最小間隔（秒）,
                        "max": 最大間隔（秒）
                    }
                }
        """
        self.timezone = pytz.timezone(timezone)
        self.post_interval = post_interval
        self.next_post_time = None
        self.logger = logging.getLogger(__name__)
        
    def _is_prime_time(self, dt: datetime = None) -> bool:
        """判斷是否為主要發文時段
        
        Args:
            dt: 要判斷的時間，如果不指定則使用當前時間
            
        Returns:
            bool: 是否為主要發文時段
        """
        if dt is None:
            dt = datetime.now(self.timezone)
            
        hour = dt.hour
        return (11 <= hour <= 14) or (17 <= hour <= 22)
        
    def _get_interval(self) -> int:
        """獲取下一次發文間隔
        
        Returns:
            int: 間隔秒數
        """
        if self._is_prime_time():
            interval = self.post_interval["prime_time"]
        else:
            interval = self.post_interval["other_time"]
            
        return random.randint(interval["min"], interval["max"])
        
    async def get_next_post_time(self) -> datetime:
        """獲取下一次發文時間
        
        Returns:
            datetime: 下一次發文時間
        """
        if self.next_post_time is None:
            self.next_post_time = datetime.now(self.timezone)
            
        return self.next_post_time
        
    async def update_next_post_time(self):
        """更新下一次發文時間"""
        interval = self._get_interval()
        self.next_post_time = datetime.now(self.timezone) + timedelta(seconds=interval)
        self.logger.info(f"更新下一次發文時間：{self.next_post_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
    def get_current_time_info(self) -> Dict[str, Any]:
        """獲取當前時間資訊
        
        Returns:
            Dict[str, Any]: 時間資訊
        """
        now = datetime.now(self.timezone)
        return {
            "current_time": now,
            "is_prime_time": self._is_prime_time(now),
            "next_post_time": self.next_post_time,
            "timezone": str(self.timezone)
        } 