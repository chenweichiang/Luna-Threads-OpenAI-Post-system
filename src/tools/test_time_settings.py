#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Version: 2024.03.31 (v1.1.6)
Author: ThreadsPoster Team
Description: 測試腳本：驗證時間設定是否正確從.env文件讀取
Last Modified: 2024.03.31
Changes:
- 改進時間設定測試功能
- 移至工具目錄統一管理
"""

import os
import sys
import pytz
from datetime import datetime

# 添加專案根目錄到路徑，以便能夠導入相關模組
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from dotenv import load_dotenv
from config import Config
from time_controller import TimeController

def test_settings():
    """測試各個類的時間設定"""
    # 載入環境變數
    load_dotenv(override=True)
    
    # 測試Config類
    config = Config()
    print("===== Config類時間設定 =====")
    print(f"主要發文時段：{config.PRIME_POST_START}-{config.PRIME_POST_END}時")
    print(f"每日發文數範圍：{config.MIN_POSTS_PER_DAY}-{config.MAX_POSTS_PER_DAY}")
    print(f"主要時段發文比例：{config.PRIME_TIME_POST_RATIO}")
    print(f"情緒/心情模式時間：")
    print(f"- 早晨：{config.MOOD_MORNING_START}-{config.MOOD_MORNING_END}時")
    print(f"- 中午：{config.MOOD_NOON_START}-{config.MOOD_NOON_END}時")
    print(f"- 下午：{config.MOOD_AFTERNOON_START}-{config.MOOD_AFTERNOON_END}時")
    print(f"- 晚上：{config.MOOD_EVENING_START}-{config.MOOD_EVENING_END}時")
    print("")
    
    # 測試TimeController類
    tc = TimeController(config)
    print("===== TimeController類時間設定 =====")
    print(f"發文間隔設定：")
    print(f"- 黃金時段：{tc.post_interval['prime_time']} 秒")
    print(f"- 一般時段：{tc.post_interval['other_time']} 秒")
    print(f"允許發文時間範圍：{tc.allowed_hours.start}-{tc.allowed_hours.stop-1}時")
    print(f"黃金時段定義：")
    print(f"- 午間：{tc.prime_time_afternoon_start}-{tc.prime_time_afternoon_end}時")
    print(f"- 晚間：{tc.prime_time_evening_start}-{tc.prime_time_evening_end}時")
    print("")
    
    # 顯示當前時間資訊
    tz = pytz.timezone("Asia/Taipei")
    now = datetime.now(tz)
    print(f"當前時間: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"是否為黃金時段: {tc._is_prime_time()}")
    print(f"當前建議發文間隔: {tc.get_interval()} 秒")
    print("")
    
    print("所有時間設定都從.env文件中讀取")

if __name__ == "__main__":
    test_settings() 