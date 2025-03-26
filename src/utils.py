"""
ThreadsPoster 工具函數
"""

import json
import logging
import os
import re
import pytz
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from src.config import Config
from src.exceptions import ValidationError
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def validate_environment():
    """驗證環境變數設定"""
    load_dotenv()  # 載入 .env 檔案
    
    required_vars = [
        'THREADS_ACCESS_TOKEN',
        'THREADS_APP_ID',
        'THREADS_APP_SECRET',
        'OPENAI_API_KEY',
        'MONGODB_URI',
        'MONGODB_DB'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"缺少必要的環境變數: {', '.join(missing_vars)}")

def get_current_time():
    """獲取當前時間（UTC）"""
    return datetime.now(pytz.UTC)

def format_time(dt: datetime) -> str:
    """
    格式化時間為 ISO 8601 格式
    
    Args:
        dt: 要格式化的時間
        
    Returns:
        str: 格式化後的時間字串
    """
    return dt.isoformat()

def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """
    清理文本，移除多餘的空格和換行符，並限制長度
    
    Args:
        text: 要清理的文本
        max_length: 可選的最大長度限制
        
    Returns:
        清理後的文本
    """
    # 移除多餘的空格和換行符
    text = ' '.join(text.split())
    
    # 如果指定了最大長度，確保不會切斷單詞
    if max_length and len(text) > max_length:
        words = text[:max_length+1].split()
        if len(words) > 1:
            words.pop()
        text = ' '.join(words)
    
    return text

def safe_json_loads(json_str: str) -> Dict:
    """安全載入 JSON
    
    Args:
        json_str: JSON 字串
        
    Returns:
        解析後的字典，失敗則回傳空字典
    """
    try:
        return json.loads(json_str)
    except Exception as e:
        logger.error(f"JSON 解析失敗: {str(e)}")
        return {}

def get_posting_probability():
    """根據當前時間獲取發文機率"""
    current_hour = get_current_time().hour
    schedule = config.CHARACTER_PROFILE['posting_schedule']
    
    if 9 <= current_hour < 12:
        return schedule['morning']['probability']
    elif 14 <= current_hour < 18:
        return schedule['afternoon']['probability']
    elif 19 <= current_hour < 23:
        return schedule['evening']['probability']
    return 0

def get_suggested_topics():
    """根據當前時間獲取建議的發文主題"""
    current_hour = get_current_time().hour
    schedule = config.CHARACTER_PROFILE['posting_schedule']
    
    if 9 <= current_hour < 12:
        return schedule['morning']['topics']
    elif 14 <= current_hour < 18:
        return schedule['afternoon']['topics']
    elif 19 <= current_hour < 23:
        return schedule['evening']['topics']
    return []