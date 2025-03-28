"""
ThreadsPoster 工具函數
Version: 1.0.0
Last Updated: 2025-03-29
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

def sanitize_text(text: str, max_length: int = 25) -> str:
    """清理和格式化文本"""
    if not text or len(text.strip()) == 0:
        return ""
        
    # 修正縮寫
    text = re.sub(r'\bB\b', 'BL', text)
    text = re.sub(r'\bSw\b', 'Switch', text)
    text = re.sub(r'\bMac\b', 'Macbook', text)
    text = re.sub(r'\bPC\b', '電腦', text)
    text = re.sub(r'\bVR\b', 'Quest', text)
    text = re.sub(r'\bApp\b', 'APP', text)
    text = re.sub(r'\bAI\b', '人工智慧', text)
    
    # 移除引號
    text = re.sub(r'[「」『』""'']', '', text)
    
    # 移除多餘的標點符號
    text = re.sub(r'[,，]{2,}', '，', text)  # 重複的逗號
    text = re.sub(r'[.。]{2,}', '。', text)  # 重複的句號
    text = re.sub(r'[!！]{2,}', '！', text)  # 重複的驚嘆號
    text = re.sub(r'[?？]{2,}', '？', text)  # 重複的問號
    text = re.sub(r'[\s]+', ' ', text)  # 多餘的空白
    text = re.sub(r'[,，。][,，。]+', '。', text)  # 多個不同的句號
    text = re.sub(r'[,，。][!！?？]', lambda m: m.group(0)[-1], text)  # 句號後的驚嘆號或問號，保留後者
    text = re.sub(r'[,，]([!！?？])', lambda m: m.group(1), text)  # 逗號後的驚嘆號或問號，保留後者
    
    # 修正不完整的詞語
    text = re.sub(r'人工智慧生成同[!！?？]', '人工智慧生成的同人圖好精緻！', text)
    text = re.sub(r'人工智慧畫的[!！?？]', '人工智慧畫的圖好精美！', text)
    text = re.sub(r'人工智慧做的[!！?？]', '人工智慧做的立繪好可愛！', text)
    text = re.sub(r'人工智慧生成[!！?？]', '人工智慧生成的內容好棒！', text)
    text = re.sub(r'Switch上玩的[!！?？]', 'Switch上玩的遊戲好好玩！', text)
    text = re.sub(r'Quest看的[!！?？]', 'Quest看的動畫好精彩！', text)
    text = re.sub(r'BL漫畫的[!！?？]', 'BL漫畫的劇情好精彩！', text)
    text = re.sub(r'BL遊戲的[!！?？]', 'BL遊戲的劇情好甜！', text)
    text = re.sub(r'BL動畫的[!！?？]', 'BL動畫的畫風好美！', text)
    text = re.sub(r'新的遊戲[!！?？]', '新的遊戲好好玩！', text)
    text = re.sub(r'新的動畫[!！?？]', '新的動畫好精彩！', text)
    text = re.sub(r'新的漫畫[!！?？]', '新的漫畫好好看！', text)
    text = re.sub(r'新的APP[!！?？]', '新的APP好實用！', text)
    text = re.sub(r'新的功能[!！?？]', '新的功能好方便！', text)
    text = re.sub(r'新的更新[!！?？]', '新的更新好貼心！', text)
    
    # 修正常見的不完整句子
    text = re.sub(r'對我的[!！?？]', '對我的感覺！', text)
    text = re.sub(r'這麼[!！?？]', '這麼棒！', text)
    text = re.sub(r'好想[!！?？]', '好想要！', text)
    text = re.sub(r'不行[!！?？]', '不行啦！', text)
    text = re.sub(r'好棒[!！?？]', '好棒啊！', text)
    text = re.sub(r'好可愛[!！?？]', '好可愛啊！', text)
    text = re.sub(r'好厲害[!！?？]', '好厲害啊！', text)
    text = re.sub(r'好喜歡[!！?？]', '好喜歡啊！', text)
    text = re.sub(r'好期待[!！?？]', '好期待啊！', text)
    text = re.sub(r'好興奮[!！?？]', '好興奮啊！', text)
    
    # 修正句子結構
    text = re.sub(r'它的角色和[!！?？]', '它的角色設計超棒的！', text)
    text = re.sub(r'這個遊戲的[!！?？]', '這個遊戲的劇情好精彩！', text)
    text = re.sub(r'新的功能[!！?？]', '新的功能超好用！', text)
    text = re.sub(r'這部動畫的[!！?？]', '這部動畫的畫風好美！', text)
    text = re.sub(r'這款APP的[!！?？]', '這款APP的設計好貼心！', text)
    text = re.sub(r'這個更新[!！?？]', '這個更新太讚了！', text)
    text = re.sub(r'這個劇情[!！?？]', '這個劇情好精彩！', text)
    text = re.sub(r'這個聲優[!！?？]', '這個聲優配音好棒！', text)
    text = re.sub(r'這個畫面[!！?？]', '這個畫面太美了！', text)
    text = re.sub(r'這個效果[!！?？]', '這個效果好厲害！', text)
    text = re.sub(r'這個設計[!！?？]', '這個設計好貼心！', text)
    text = re.sub(r'這個體驗[!！?？]', '這個體驗好棒！', text)
    text = re.sub(r'這個感覺[!！?？]', '這個感覺好舒服！', text)
    text = re.sub(r'這個操作[!！?？]', '這個操作好順手！', text)
    text = re.sub(r'這個介面[!！?？]', '這個介面好漂亮！', text)
    text = re.sub(r'這個功能[!！?？]', '這個功能好實用！', text)
    text = re.sub(r'這個表現[!！?？]', '這個表現好出色！', text)
    text = re.sub(r'這個配音[!！?？]', '這個配音好動聽！', text)
    text = re.sub(r'這個故事[!！?？]', '這個故事好感人！', text)
    text = re.sub(r'這個結局[!！?？]', '這個結局好意外！', text)
    
    # 確保句子結尾有適當的標點符號
    if not re.search(r'[。！？]$', text):
        text = text.rstrip('，') + '！'
    
    # 移除開頭的標點符號
    text = re.sub(r'^[,，。!！?？\s]+', '', text)
    
    # 如果文字太長，截斷到最後一個完整句子
    if len(text) > max_length:
        sentences = re.split(r'([。！？])', text)
        result = ''
        for i in range(0, len(sentences)-1, 2):
            if len(result + sentences[i] + sentences[i+1]) <= max_length:
                result += sentences[i] + sentences[i+1]
            else:
                break
        text = result if result else text[:max_length-1] + '！'
    
    # 確保文字長度至少10個字
    if len(text) < 10:
        return ""
        
    # 根據關鍵字選擇emoji
    emoji = ''
    if any(word in text for word in ['BL', 'CP', '配對', '戀愛', '心動', '害羞']):
        emoji = '🥰'
    elif any(word in text for word in ['遊戲', 'Switch', 'Quest', '玩']):
        emoji = '🎮'
    elif any(word in text for word in ['動畫', '漫畫', '番', '作品']):
        emoji = '✨'
    elif any(word in text for word in ['人工智慧', '科技', '新功能']):
        emoji = '🤖'
    elif any(word in text for word in ['iPhone', 'Macbook', '手機', '電腦']):
        emoji = '📱'
    
    # 如果沒有找到對應的emoji，使用預設的
    if not emoji:
        emoji = '💕'
    
    return text + emoji

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