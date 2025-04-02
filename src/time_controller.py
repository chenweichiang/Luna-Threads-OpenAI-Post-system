"""
Version: 2025.04.02 (v1.2.1)
Author: ThreadsPoster Team
Description: 時間控制器類別，負責管理系統運行時間和排程
Copyright (c) 2025 Chiang, Chenwei. All rights reserved.
License: MIT License
Last Modified: 2025.04.02
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
- 調整發文頻率為一天3-5次
- 集中發文時間在晚上20:00-2:00
"""

import logging
import random
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any, Optional, List
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
        self.today_post_count = 0
        self.max_daily_posts = random.randint(3, 5)  # 每天發文3-5次
        self.daily_post_plan = []
        
        # 設定發文間隔
        if config and hasattr(config, 'SYSTEM_CONFIG') and 'post_interval' in config.SYSTEM_CONFIG:
            self.post_interval = config.SYSTEM_CONFIG['post_interval']
            self.logger.info(f"從配置讀取發文間隔設定: {self.post_interval}")
        else:
            # 使用預設值或環境變數
            self.post_interval = {
                "prime_time": {
                    "min": int(clean_env("PRIME_TIME_MIN_INTERVAL", "1800")),  # 30分鐘
                    "max": int(clean_env("PRIME_TIME_MAX_INTERVAL", "3600"))   # 60分鐘
                },
                "other_time": {
                    "min": int(clean_env("OTHER_TIME_MIN_INTERVAL", "5400")),  # 1.5小時
                    "max": int(clean_env("OTHER_TIME_MAX_INTERVAL", "10800"))   # 3小時
                }
            }
        
        # 設定允許發文的時間範圍，調整為晚上20:00到凌晨2:00
        posting_hours_start = int(clean_env("POSTING_HOURS_START", "20"))  # 預設晚上8點
        posting_hours_end = int(clean_env("POSTING_HOURS_END", "26"))    # 預設凌晨2點 (24+2)
        
        # 將時間範圍轉換為兩個列表，因為range不支持跨日循環
        if posting_hours_end > 24:
            night_hours = list(range(posting_hours_start, 24))
            morning_hours = list(range(0, posting_hours_end - 24))
            self.allowed_hours = night_hours + morning_hours
        else:
            self.allowed_hours = list(range(posting_hours_start, posting_hours_end))
            
        self.logger.info(f"設定允許發文時間範圍: 晚上{posting_hours_start}點到凌晨{posting_hours_end-24}點")
        
        # 設定黃金時段，調整為晚上21:00到凌晨1:00
        self.prime_time_evening_start = int(clean_env("PRIME_TIME_EVENING_START", "21"))
        self.prime_time_evening_end = int(clean_env("PRIME_TIME_EVENING_END", "25"))  # 凌晨1點 (24+1)
        self.logger.info(f"設定黃金時段時間範圍: 晚間({self.prime_time_evening_start}-{self.prime_time_evening_end-24 if self.prime_time_evening_end > 24 else self.prime_time_evening_end})")
        
        # 一開始就生成今日發文計劃
        self.generate_daily_post_plan()
        
    def generate_daily_post_plan(self):
        """生成每日發文計劃，隨機安排3-5個時間點"""
        now = datetime.now(self.timezone)
        today_start = now.replace(hour=20, minute=0, second=0, microsecond=0)
        
        # 如果當前時間已經過了今天的晚上8點，則計劃是從今晚8點到明天凌晨2點
        if now.hour >= 20:
            pass
        else:
            # 如果當前時間還沒到晚上8點，計劃是從昨天晚上8點到今天凌晨2點
            today_start = today_start - timedelta(days=1)
            
        tomorrow_end = today_start + timedelta(hours=6)  # 晚上8點到凌晨2點共6小時
        
        # 重設每日發文計數
        self.today_post_count = 0
        self.max_daily_posts = random.randint(3, 5)
        
        # 生成發文時間點
        self.daily_post_plan = []
        available_minutes = (tomorrow_end - today_start).total_seconds() / 60
        
        for i in range(self.max_daily_posts):
            # 計算間隔，確保時間點均勻分布
            segment_minutes = available_minutes / self.max_daily_posts
            segment_start = today_start + timedelta(minutes=segment_minutes * i)
            segment_end = today_start + timedelta(minutes=segment_minutes * (i + 1))
            
            # 在每個時間段中隨機選擇一個時間點
            random_minutes = random.randint(0, int(segment_minutes) - 1)
            post_time = segment_start + timedelta(minutes=random_minutes)
            
            self.daily_post_plan.append(post_time)
            
        self.daily_post_plan.sort()  # 確保時間順序正確
        
        # 設置第一個發文時間
        if self.daily_post_plan and now < self.daily_post_plan[-1]:
            # 找出第一個大於當前時間的發文時間點
            for post_time in self.daily_post_plan:
                if post_time > now:
                    self.next_post_time = post_time
                    break
            if not self.next_post_time:
                self.next_post_time = self.daily_post_plan[0]
        else:
            # 如果已經超過了今天所有的發文時間，則設置為明天的第一個發文時間
            tomorrow_start = today_start + timedelta(days=1)
            # 重新生成明天的計劃
            self.daily_post_plan = []
            for i in range(self.max_daily_posts):
                segment_minutes = available_minutes / self.max_daily_posts
                segment_start = tomorrow_start + timedelta(minutes=segment_minutes * i)
                segment_end = tomorrow_start + timedelta(minutes=segment_minutes * (i + 1))
                random_minutes = random.randint(0, int(segment_minutes) - 1)
                post_time = segment_start + timedelta(minutes=random_minutes)
                self.daily_post_plan.append(post_time)
            self.daily_post_plan.sort()
            self.next_post_time = self.daily_post_plan[0]
            
        plan_str = ", ".join([dt.strftime("%Y-%m-%d %H:%M:%S") for dt in self.daily_post_plan])
        self.logger.info(f"已生成每日發文計劃，今日計劃發文{self.max_daily_posts}次，時間點: {plan_str}")
            
    def should_post(self) -> bool:
        """檢查是否應該發文
        
        Returns:
            bool: 是否應該發文
        """
        current_time = datetime.now(self.timezone)
        
        # 如果 next_post_time 未設定，先生成發文計劃
        if self.next_post_time is None:
            self.generate_daily_post_plan()
            return False
            
        # 檢查是否到達發文時間
        if current_time < self.next_post_time:
            self.logger.info("等待下次發文時間，當前時間：%s，下次發文時間：%s",
                current_time.strftime("%Y-%m-%d %H:%M:%S"),
                self.next_post_time.strftime("%Y-%m-%d %H:%M:%S"))
            return False
            
        # 檢查今日發文次數是否已達上限
        if self.today_post_count >= self.max_daily_posts:
            self.logger.info("今日發文次數已達上限(%d/%d)，等待明日發文計劃",
                self.today_post_count, self.max_daily_posts)
            # 生成明日計劃
            self.generate_daily_post_plan()
            return False
        
        # 檢查是否在允許的時間範圍內
        hour = current_time.hour
        if hour not in self.allowed_hours:
            self.logger.info("當前時間不在允許發文範圍，當前時間：%d時，允許時間：晚上20點至凌晨2點", hour)
            # 設定下次發文時間為今晚的發文時間點或明天的第一個發文時間點
            if self.daily_post_plan:
                for post_time in self.daily_post_plan:
                    if post_time > current_time:
                        self.next_post_time = post_time
                        return False
            
            # 如果沒有找到適合的時間點，重新生成計劃
            self.generate_daily_post_plan()
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
        # 從環境變數讀取的黃金時段設定，僅考慮晚間時段
        if hour < 0 or hour >= 24:  # 處理跨日情況
            hour = hour % 24
            
        evening_start = self.prime_time_evening_start
        evening_end = self.prime_time_evening_end
        
        # 處理跨日情況
        if evening_end > 24:
            if hour >= evening_start or hour < evening_end - 24:
                return True
        else:
            if evening_start <= hour <= evening_end:
                return True
                
        return False
        
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
            # 增加今日發文計數並更新下次發文時間
            self.today_post_count += 1
            
            # 從發文計劃中獲取下一個發文時間
            current_time = datetime.now(self.timezone)
            next_time_found = False
            
            for post_time in self.daily_post_plan:
                if post_time > current_time:
                    self.next_post_time = post_time
                    next_time_found = True
                    break
                    
            # 如果沒有找到下一個發文時間，則生成明天的發文計劃
            if not next_time_found:
                self.generate_daily_post_plan()
            
            # 計算等待時間
            wait_time = self.get_wait_time()
            
            self.logger.info("更新發文計數，今日已發文：%d/%d，下次發文時間：%s，等待：%d 秒",
                self.today_post_count, self.max_daily_posts,
                self.next_post_time.strftime("%Y-%m-%d %H:%M:%S"),
                wait_time)
                
            # 等待到下次發文時間
            await asyncio.sleep(wait_time)
            
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
            "allowed_hours": "晚上20點至凌晨2點",
            "today_post_count": f"{self.today_post_count}/{self.max_daily_posts}",
            "post_plan": [dt.strftime("%H:%M:%S") for dt in self.daily_post_plan] if self.daily_post_plan else []
        } 