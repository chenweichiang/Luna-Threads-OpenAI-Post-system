"""
Version: 2024.03.30
Author: ThreadsPoster Team
Description: 工具函數模組，提供各種通用功能
Last Modified: 2024.03.30
Changes:
- 優化文本處理功能
- 改進時間處理邏輯
- 加強錯誤處理
- 統一日誌路徑
- 優化配置讀取
"""

import json
import logging
import os
import re
import pytz
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Tuple
from src.config import Config
from src.exceptions import ValidationError
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 創建全局配置實例
config = Config(skip_validation=True)

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
    """獲取當前時間（使用配置中的時區）"""
    # 先取得 UTC 時間
    utc_now = datetime.now(pytz.UTC)
    # 轉換到目標時區
    local_time = utc_now.astimezone(config.POSTING_TIMEZONE)
    return local_time

def format_time(dt: datetime, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """格式化時間"""
    try:
        if not dt:
            return ''
        return dt.strftime(format_str)
    except Exception as e:
        logging.error(f"格式化時間時發生錯誤：{str(e)}")
        return ''

def sanitize_text(text: str) -> str:
    """清理文本，保持原始文本的完整性。
    智能處理文本，盡可能保留原始內容。
    """
    if not text:
        return text

    # 定義表情符號
    emoji_pattern = r'[\U0001F300-\U0001F9FF]|[\u2600-\u26FF]|[\u2700-\u27BF]'
    
    # 提取表情符號
    emojis = re.findall(emoji_pattern, text)
    
    # 移除多餘的表情符號，只保留最後兩個
    if len(emojis) > 2:
        emojis = emojis[-2:]
    
    # 移除文本中的表情符號，但保留位置
    text_without_emojis = re.sub(emoji_pattern, '', text)
    
    # 基本清理
    text_without_emojis = text_without_emojis.strip()
    text_without_emojis = re.sub(r'[\s]+', ' ', text_without_emojis)  # 清理多餘空格
    
    # 移除開頭的標點符號
    text_without_emojis = re.sub(r'^[。!！?？\s]+', '', text_without_emojis)
    
    # 檢查結尾標點
    valid_endings = ['！', '。', '？', '～']
    
    # 如果文本以表情符號結尾，先移除它們
    while text_without_emojis and text_without_emojis[-1] in ['～', '~']:
        text_without_emojis = text_without_emojis[:-1].strip()
    
    # 檢查是否有有效的結尾標點
    has_valid_ending = any(text_without_emojis.endswith(p) for p in valid_endings)
    
    # 如果沒有有效的結尾標點
    if not has_valid_ending:
        # 如果最後一個字符是標點符號
        if text_without_emojis[-1] in ['，', ',', '、', '；', ';']:
            text_without_emojis = text_without_emojis[:-1] + '！'
        else:
            text_without_emojis = text_without_emojis + '！'
    
    # 檢查是否包含完整句子
    if '，' in text_without_emojis or ',' in text_without_emojis:
        parts = re.split('[，,]', text_without_emojis)
        # 如果最後一部分太短，而且不是完整的句子
        if len(parts[-1].strip()) <= 5 and not any(word in parts[-1] for word in ['嗎', '呢', '吧', '啊']):
            text_without_emojis = ''.join(parts[:-1]) + '！'
    
    # 重新添加表情符號
    result = text_without_emojis
    if emojis:
        result = result + ''.join(emojis)
    
    return result

def safe_json_loads(json_str: str) -> Optional[Any]:
    """安全的 JSON 解析"""
    try:
        if not json_str:
            return None
        return json.loads(json_str)
    except Exception as e:
        logging.error(f"JSON 解析時發生錯誤：{str(e)}")
        return None

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

async def check_latest_posts(db_handler, limit=3, print_result=True):
    """檢查最近的文章

    Args:
        db_handler: 資料庫處理器
        limit: 要檢查的文章數量
        print_result: 是否列印結果

    Returns:
        List: 文章列表
    """
    posts = await db_handler.get_latest_posts(limit)
    
    if print_result:
        print(f"找到 {len(posts)} 篇文章")
        for post in posts:
            print(f'文章ID: {post.get("post_id", "未知")}\n內容: {post.get("content", "無內容")}\n')
    
    return posts