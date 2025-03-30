"""
Version: 2024.03.31 (v1.1.6)
Author: ThreadsPoster Team
Description: 時間控制器類別，負責管理系統運行時間和排程
Last Modified: 2024.03.31
Changes:
- 實現基本時間控制功能
- 加強錯誤處理
- 優化時間分布
- 動態調整發文間隔
- 支援不同時段的發文頻率設定
- 優化時區處理
"""

import logging
import random
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any, Optional
import os
import asyncio

class TimeController:
    """時間控制器類別"""
    
    def __init__(self):
        """初始化時間控制器"""
        self.timezone = pytz.timezone(os.getenv("TIMEZONE", "Asia/Taipei"))
        self.next_post_time = None
        self.logger = logging.getLogger(__name__)
        
        # 設定發文間隔
        self.post_interval = {
            "prime_time": {
                "min": int(os.getenv("PRIME_TIME_MIN_INTERVAL", "1800")),  # 30分鐘
                "max": int(os.getenv("PRIME_TIME_MAX_INTERVAL", "3600"))   # 1小時
            },
            "other_time": {
                "min": int(os.getenv("OTHER_TIME_MIN_INTERVAL", "3600")),  # 1小時
                "max": int(os.getenv("OTHER_TIME_MAX_INTERVAL", "7200"))   # 2小時
            }
        }
        
        # 設定允許發文的時間範圍
        self.allowed_hours = range(7, 23)  # 早上7點到晚上11點
        
    def should_post(self) -> bool:
        """檢查是否應該發文
        
        Returns:
            bool: 是否應該發文
        """
        current_time = datetime.now(self.timezone)
        
        # 如果 next_post_time 未設定，先設定它
        if self.next_post_time is None:
            self.next_post_time = current_time
            return True
            
        # 檢查是否到達發文時間
        if current_time < self.next_post_time:
            self.logger.info("等待下次發文時間，當前時間：%s，下次發文時間：%s",
                current_time.strftime("%Y-%m-%d %H:%M:%S"),
                self.next_post_time.strftime("%Y-%m-%d %H:%M:%S"))
            return False
            
        # 檢查是否在允許的時間範圍內
        hour = current_time.hour
        if hour not in self.allowed_hours:
            self.logger.info("當前時間不在允許發文範圍，當前時間：%d時，允許時間：7-23時", hour)
            # 設定下次發文時間為明天早上7點
            tomorrow = current_time + timedelta(days=1)
            self.next_post_time = tomorrow.replace(hour=7, minute=0, second=0, microsecond=0)
            return False
        
        return True
        
    def get_wait_time(self) -> float:
        """獲取需要等待的時間
        
        Returns:
            float: 需要等待的秒數
        """
        current_time = datetime.now(self.timezone)
        wait_seconds = (self.next_post_time - current_time).total_seconds()
        return max(0, wait_seconds)
        
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
        
    def get_interval(self) -> int:
        """獲取下一次發文間隔
        
        Returns:
            int: 間隔秒數
        """
        if self._is_prime_time():
            interval = self.post_interval["prime_time"]
        else:
            interval = self.post_interval["other_time"]
            
        return random.randint(interval["min"], interval["max"])
        
    async def wait_until_next_post(self):
        """等待到下一次發文時間"""
        try:
            # 更新下次發文時間
            interval = self.get_interval()
            self.next_post_time = datetime.now(self.timezone) + timedelta(seconds=interval)
            
            # 如果下次發文時間超出允許範圍，調整到明天早上7點
            if self.next_post_time.hour not in self.allowed_hours:
                tomorrow = self.next_post_time + timedelta(days=1)
                self.next_post_time = tomorrow.replace(hour=7, minute=0, second=0, microsecond=0)
                interval = (self.next_post_time - datetime.now(self.timezone)).total_seconds()
            
            self.logger.info("更新發文時間，下次發文時間：%s，間隔：%d 秒",
                self.next_post_time.strftime("%Y-%m-%d %H:%M:%S"),
                interval)
                
            # 等待到下次發文時間
            await asyncio.sleep(self.get_wait_time())
            
        except Exception as e:
            self.logger.error("更新發文時間失敗：%s", str(e))
            # 如果更新失敗，等待一小時
            await asyncio.sleep(3600)
        
    def get_current_time_info(self) -> Dict[str, Any]:
        """獲取當前時間資訊
        
        Returns:
            Dict[str, Any]: 時間資訊
        """
        now = datetime.now(self.timezone)
        return {
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "is_prime_time": self._is_prime_time(now),
            "next_post_time": self.next_post_time.strftime("%Y-%m-%d %H:%M:%S") if self.next_post_time else None,
            "timezone": str(self.timezone),
            "allowed_hours": f"{self.allowed_hours.start}-{self.allowed_hours.stop-1}"
        } 