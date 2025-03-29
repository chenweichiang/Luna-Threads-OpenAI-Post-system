import datetime
import pytz
import random
from typing import Optional

class TimeController:
    def __init__(self, timezone: str = "Asia/Taipei"):
        """初始化時間控制器。

        Args:
            timezone (str): 時區設定，預設為台北時區
        """
        self.timezone = pytz.timezone(timezone)
        self._last_post_time = None
        self._next_post_time = None
        self._daily_post_count = 0
        self._last_reset_date = None

    def get_current_time(self) -> datetime.datetime:
        """獲取當前時間（考慮時區）。"""
        return datetime.datetime.now(self.timezone)

    def should_reset_daily_count(self) -> bool:
        """檢查是否需要重置每日發文計數。"""
        current_time = self.get_current_time()
        current_date = current_time.date()
        
        if self._last_reset_date is None or current_date > self._last_reset_date:
            self._last_reset_date = current_date
            return True
        return False

    def reset_daily_count(self) -> None:
        """重置每日發文計數。"""
        self._daily_post_count = 0
        self._last_reset_date = self.get_current_time().date()

    def increment_post_count(self) -> None:
        """增加發文計數。"""
        self._daily_post_count += 1

    def get_daily_post_count(self) -> int:
        """獲取當日發文計數。"""
        return self._daily_post_count

    def is_prime_time(self) -> bool:
        """檢查當前是否為黃金發文時段。"""
        current_time = self.get_current_time()
        hour = current_time.hour
        
        # 定義黃金時段：12-14點（午餐時間）和 19-22點（晚間時間）
        return (12 <= hour <= 14) or (19 <= hour <= 22)

    def calculate_next_post_time(self, min_interval: int = 3600, max_interval: int = 7200) -> datetime.datetime:
        """計算下一次發文時間。

        Args:
            min_interval (int): 最小發文間隔（秒），預設1小時
            max_interval (int): 最大發文間隔（秒），預設2小時

        Returns:
            datetime.datetime: 下一次發文時間
        """
        current_time = self.get_current_time()
        
        # 如果是黃金時段，縮短發文間隔
        if self.is_prime_time():
            min_interval = min_interval // 2
            max_interval = max_interval // 2
        
        # 隨機選擇發文間隔
        interval = random.randint(min_interval, max_interval)
        next_time = current_time + datetime.timedelta(seconds=interval)
        
        # 避免在深夜發文（23點到早上7點）
        while 23 <= next_time.hour or next_time.hour <= 7:
            next_time = next_time + datetime.timedelta(hours=8)
        
        self._next_post_time = next_time
        return next_time

    def should_post(self, max_daily_posts: int = 3) -> bool:
        """檢查是否應該發文。

        Args:
            max_daily_posts (int): 每日最大發文數，預設3篇

        Returns:
            bool: 是否應該發文
        """
        # 檢查是否需要重置每日計數
        if self.should_reset_daily_count():
            self.reset_daily_count()
        
        # 檢查是否超過每日發文限制
        if self._daily_post_count >= max_daily_posts:
            return False
        
        # 如果沒有設定下一次發文時間，立即計算
        if self._next_post_time is None:
            self.calculate_next_post_time()
            return True
        
        current_time = self.get_current_time()
        return current_time >= self._next_post_time

    def get_next_post_time(self) -> Optional[datetime.datetime]:
        """獲取下一次預計發文時間。"""
        return self._next_post_time

    def update_last_post_time(self) -> None:
        """更新最後一次發文時間。"""
        self._last_post_time = self.get_current_time()
        self.increment_post_count()
        self.calculate_next_post_time()  # 立即計算下一次發文時間 