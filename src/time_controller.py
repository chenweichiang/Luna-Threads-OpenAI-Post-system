"""
Version: 2025.03.31 (v1.1.9)
Author: ThreadsPoster Team
Description: 時間控制器類別，負責管理系統運行時間和排程
Copyright (c) 2025 Chiang, Chenwei. All rights reserved.
License: MIT License
Last Modified: 2025.03.31
Changes:
- 實現基本時間控制功能
- 加強錯誤處理
- 優化時間分布
- 動態調整發文間隔
- 支援不同時段的發文頻率設定
- 優化時區處理
- 加強晚間發文比例
- 實現智能發文計劃生成
- 處理24點特殊情況
- 測試模式支援
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
    
    def __init__(self, config=None):
        """初始化時間控制器
        
        Args:
            config: 配置對象，包含發文間隔設定
        """
        # 輔助函數：清理環境變數值中的註釋
        def clean_env(env_name, default_value):
            value = os.getenv(env_name, default_value)
            if isinstance(value, str) and '#' in value:
                value = value.split('#')[0].strip()
            return value
            
        self.timezone = pytz.timezone(clean_env("TIMEZONE", "Asia/Taipei"))
        self.next_post_time = None
        self.logger = logging.getLogger(__name__)
        
        # 設定發文間隔
        if config and hasattr(config, 'SYSTEM_CONFIG') and 'post_interval' in config.SYSTEM_CONFIG:
            self.post_interval = config.SYSTEM_CONFIG['post_interval']
            self.logger.info(f"從配置讀取發文間隔設定: {self.post_interval}")
        else:
            # 使用預設值或環境變數
            self.post_interval = {
                "prime_time": {
                    "min": int(clean_env("PRIME_TIME_MIN_INTERVAL", "900")),  # 15分鐘
                    "max": int(clean_env("PRIME_TIME_MAX_INTERVAL", "2700"))   # 45分鐘
                },
                "other_time": {
                    "min": int(clean_env("OTHER_TIME_MIN_INTERVAL", "3600")),  # 1小時
                    "max": int(clean_env("OTHER_TIME_MAX_INTERVAL", "10800"))   # 3小時
                }
            }
        
        # 設定允許發文的時間範圍，從環境變數讀取
        posting_hours_start = int(clean_env("POSTING_HOURS_START", "7"))  # 預設早上7點
        posting_hours_end = int(clean_env("POSTING_HOURS_END", "23"))    # 預設晚上11點
        self.allowed_hours = range(posting_hours_start, posting_hours_end)
        self.logger.info(f"設定允許發文時間範圍: {posting_hours_start}-{posting_hours_end}")
        
        # 設定黃金時段的時間範圍，從環境變數讀取
        self.prime_time_afternoon_start = int(clean_env("PRIME_TIME_AFTERNOON_START", "11"))
        self.prime_time_afternoon_end = int(clean_env("PRIME_TIME_AFTERNOON_END", "14"))
        self.prime_time_evening_start = int(clean_env("PRIME_TIME_EVENING_START", "17"))
        self.prime_time_evening_end = int(clean_env("PRIME_TIME_EVENING_END", "22"))
        self.logger.info(f"設定黃金時段時間範圍: 午間({self.prime_time_afternoon_start}-{self.prime_time_afternoon_end}), 晚間({self.prime_time_evening_start}-{self.prime_time_evening_end})")
        
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
            self.logger.info("當前時間不在允許發文範圍，當前時間：%d時，允許時間：%d-%d時", 
                hour, self.allowed_hours.start, self.allowed_hours.stop-1)
            # 設定下次發文時間為明天早上的允許發文開始時間
            tomorrow = current_time + timedelta(days=1)
            self.next_post_time = tomorrow.replace(hour=self.allowed_hours.start, minute=0, second=0, microsecond=0)
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
        # 從環境變數讀取的黃金時段設定
        return (self.prime_time_afternoon_start <= hour <= self.prime_time_afternoon_end) or \
               (self.prime_time_evening_start <= hour <= self.prime_time_evening_end)
        
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
            
            # 如果下次發文時間超出允許範圍，調整到明天早上的允許發文開始時間
            if self.next_post_time.hour not in self.allowed_hours:
                tomorrow = self.next_post_time + timedelta(days=1)
                self.next_post_time = tomorrow.replace(hour=self.allowed_hours.start, minute=0, second=0, microsecond=0)
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