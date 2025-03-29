"""
Version: 2024.03.30
Author: ThreadsPoster Team
Description: 時間控制器，負責管理發文時間和頻率控制
Last Modified: 2024.03.30
Changes:
- 優化時間控制邏輯
- 改進發文頻率計算
- 加強時區處理
- 優化排程機制
- 改進時間驗證
"""

import datetime
import pytz
import random
import os
from typing import Optional
import logging

class TimeController:
    def __init__(self, config):
        """初始化時間控制器"""
        self._config = config
        self._timezone = config.TIMEZONE
        self._min_daily_posts = config.MIN_POSTS_PER_DAY
        self._max_daily_posts = config.MAX_POSTS_PER_DAY
        self._prime_post_start = config.PRIME_POST_START
        self._prime_post_end = config.PRIME_POST_END
        self._prime_time_post_ratio = config.PRIME_TIME_POST_RATIO
        self._daily_post_count = 0
        self._last_post_time = None
        self._last_reset_date = None
        self._reset_daily_count()

    def _reset_daily_count(self) -> None:
        """重置每日發文計數"""
        current_date = self.get_current_time().date()
        if self._last_reset_date != current_date:
            self._daily_post_count = 0
            self._last_reset_date = current_date
            logging.info(f"重置每日發文計數，目前已發文 {self._daily_post_count} 篇")

    def get_current_time(self) -> datetime:
        """獲取當前時間（考慮時區）"""
        return datetime.datetime.now(self._timezone)

    def is_prime_time(self) -> bool:
        """判斷是否為主要發文時段"""
        current_hour = self.get_current_time().hour
        if self._prime_post_start > self._prime_post_end:  # 跨日情況
            return current_hour >= self._prime_post_start or current_hour < self._prime_post_end
        else:
            return self._prime_post_start <= current_hour < self._prime_post_end

    def increment_post_count(self) -> None:
        """增加發文計數"""
        self._daily_post_count += 1
        self._last_post_time = self.get_current_time()
        logging.info(f"增加發文計數，目前已發文 {self._daily_post_count} 篇")

    def should_post(self) -> bool:
        """判斷是否應該發文"""
        self._reset_daily_count()

        # 檢查是否超過每日最大發文數
        if self._daily_post_count >= self._max_daily_posts:
            logging.info(f"已達到每日發文上限 {self._max_daily_posts} 篇")
            return False

        current_time = self.get_current_time()
        hours_left = 24 - current_time.hour
        posts_left = self._min_daily_posts - self._daily_post_count

        # 如果還沒達到最小發文數且時間不多，提高發文機率
        if posts_left > 0 and hours_left < 6:
            logging.info(f"距離結束還有 {hours_left} 小時，還需發文 {posts_left} 篇")
            return True

        # 根據時段決定發文間隔
        if self.is_prime_time():
            min_interval = self._config.SYSTEM_CONFIG["post_interval"]["prime_time"]["min"]
            max_interval = self._config.SYSTEM_CONFIG["post_interval"]["prime_time"]["max"]
        else:
            min_interval = self._config.SYSTEM_CONFIG["post_interval"]["other_time"]["min"]
            max_interval = self._config.SYSTEM_CONFIG["post_interval"]["other_time"]["max"]

        # 如果是第一篇文章
        if self._last_post_time is None:
            return True

        # 計算距離上一篇文章的時間間隔
        time_since_last_post = (current_time - self._last_post_time).total_seconds()
        random_interval = random.randint(min_interval, max_interval)

        # 根據時段和剩餘發文數調整發文機率
        if time_since_last_post >= random_interval:
            if self.is_prime_time():
                post_probability = self._prime_time_post_ratio
            else:
                post_probability = 1 - self._prime_time_post_ratio

            # 根據剩餘發文數調整機率
            if posts_left > 0:
                post_probability *= (posts_left / hours_left) if hours_left > 0 else 1

            return random.random() < post_probability

        return False

    def calculate_next_post_time(self) -> datetime.datetime:
        """計算下一次發文時間。"""
        current_time = self.get_current_time()
        
        # 根據時段決定發文間隔
        if self.is_prime_time():
            # 主要時段：15-45分鐘
            min_interval = 15 * 60  # 15分鐘
            max_interval = 45 * 60  # 45分鐘
        else:
            # 其他時段：1-3小時
            min_interval = 60 * 60   # 1小時
            max_interval = 180 * 60  # 3小時
        
        # 隨機選擇發文間隔
        interval = random.randint(min_interval, max_interval)
        next_time = current_time + datetime.timedelta(seconds=interval)
        
        # 如果下一次發文時間在主要時段，縮短間隔
        if self.is_prime_time():
            interval = random.randint(15 * 60, 45 * 60)  # 15-45分鐘
            next_time = current_time + datetime.timedelta(seconds=interval)
        
        return next_time

    def get_next_post_time(self) -> Optional[datetime.datetime]:
        """獲取下一次預計發文時間。"""
        return self.calculate_next_post_time()

    def get_daily_post_count(self) -> int:
        """獲取當日發文計數。"""
        return self._daily_post_count

    def update_last_post_time(self) -> None:
        """更新最後一次發文時間。"""
        self._last_post_time = self.get_current_time()
        self.increment_post_count()
        self.calculate_next_post_time()  # 立即計算下一次發文時間 