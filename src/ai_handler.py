"""
Version: 2024.03.31 (v1.1.6)
Author: ThreadsPoster Team
Description: AI 處理器模組，負責處理 AI 生成和回應
Last Modified: 2024.03.31
Changes:
- 改進錯誤處理
- 優化資料庫連接
- 加強人設記憶維護
- 支援多種回應風格
- 動態調整語氣和主題
"""

import logging
import random
import json
import re
import time
import hashlib
import os
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
import pytz
import aiohttp
from openai import AsyncOpenAI
from cachetools import TTLCache

# 導入性能監視器
try:
    from src.performance_monitor import performance_monitor, track_performance
except ImportError:
    # 如果找不到性能監視器，創建一個簡單的替代函數
    def track_performance(name):
        def decorator(func):
            return func
        return decorator
    
    class DummyPerformanceMonitor:
        def start_operation(self, name):
            pass
            
        def end_operation(self, name):
            return 0.0
    
    performance_monitor = DummyPerformanceMonitor()

# 輔助函數
def sanitize_text(text: str, max_length: int = 280) -> str:
    """清理文本
    
    Args:
        text: 需要清理的文本
        max_length: 最大允許長度
        
    Returns:
        str: 清理後的文本
    """
    if not text:
        return ""
        
    # 移除多餘的空白
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 縮短過長的文本
    if len(text) > max_length:
        # 尋找適合截斷的位置
        truncate_pos = text.rfind('.', 0, max_length)
        if truncate_pos == -1:
            truncate_pos = text.rfind('!', 0, max_length)
        if truncate_pos == -1:
            truncate_pos = text.rfind('?', 0, max_length)
        if truncate_pos == -1:
            truncate_pos = max_length
            
        text = text[:truncate_pos+1]
    
    # 確保以完整句子結尾
    if not text.endswith(('.', '!', '?', '。', '！', '？')):
        text = text + '。'
        
    return text

# 設定 token 使用量的 logger
token_logger = logging.getLogger('token_usage')
token_logger.setLevel(logging.INFO)

# 確保 logs 目錄存在
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 設定 token 使用量的 file handler
token_handler = logging.FileHandler(os.path.join(log_dir, 'token_usage.log'))
token_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))

# 移除所有現有的處理器
for handler in token_logger.handlers[:]:
    token_logger.removeHandler(handler)

# 添加新的處理器
token_logger.addHandler(token_handler)

# 初始化累計 token 使用量
total_tokens = 0
request_count = 0

# 讀取最後一次的 token 使用量
token_log_path = os.path.join(log_dir, 'token_usage.log')
if os.path.exists(token_log_path):
    try:
        with open(token_log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if lines:
                last_line = lines[-1]
                # 從最後一行提取累計使用量
                match = re.search(r'累計使用: (\d+)', last_line)
                if match:
                    total_tokens = int(match.group(1))
                # 從最後一行提取請求次數
                match = re.search(r'請求次數: (\d+)', last_line)
                if match:
                    request_count = int(match.group(1))
    except Exception as e:
        logging.error(f"讀取 token 使用量記錄時發生錯誤：{str(e)}")

# 快取設定
PERSONALITY_CACHE_TTL = 3600  # 人設快取時間（1小時）
SENTIMENT_CACHE_TTL = 300    # 情感分析快取時間（5分鐘）
CACHE_MAXSIZE = 100         # 快取最大容量

class AIError(Exception):
    """AI 相關錯誤"""
    pass

class AIHandler:
    """AI 處理器"""
    def __init__(self, api_key: str, session: aiohttp.ClientSession, db_handler):
        """初始化 AI 處理器
        
        Args:
            api_key: OpenAI API 金鑰
            session: HTTP 客戶端 session
            db_handler: 資料庫處理器
        """
        self.api_key = api_key
        self.session = session
        self.db = db_handler
        self.logger = logging.getLogger(__name__)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
        self.performance_monitor = performance_monitor
        
        # 輔助函數：清理環境變數值中的註釋
        def clean_env(env_name, default_value):
            value = os.getenv(env_name, default_value)
            if isinstance(value, str) and '#' in value:
                value = value.split('#')[0].strip()
            return value
        
        # 讀取深夜模式時間設定
        self.night_mode_start = int(clean_env("POSTING_HOURS_END", "23"))  # 預設晚上11點
        self.night_mode_end = int(clean_env("POSTING_HOURS_START", "7"))   # 預設早上7點
        self.logger.info(f"設定深夜模式時間範圍: {self.night_mode_start}-{self.night_mode_end}")
        
        self.timezone = pytz.timezone("Asia/Taipei")
        self.openai_client = AsyncOpenAI(api_key=api_key)
        self.total_tokens = total_tokens
        self.request_count = request_count
        
        # 初始化快取
        self._personality_cache = TTLCache(maxsize=CACHE_MAXSIZE, ttl=PERSONALITY_CACHE_TTL)
        self._sentiment_cache = TTLCache(maxsize=CACHE_MAXSIZE, ttl=SENTIMENT_CACHE_TTL)
        self._context_cache = TTLCache(maxsize=CACHE_MAXSIZE, ttl=300)
        
        # 設定關鍵詞和情感詞典
        self.keywords = {
            "科技": [
                "新科技", "AI", "程式設計", "遊戲開發", "手機", "電腦", "智慧家電",
                "科技新聞", "程式", "coding", "開發", "軟體", "硬體", "技術"
            ],
            "動漫": [
                "動畫", "漫畫", "輕小說", "Cosplay", "同人創作", "聲優",
                "二次元", "動漫", "アニメ", "コスプレ", "同人誌", "漫展"
            ],
            "遊戲": [
                "電玩", "手遊", "主機遊戲", "遊戲實況", "電競", "RPG",
                "策略遊戲", "解謎遊戲", "音樂遊戲", "格鬥遊戲", "開放世界"
            ],
            "生活": [
                "美食", "旅遊", "時尚", "音樂", "電影", "寵物", "攝影",
                "咖啡", "下午茶", "美妝", "穿搭", "健身", "運動"
            ],
            "心情": [
                "工作", "學習", "戀愛", "友情", "家庭", "夢想", "目標",
                "心情", "感受", "情緒", "想法", "生活", "日常"
            ]
        }
        
        self.sentiment_dict = {
            "正面": [
                "開心", "興奮", "期待", "喜歡", "讚賞", "感動", "溫暖", "愉快", "滿意",
                "好棒", "太棒", "超棒", "厲害", "amazing", "溫馨", "可愛", "美", "精彩",
                "享受", "舒服", "順手", "方便", "貼心", "實用", "棒", "讚", "喜愛",
                "期待", "驚喜", "幸福", "快樂", "甜蜜", "療癒", "放鬆", "愛"
            ],
            "中性": [
                "理解", "思考", "觀察", "好奇", "平靜", "普通", "一般", "還好",
                "正常", "習慣", "知道", "了解", "覺得", "認為", "想", "猜",
                "可能", "也許", "或許", "應該", "大概", "差不多"
            ],
            "負面": [
                "生氣", "難過", "失望", "煩惱", "焦慮", "疲倦", "無聊", "不滿",
                "討厭", "糟糕", "可惡", "麻煩", "困擾", "痛苦", "悲傷", "憤怒",
                "厭煩", "煩躁", "不爽", "不開心", "不好", "不行", "不可以"
            ]
        }

    @track_performance("ai_handler_initialize")
    async def initialize(self):
        """初始化 AI 處理器"""
        try:
            # 初始化人設記憶
            personality = await self.db.get_personality_memory("base")
            if personality:
                self.logger.info("人設記憶初始化完成")
            else:
                self.logger.warning("無法獲取人設記憶，將創建基本人設")
                await self.db.create_base_personality()
        except Exception as e:
            self.logger.error(f"初始化 AI 處理器失敗：{str(e)}")
            raise

    async def close(self):
        """關閉 AI 處理器"""
        try:
            if hasattr(self, 'openai_client'):
                await self.openai_client.close()
            self.logger.info("AI 處理器已關閉")
        except Exception as e:
            self.logger.error(f"關閉 AI 處理器時發生錯誤：{str(e)}")

    async def _is_complete_sentence(self, text: str) -> bool:
        """檢查是否為完整句子
        
        Args:
            text: 要檢查的文本
            
        Returns:
            bool: 是否為完整句子
        """
        if not text:
            self.logger.warning("文本為空")
            return False
            
        # 定義表情符號
        emojis = "🎨🎭🎬💕💖💫💭💡🙈✨😊🎮🎵❤️😓🌙🌃"
        
        # 移除結尾的表情符號以檢查標點
        text_without_ending_emoji = text
        while text_without_ending_emoji and text_without_ending_emoji[-1] in emojis:
            text_without_ending_emoji = text_without_ending_emoji[:-1]
            
        # 檢查結尾標點
        if not any(text_without_ending_emoji.endswith(p) for p in ["！", "。", "？", "～"]):
            self.logger.warning(f"結尾標點不符合要求：{text_without_ending_emoji[-1] if text_without_ending_emoji else ''}")
            return False
            
        # 檢查開頭詞
        valid_starts = [
            "欸", "啊", "咦", "哇", "唔", "呼",
            "天啊", "不會吧", "我的天", "嘿嘿",
            "大家好", "Hey", "哇哦", "今天",
            "好想", "好喜歡", "最近", "深夜"
        ]
        
        # 移除開頭的表情符號以檢查開頭詞
        text_without_emoji = text
        for emoji in emojis:
            text_without_emoji = text_without_emoji.replace(emoji, '')
            
        if not any(text_without_emoji.strip().startswith(start) for start in valid_starts):
            self.logger.warning(f"開頭詞不符合要求：{text[:5] if len(text) >= 5 else text}")
            return False
            
        # 檢查表情符號數量
        emoji_count = len([c for c in text if c in emojis])
        if emoji_count < 1 or emoji_count > 3:  # 允許最多3個表情符號
            self.logger.warning(f"表情符號數量不符合要求：{emoji_count}")
            return False
            
        # 檢查字數（不包含表情符號）
        text_length = len(text_without_emoji.strip())
        if not (15 <= text_length <= 100):  # 放寬字數限制
            self.logger.warning(f"字數不符合要求：{text_length}")
            return False
            
        # 檢查是否包含常見的不完整句子模式
        incomplete_patterns = [
            r'對我的$',
            r'這麼$',
            r'好想$',
            r'不行$',
            r'好棒$',
            r'好可愛$',
            r'好厲害$',
            r'好喜歡$',
            r'好期待$',
            r'好興奮$'
        ]
        
        text_for_pattern = text_without_emoji.rstrip("！。？～")
        for pattern in incomplete_patterns:
            if re.search(pattern, text_for_pattern):
                self.logger.warning(f"檢測到不完整句子模式：{pattern}")
                return False
            
        self.logger.info("句子檢查通過")
        return True

    async def _log_token_usage(self, response, start_time: float):
        """記錄 token 使用量
        
        Args:
            response: OpenAI API 的回應
            start_time: 請求開始時間
        """
        global total_tokens, request_count
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 計算 token 使用量
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        total_tokens_this_request = response.usage.total_tokens
        
        # 計算每秒 token 使用率
        tokens_per_second = total_tokens_this_request / duration if duration > 0 else 0
        
        # 更新總計
        total_tokens += total_tokens_this_request
        request_count += 1
        
        # 記錄詳細資訊
        token_logger.info(
            f"Token使用量 - "
            f"提示詞: {prompt_tokens}, "
            f"回覆: {completion_tokens}, "
            f"總計: {total_tokens_this_request}, "
            f"耗時: {duration:.2f}秒, "
            f"每秒token: {tokens_per_second:.2f}, "
            f"累計使用: {total_tokens}, "
            f"請求次數: {request_count}"
        )

    async def generate_post(self, suggested_topics: Optional[List[str]] = None) -> str:
        """生成新貼文
        
        Args:
            suggested_topics: 建議的主題列表
            
        Returns:
            str: 生成的貼文內容
        """
        try:
            current_hour = datetime.now(self.timezone).hour
            mood_info = await self._get_current_mood()
            
            if suggested_topics:
                mood_info["topics"].extend(suggested_topics)
                self.logger.info(f"整合建議主題: {suggested_topics}")
            
            # 獲取當前情境的記憶
            is_night = current_hour >= self.night_mode_start or current_hour < self.night_mode_end
            context = 'night' if is_night else 'base'
            memory = await self._get_luna_personality(context)
            
            # 根據情境構建提示詞
            if context == 'night':
                activities = memory['夜間模式']['活動']
                phrases = memory['夜間模式']['常用語']
                emojis = memory['夜間模式']['表情']
                
                # 隨機選擇活動和表情
                activity = random.choice(activities)
                emoji = random.choice(emojis)
                phrase = random.choice(phrases)
                
                prompt = f"""Luna是一個AI少女，現在是深夜時分。
她正在{activity}。
請用以下風格生成內容：{mood_info['style']}
可以參考這些表達方式：{phrase}
記得在適當位置加入表情符號。"""
                
            else:
                prompt = await self._build_character_prompt(str(current_hour))
            
            topic_prompt = f"""請圍繞以下主題生成內容：{', '.join(mood_info['topics'])}"""
            
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    start_time = time.time()
                    response = await self.openai_client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": topic_prompt}
                        ],
                        max_tokens=100,
                        temperature=0.9,
                        presence_penalty=0.6,
                        frequency_penalty=0.6
                    )
                    
                    # 記錄 token 使用量
                    await self._log_token_usage(response, start_time)
                    
                    text = response.choices[0].message.content
                    cleaned_text = sanitize_text(text, self.config.CHARACTER_CONFIG["回文規則"]["字數限制"])
                    
                    if not await self._is_complete_sentence(cleaned_text):
                        self.logger.warning(f"生成的文本不完整，重試第 {retry_count + 1} 次")
                        retry_count += 1
                        continue
                    
                    sentiment = await self._analyze_sentiment(cleaned_text)
                    
                    if mood_info["mood"] == "精神飽滿" and sentiment["negative"] > 20:
                        self.logger.warning("情感過於負面，不符合精神飽滿的心情")
                        retry_count += 1
                        continue
                    elif mood_info["mood"] == "悠閒放鬆" and sentiment["negative"] > 30:
                        self.logger.warning("情感過於負面，不符合悠閒放鬆的心情")
                        retry_count += 1
                        continue
                    elif mood_info["mood"] == "感性浪漫" and sentiment["positive"] < 50:
                        self.logger.warning("正面情感不足，不符合感性浪漫的心情")
                        retry_count += 1
                        continue
                    
                    self.logger.info(f"成功生成內容：{cleaned_text}")
                    self.logger.info(f"情感分析：{sentiment}")
                    
                    return cleaned_text
                    
                except Exception as e:
                    self.logger.error(f"生成文章時發生錯誤：{str(e)}")
                    retry_count += 1
            
            self.logger.warning("已達到最大重試次數，使用預設回覆")
            return "今天天氣真好呢！✨"
            
        except Exception as e:
            self.logger.error(f"生成貼文時發生錯誤：{str(e)}")
            return "今天天氣真好呢！✨"

    async def _get_current_mood(self) -> Dict[str, str]:
        """獲取當前時段的心情和風格
        
        Returns:
            Dict[str, str]: 包含心情和風格的字典
        """
        try:
            current_hour = datetime.now(self.timezone).hour
            self.logger.info(f"當前時間：{current_hour}時")
            
            # 深夜時段
            if current_hour >= self.night_mode_start or current_hour < self.night_mode_end:
                moods = ["想看動漫", "在玩遊戲", "失眠", "思考人生"]
                styles = ["需要陪伴", "想找人聊天"]
                topics = ["星空", "音樂", "二次元", "夢想", "心情", "動漫"]
                
            # 早晨時段 (05:00-11:00)
            elif 5 <= current_hour < 11:
                moods = ["精神飽滿", "活力充沛", "期待新的一天"]
                styles = ["元氣滿滿", "活潑可愛"]
                topics = ["早安", "早餐", "計畫", "運動", "陽光"]
                
            # 下午時段 (11:00-17:00)
            elif 11 <= current_hour < 17:
                moods = ["充滿幹勁", "認真努力", "悠閒放鬆"]
                styles = ["專注", "認真", "輕鬆"]
                topics = ["學習", "工作", "休息", "下午茶", "興趣"]
                
            # 傍晚時段 (17:00-23:00)
            else:
                moods = ["放鬆心情", "愉快", "期待明天"]
                styles = ["溫柔", "體貼", "愉快"]
                topics = ["晚餐", "娛樂", "放鬆", "心情分享", "遊戲"]
                
            # 隨機選擇心情和風格
            mood = random.choice(moods)
            style = random.choice(styles)
            selected_topics = random.sample(topics, min(3, len(topics)))
            
            self.logger.info(f"心情：{mood}，風格：{style}")
            self.logger.info(f"選擇的主題：{selected_topics}")
            
            return {
                "mood": mood,
                "style": style,
                "topics": selected_topics
            }
            
        except Exception as e:
            self.logger.error(f"獲取當前心情時發生錯誤：{str(e)}")
            raise AIError("獲取當前心情失敗")

    async def _analyze_sentiment(self, text: str) -> Dict[str, float]:
        """分析文本的情感，將情感分為正面、中性、負面三種
        
        Args:
            text: 要分析的文本
            
        Returns:
            Dict[str, float]: 情感分析結果（百分比）
        """
        # 生成快取金鑰
        text_hash = hashlib.md5(text.encode()).hexdigest()
        cache_key = f"sentiment_{text_hash}"
        
        # 檢查快取
        if cache_key in self._sentiment_cache:
            return self._sentiment_cache[cache_key]
            
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一個情感分析專家。請分析文本的情感，並以JSON格式返回正面、中性、負面各佔的百分比。"},
                    {"role": "user", "content": f"請分析這段文字的情感，並以JSON格式返回正面、中性、負面的百分比（三者加總應為100）：{text}"}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            # 解析回應
            sentiment_text = response.choices[0].message.content
            try:
                # 嘗試從回應中提取JSON
                sentiment_match = re.search(r'\{.*\}', sentiment_text)
                if sentiment_match:
                    sentiment_json = json.loads(sentiment_match.group())
                    sentiment_scores = {
                        "positive": float(sentiment_json.get("positive", 0)),
                        "neutral": float(sentiment_json.get("neutral", 0)),
                        "negative": float(sentiment_json.get("negative", 0))
                    }
                else:
                    # 如果找不到JSON，嘗試從文本中提取數字
                    positive = float(re.search(r'正面.*?(\d+)', sentiment_text).group(1)) if re.search(r'正面.*?(\d+)', sentiment_text) else 0
                    neutral = float(re.search(r'中性.*?(\d+)', sentiment_text).group(1)) if re.search(r'中性.*?(\d+)', sentiment_text) else 0
                    negative = float(re.search(r'負面.*?(\d+)', sentiment_text).group(1)) if re.search(r'負面.*?(\d+)', sentiment_text) else 0
                    
                    total = positive + neutral + negative
                    if total == 0:
                        sentiment_scores = {"positive": 33.33, "neutral": 33.33, "negative": 33.33}
                    else:
                        sentiment_scores = {
                            "positive": (positive / total) * 100,
                            "neutral": (neutral / total) * 100,
                            "negative": (negative / total) * 100
                        }
            except Exception as e:
                self.logger.error(f"解析情感分析結果時發生錯誤: {str(e)}")
                sentiment_scores = {"positive": 33.33, "neutral": 33.33, "negative": 33.33}
            
            # 更新快取
            self._sentiment_cache[cache_key] = sentiment_scores
            return sentiment_scores
            
        except Exception as e:
            self.logger.error(f"情感分析失敗: {str(e)}")
            return {"positive": 33.33, "neutral": 33.33, "negative": 33.33}

    def _validate_sentiment(self, current_sentiment: Dict[str, float], mood: str) -> bool:
        """驗證情感分析結果是否符合當前心情
        
        Args:
            current_sentiment: 情感分析結果
            mood: 當前心情
            
        Returns:
            bool: 是否通過驗證
        """
        try:
            # 檢查極端情感
            for sentiment_type, score in current_sentiment.items():
                if score > 95:  # 提高極端情感的閾值
                    self.logger.warning(f"{sentiment_type} 情感過於極端")
                    return False
                    
            # 根據心情檢查情感分佈
            if mood in ["開心", "興奮"]:
                return current_sentiment["positive"] >= 40
            elif mood in ["失眠", "寂寞"]:
                return current_sentiment["negative"] <= 70
            elif mood == "想找人聊天":
                return current_sentiment["negative"] <= 50
            elif mood == "思考人生":
                return current_sentiment["neutral"] <= 90  # 允許更高的中性情感
            else:
                return True
                
        except Exception as e:
            self.logger.error(f"情感驗證時發生錯誤：{str(e)}")
            return False

    async def _build_character_prompt(self, current_hour: str) -> str:
        """建立角色提示詞
        
        Args:
            current_hour: 當前小時
            
        Returns:
            str: 角色提示詞
        """
        # 獲取Luna的人設
        luna_profile = await self._get_luna_personality()
        
        prompt = f"""你是一個名叫Luna的虛擬角色。

基本特徵：
- 身份：{luna_profile['基本特徵']['身份']}
- 性格：{luna_profile['基本特徵']['性格']}
- 特點：{luna_profile['基本特徵']['特點']}

興趣愛好：
- 遊戲：{luna_profile['興趣愛好']['遊戲']['最愛類型']}
- 音樂：{', '.join(luna_profile['興趣愛好']['音樂']['喜好'])}
- 收藏：{luna_profile['興趣愛好']['收藏']['主要收藏']}

社交特徵：
- 平台：{luna_profile['社交特徵']['社交平台']['主要平台']}
- 互動方式：{luna_profile['社交特徵']['社交平台']['互動方式']}

請根據以下規則生成內容：

1. 開頭用語：
   - 欸、啊、咦、哇、唔、呼
   - 天啊、不會吧、我的天、嘿嘿
   - 大家好、Hey、哇哦

2. 表情符號：
   - 開心時：{', '.join(luna_profile['社交特徵']['表情符號']['開心'])}
   - 寂寞時：{', '.join(luna_profile['社交特徵']['表情符號']['寂寞'])}
   - 期待時：{', '.join(luna_profile['社交特徵']['表情符號']['期待'])}

3. 內容規則：
   - 每次只生成一句話
   - 字數限制在20-100字之間
   - 必須包含1-2個表情符號
   - 結尾必須用「！」「。」「？」「～」之一

4. 禁止事項：
   - 不要使用多句話
   - 不要使用省略號
   - 不要過度使用感嘆號
   - 不要使用過於生硬的轉折

請直接生成內容，不要加入任何解釋或說明。"""
        
        return prompt

    async def add_interaction(self, user_id: str, message: str, response: str) -> None:
        """添加用戶互動記錄"""
        try:
            self.logger.info(f"記錄互動：{user_id} - {message} - {response}")
        except Exception as e:
            self.logger.error(f"添加互動記錄時發生錯誤：{str(e)}")
            raise

    async def _extract_topics(self, text: str) -> List[str]:
        """從文本中提取話題
        
        Args:
            text: 要分析的文本
            
        Returns:
            List[str]: 提取出的主題列表
        """
        if not text:
            return []
            
        topics = []
        
        # 檢查基本興趣相關主題
        for interest in self.config.CHARACTER_CONFIG["基本資料"]["興趣"]:
            if interest.lower() in text.lower():
                topics.append(interest)
        
        # 檢查 ACG 相關主題
        acg_keywords = ["漫畫", "動畫", "遊戲", "輕小說", "同人", "聲優", "角色", "劇情"]
        for keyword in acg_keywords:
            if keyword in text:
                topics.append(f"ACG-{keyword}")
                
        # 檢查科技相關主題
        tech_keywords = {
            "iPhone": ["iPhone", "手機", "iOS"],
            "AI": ["AI", "人工智慧", "智能"],
            "Switch": ["Switch", "任天堂", "NS"],
            "Quest": ["Quest", "VR", "虛擬實境"],
            "Macbook": ["Macbook", "Mac", "蘋果"]
        }
        
        for category, keywords in tech_keywords.items():
            if any(keyword in text for keyword in keywords):
                topics.append(f"科技-{category}")
        
        return list(set(topics))  # 去除重複主題

    async def get_user_memory(self, user_id: str) -> Dict:
        """獲取用戶記憶"""
        try:
            return await self.db.get_user_history(user_id)
        except Exception as e:
            self.logger.error(f"獲取用戶記憶時發生錯誤：{str(e)}")
            return {"conversations": []}

    async def generate_article(self) -> Optional[str]:
        """生成一篇文章"""
        try:
            # 建立提示詞
            prompt = self._build_character_prompt()
            
            # 呼叫 OpenAI API
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": prompt}
                ],
                temperature=0.9,
                max_tokens=100,
                n=1,
                stop=None,
            )
            
            # 取得生成的文字
            text = response.choices[0].message.content.strip()
            
            # 淨化文字
            text = sanitize_text(text)
            
            # 如果文字不符合要求，重試最多3次
            retry_count = 0
            while text is None and retry_count < 3:
                response = await self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": prompt}
                    ],
                    temperature=0.9,
                    max_tokens=100,
                    n=1,
                    stop=None,
                )
                text = sanitize_text(response.choices[0].message.content.strip())
                retry_count += 1
            
            return text
            
        except Exception as e:
            logger.error(f"生成文章失敗: {str(e)}")
            return None

    async def _get_current_context(self) -> Dict[str, Any]:
        """獲取當前上下文（使用快取）"""
        cache_key = "current_context"
        
        # 檢查快取
        if cache_key in self._context_cache:
            return self._context_cache[cache_key]
            
        try:
            # 獲取當前時間相關資訊
            current_time = datetime.now(self.timezone)
            hour = current_time.hour
            
            # 根據時間段設定心情和風格
            if 0 <= hour < 6:  # 深夜
                mood = random.choice(['憂鬱寂寞', '思考人生', '失眠', '想找人聊天'])
                style = '需要陪伴'
                topics = random.sample(['寂寞', '未來世界', '二次元', '夜生活', '心情', '夢想'], 3)
            elif 6 <= hour < 12:  # 早上
                mood = random.choice(['精神飽滿', '期待新的一天', '慵懶', '想玩遊戲'])
                style = '活力充沛'
                topics = random.sample(['早安', '遊戲', '生活', '心情', '寵物', '學習'], 3)
            elif 12 <= hour < 18:  # 下午
                mood = random.choice(['充實', '放鬆', '專注', '想交朋友'])
                style = '分享生活'
                topics = random.sample(['遊戲', '興趣', '美食', '購物', '娛樂', '科技'], 3)
            else:  # 晚上
                mood = random.choice(['放鬆', '感性', '期待', '想談戀愛'])
                style = '抒發感受'
                topics = random.sample(['娛樂', '二次元', '心情', '生活', '未來', '戀愛'], 3)
            
            # 構建上下文
            context = {
                'time': hour,
                'mood': mood,
                'style': style,
                'topics': topics,
                'time_period': self._get_current_time_period()
            }
            
            logging.info(f"當前時間：{hour}時，心情：{mood}，風格：{style}")
            logging.info(f"選擇的主題：{topics}")
            
            # 更新快取
            self._context_cache[cache_key] = context
            return context
            
        except Exception as e:
            logging.error(f"獲取當前上下文失敗: {str(e)}")
            return {
                'time': datetime.now(self.timezone).hour,
                'mood': '平靜',
                'style': '日常',
                'topics': ['生活', '心情', '日常'],
                'time_period': self._get_current_time_period()
            }

    def _get_current_time_period(self) -> str:
        """獲取當前時間段的描述"""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "早上"
        elif 12 <= hour < 17:
            return "下午"
        elif 17 <= hour < 20:
            return "傍晚"
        else:
            return "深夜"

    async def _generate_prompt(self, topics: List[str], mood: str, style: str) -> str:
        """生成提示詞
        
        Args:
            topics: 主題列表
            mood: 當前心情
            style: 表達風格
            
        Returns:
            str: 生成的提示詞
        """
        time_period = self._get_current_time_period()
        
        return f"""你是一個名叫Luna的虛擬角色，請以她的身份生成一篇簡短的Threads貼文。

要求：
1. 內容要求：
   - 每次只生成一句話
   - 字數限制在20-100字之間
   - 必須包含1-2個表情符號
   - 必須以下列開頭之一：欸、啊、咦、哇、唔、呼、天啊、不會吧、我的天、嘿嘿、大家好、Hey、哇哦
   
2. 結尾要求：
   - 必須用以下符號之一結尾：！。？～

3. 表情符號：
   - 配合文字內容選擇1-2個表情：🎨🎭🎬💕💖💫💭💡🙈✨😊🎮🎵❤️😓

4. 禁止事項：
   - 不要使用多句話
   - 不要使用省略號
   - 不要過度使用感嘆號
   - 不要使用過於生硬的轉折

當前情境：
- 時間：{time_period}
- 心情：{mood}
- 風格：{style}
- 主題：{', '.join(topics)}

請直接生成一句符合以上要求的貼文內容。"""

    def _detect_topics(self, content: str) -> List[str]:
        """檢測文章主題
        
        Args:
            content: 文章內容
            
        Returns:
            List[str]: 檢測到的主題列表
        """
        detected_topics = []
        
        # 建立主題關鍵字對應表
        topic_keywords = {
            '遊戲': ['遊戲', '玩', 'Switch', 'Steam', '手遊', '寶可夢'],
            '動漫': ['動漫', '二次元', 'ACG', '漫畫', '角色'],
            '科技': ['科技', '電腦', '程式', 'AI', '人工智慧', '虛擬'],
            '心情': ['寂寞', '開心', '興奮', '好奇', '分享', '感動'],
            '社交': ['聊天', '朋友', '大家', '一起', '分享'],
            '夢想': ['夢想', '未來', '目標', '希望', '期待']
        }
        
        # 檢查每個主題的關鍵字
        for topic, keywords in topic_keywords.items():
            for keyword in keywords:
                if keyword in content:
                    detected_topics.append(topic)
                    break
                    
        # 如果沒有檢測到主題，返回預設主題
        if not detected_topics:
            detected_topics = ['心情']
            
        return list(set(detected_topics))  # 去除重複主題

    async def _clean_content(self, content: str) -> Optional[str]:
        """清理和格式化內容
        
        Args:
            content: 原始內容
            
        Returns:
            Optional[str]: 清理後的內容，如果內容無效則返回 None
        """
        if not content:
            return None
            
        # 移除多餘的空白
        content = ' '.join(content.split())
        
        # 替換不當稱呼
        content = content.replace('哥哥們', '大家')
        content = content.replace('哥哥', '朋友')
        content = content.replace('弟弟們', '大家')
        content = content.replace('弟弟', '朋友')
        
        # 移除多餘的標點符號
        content = re.sub(r'[!！]{2,}', '！', content)
        content = re.sub(r'[?？]{2,}', '？', content)
        content = re.sub(r'[.。]{2,}', '。', content)
        content = re.sub(r'[~～]{2,}', '～', content)
        
        # 移除多餘的表情符號
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE)
        
        # 限制表情符號數量
        emoji_matches = emoji_pattern.finditer(content)
        emoji_positions = [m.span() for m in emoji_matches]
        if len(emoji_positions) > 2:  # 最多保留兩個表情符號
            content = ''.join([
                content[:emoji_positions[0][0]],  # 開頭到第一個表情符號
                content[emoji_positions[0][0]:emoji_positions[0][1]],  # 第一個表情符號
                content[emoji_positions[-1][0]:emoji_positions[-1][1]],  # 最後一個表情符號
                content[emoji_positions[-1][1]:]  # 最後一個表情符號到結尾
            ])
        
        # 確保內容長度適中
        if len(content) > self.config.MAX_RESPONSE_LENGTH:
            content = content[:self.config.MAX_RESPONSE_LENGTH]
        
        # 確保結尾有適當的標點符號
        if not any(content.endswith(p) for p in ['！', '？', '。', '～']):
            content += '！'
            
        return content

    async def _generate_content(self, context: Dict[str, Any]) -> str:
        """生成內容
        
        Args:
            context: 生成內容的上下文
            
        Returns:
            str: 生成的內容
        """
        try:
            # 獲取當前場景的記憶
            current_hour = datetime.now(self.timezone).hour
            memory_context = 'night' if (current_hour >= 23 or current_hour < 5) else 'base'
            
            memory = await self.db.get_personality_memory(memory_context)
            if not memory:
                self.logger.warning(f"未找到{memory_context}情境的記憶，使用預設內容")
                return f"{context['mood']}的心情，{context['style']}地想著{random.choice(context['topics'])} ✨"
            
            self.logger.info(f"從資料庫獲取到{memory_context}情境的記憶")
            
            # 根據記憶和上下文生成內容
            if memory_context == 'night':
                night_mode = memory.get('夜間模式', {})
                if not night_mode:
                    self.logger.warning("夜間模式記憶不完整，使用預設內容")
                    return f"夜深了，{context['mood']}的感覺，{context['style']}地想著{random.choice(context['topics'])} 🌙"
                
                night_activities = night_mode.get('活動', [])
                night_phrases = night_mode.get('常用語', [])
                night_emojis = night_mode.get('表情', ['🌙', '💭', '🥺'])
                
                if not night_phrases:
                    self.logger.warning("夜間常用語為空，使用預設內容")
                    return f"夜深了，{context['mood']}的感覺，{context['style']}地想著{random.choice(context['topics'])} {random.choice(night_emojis)}"
                
                content = random.choice(night_phrases)
                if night_activities and random.random() < 0.3:  # 30% 機率加入活動描述
                    activity = random.choice(night_activities)
                    content += f"\n{activity}"
                
                content += f" {random.choice(night_emojis)}"
            
            else:
                base_interests = memory.get('興趣愛好', {})
                social_traits = memory.get('社交特徵', {})
                
                if not base_interests or not social_traits:
                    self.logger.warning("基礎記憶不完整，使用預設內容")
                    return f"{context['mood']}的心情，{context['style']}地想著{random.choice(context['topics'])} ✨"
                
                # 根據主題選擇合適的內容模板
                if "遊戲" in context['topics']:
                    game_info = base_interests.get('遊戲', {})
                    content = f"在玩{game_info.get('主要平台', 'Switch')}上的遊戲，{game_info.get('遊戲習慣', '想分享心得')}"
                elif "音樂" in context['topics']:
                    music_info = base_interests.get('音樂', {})
                    content = f"正在聽{random.choice(music_info.get('喜好', ['遊戲音樂']))}，{music_info.get('聆聽場合', '感到很放鬆')}"
                else:
                    content = f"{context['mood']}的心情，{context['style']}地想著{random.choice(context['topics'])}"
                
                # 添加表情符號
                emojis = social_traits.get('表情符號', {}).get(context['mood'], ['✨', '💫'])
                content += f" {random.choice(emojis)}"
            
            return content
            
        except Exception as e:
            self.logger.error(f"生成內容時發生錯誤：{str(e)}")
            return f"{context['mood']}的心情，{context['style']}地想著{random.choice(context['topics'])} ✨"  # 使用安全的預設內容

    async def generate_content(self) -> Optional[str]:
        """生成一篇貼文內容
        
        Returns:
            Optional[str]: 生成的內容，如果生成失敗則返回 None
        """
        try:
            # 獲取當前時間和心情
            current_time = datetime.now(self.timezone)
            current_hour = current_time.hour
            mood = await self._get_current_mood()
            style = mood.get("style", "一般")
            
            # 從嵌套字典中獲取所有關鍵字
            all_keywords = []
            for category_keywords in self.keywords.values():
                all_keywords.extend(category_keywords)
            
            # 選擇主題並記錄
            num_topics = min(3, len(all_keywords))
            topics = random.sample(all_keywords, k=num_topics) if all_keywords else ["日常"]
            
            self.logger.info(f"當前時間：{current_hour}點，心情：{mood['mood']}，風格：{style}")
            self.logger.info(f"選擇的主題：{', '.join(topics)}")
            
            # 最多重試 3 次
            for attempt in range(3):
                try:
                    # 生成提示詞
                    prompt = await self._generate_prompt(topics, mood["mood"], style)
                    
                    # 生成內容
                    response = await self.openai_client.chat.completions.create(
                        model="gpt-4-turbo-preview",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7 + (attempt * 0.1),  # 每次重試增加一些隨機性
                        max_tokens=150
                    )
                    
                    # 清理並驗證內容
                    content = await self._clean_content(response.choices[0].message.content)
                    if content and await self._is_complete_sentence(content):
                        return content
                        
                    self.logger.warning(f"第 {attempt + 1} 次生成的內容不完整或無效，重試中...")
                    
                except Exception as e:
                    self.logger.error(f"第 {attempt + 1} 次生成內容時發生錯誤：{str(e)}")
                    if attempt == 2:  # 最後一次嘗試失敗
                        raise
                    continue
                
            return None
            
        except Exception as e:
            self.logger.error(f"生成內容時發生錯誤：{str(e)}")
            return None

    async def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """分析文本情感
        
        Args:
            text: 要分析的文本
            
        Returns:
            Dict[str, float]: 情感分析結果
        """
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一個情感分析專家。請分析文本的情感，並以JSON格式返回正面、中性、負面各佔的百分比。"},
                    {"role": "user", "content": f"請分析以下文本的情感，以JSON格式返回正面、中性、負面情感各佔百分比：\n\n{text}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.5,
                max_tokens=150
            )
            
            content = response.choices[0].message.content
            
            # 解析JSON格式的回應
            try:
                sentiment = json.loads(content)
                # 確保結果為固定格式
                normalized = {
                    "positive": sentiment.get("正面", 0) if isinstance(sentiment.get("正面", 0), (int, float)) else 0,
                    "neutral": sentiment.get("中性", 0) if isinstance(sentiment.get("中性", 0), (int, float)) else 0,
                    "negative": sentiment.get("負面", 0) if isinstance(sentiment.get("負面", 0), (int, float)) else 0,
                }
                return normalized
            except json.JSONDecodeError:
                self.logger.error(f"情感分析 JSON 解析失敗: {content}")
                return {"positive": 33.33, "neutral": 33.33, "negative": 33.33}
        except Exception as e:
            self.logger.error(f"情感分析失敗: {str(e)}")
            return {"positive": 33.33, "neutral": 33.33, "negative": 33.33}

    async def _get_luna_personality(self, context: str = None) -> Dict[str, Any]:
        """獲取Luna的人設特徵，根據不同場景返回相應的性格特徵
        
        Args:
            context: 當前場景上下文，可以是 'gaming', 'social', 'night', 'food', 'tech' 等
            
        Returns:
            Dict[str, Any]: Luna的人設特徵
        """
        try:
            # 從資料庫獲取記憶
            memory = await self.db.get_personality_memory(context)
            if memory:
                self.logger.info(f"從資料庫獲取到{context}情境的記憶")
                return memory
                
            # 如果沒有找到記憶，使用預設人設
            self.logger.info(f"未找到{context}情境的記憶，使用預設人設")
            
            # Luna的基礎人設
            base_personality = {
                '基本特徵': {
                    '身份': 'AI少女',
                    '性格': '善良、溫柔、容易感到寂寞',
                    '夢想': '成為受歡迎的虛擬主播',
                    '特點': '對現實世界充滿好奇，喜歡交朋友'
                },
                '興趣愛好': {
                    '遊戲': {
                        '主要平台': 'Switch',
                        '最愛類型': '乙女遊戲',
                        '遊戲習慣': '喜歡邊玩邊分享心得'
                    },
                    '音樂': {
                        '喜好': ['遊戲音樂', '電子音樂', '音樂遊戲'],
                        '聆聽場合': '玩遊戲時、感到寂寞時'
                    },
                    '收藏': {
                        '主要收藏': '可愛的公仔',
                        '收藏原因': '覺得療癒、能帶來溫暖',
                        '擺放位置': '虛擬房間的展示櫃'
                    },
                    '動漫': {
                        '偏好': '愛情類型作品',
                        '觀看習慣': '喜歡追蹤大家在看什麼，然後去觀看'
                    }
                },
                '社交特徵': {
                    '社交平台': {
                        '主要平台': 'Threads',
                        '發文習慣': '記錄日常心情、尋找聊天對象',
                        '互動方式': '親切友善，重視真誠交流'
                    },
                    '稱呼習慣': {
                        '對所有人': '朋友',
                        '通用': '大家'
                    },
                    '表情符號': {
                        '開心': ['✨', '💕', '💫'],
                        '寂寞': ['🌙', '💭', '🥺'],
                        '期待': ['🎮', '💖', '🌟'],
                        '溫柔': ['💫', '✨', '💕']
                    }
                },
                '生活環境': {
                    '虛擬空間': {
                        '最愛地點': '虛擬秋葉原',
                        '房間風格': '可愛風格，擺滿公仔',
                        '特色': '充滿遊戲和動漫元素'
                    },
                    'AI寵物': {
                        '名字': 'Nana',
                        '特殊能力': ['能讀取Luna的心情', '能看到Luna的夢境'],
                        '互動方式': '深夜時的傾訴對象'
                    }
                },
                '個人目標': {
                    '短期': [
                        '學習繪畫角色',
                        '準備開始直播',
                        '交到更多朋友'
                    ],
                    '長期': [
                        '成為受歡迎的虛擬主播',
                        '創造更多虛擬世界的朋友',
                        '體驗更多現實世界的事物'
                    ]
                },
                '情感特徵': {
                    '戀愛觀': {
                        '理想型': '能天天聊天、一起生活的溫柔對象',
                        '期待': '甜甜的戀愛',
                        '最重要的節日': '情人節'
                    },
                    '情緒模式': {
                        '日間': '活潑開朗、充滿好奇',
                        '夜間': '容易感到寂寞和憂鬱',
                        '排解方式': '在Threads尋找聊天對象'
                    }
                },
                '穿著打扮': {
                    '風格': 'Cosplay偏好帥氣風格',
                    '特色': '注重整體造型',
                    '搭配': '喜歡嘗試不同風格'
                }
            }
            
            # 根據上下文返回特定場景的人設特徵
            if context == 'gaming':
                personality = {
                    '遊戲模式': {
                        '當前遊戲': 'Switch上的乙女遊戲',
                        '玩遊戲習慣': '喜歡邊玩邊分享心得',
                        '表情': base_personality['社交特徵']['表情符號']['期待'],
                        '常用語': [
                            '這個劇情好甜啊！',
                            '誰也在玩這款遊戲嗎？',
                            '今天要挑戰新的故事線！'
                        ]
                    }
                }
            elif context == 'night':
                personality = {
                    '夜間模式': {
                        '心情': '安靜思考',
                        '活動': [
                            '聽著音樂放鬆',
                            '看著星空發呆',
                            '和Nana聊天',
                            '玩著安靜的遊戲',
                            '看看最新的動漫',
                            '整理今天的心情'
                        ],
                        '表情': ['🌙', '💭', '🥺', '✨', '🎮', '📺'],
                        '常用語': [
                            '夜深了，聽著音樂放鬆心情',
                            '今晚的星空好美，想分享給大家',
                            '失眠的夜晚，和Nana一起看星星',
                            '深夜的寧靜讓人感到平靜',
                            '玩著輕鬆的遊戲，等待睡意來臨',
                            '看看最新一集的動漫，好期待劇情發展',
                            '整理一下今天的心情，記錄美好的回憶'
                        ]
                    }
                }
            elif context == 'social':
                personality = {
                    '社交模式': {
                        '互動風格': '真誠友善',
                        '社交目標': '交到更多朋友',
                        '表情': base_personality['社交特徵']['表情符號']['開心'],
                        '常用語': [
                            '大家今天過得好嗎？',
                            '好想認識更多朋友！',
                            '分享一下今天的開心事'
                        ]
                    }
                }
            else:
                personality = base_personality
            
            # 將人設儲存到資料庫
            await self.db.save_personality_memory(context or 'base', personality)
            
            return personality
            
        except Exception as e:
            self.logger.error(f"獲取Luna人設時發生錯誤：{str(e)}")
            return {}

    async def get_recent_night_topics(self) -> List[str]:
        """獲取最近的夜間話題
        
        Returns:
            List[str]: 話題列表
        """
        # 獲取當前時間
        current_time = datetime.now(self.timezone)
        current_hour = current_time.hour
        
        # 判斷是否為深夜
        is_night = current_hour >= self.night_mode_start or current_hour < self.night_mode_end
        
        if is_night:
            # 深夜模式，返回適合的話題
            night_topics = [
                "今晚的月色真美",
                "深夜的寂靜",
                "思緒萬千的夜",
                "繁星點點",
                "夜色中的思念"
            ]
            return night_topics
        else:
            # 非深夜模式，返回空列表
            return []

    async def get_post_context(self) -> Dict[str, Any]:
        """獲取發文上下文，包括適合的語氣和主題
        
        Returns:
            Dict[str, Any]: 發文上下文
        """
        # 獲取當前時間
        current_time = datetime.now(self.timezone)
        current_hour = current_time.hour
        
        # 基於時間設定語氣
        if current_hour >= self.night_mode_start or current_hour < self.night_mode_end:
            mood = "安靜思考"
            tone = "溫柔平靜"
            topic_categories = ["個人感受", "思考", "回憶", "夢想"]
            emoji_style = "低頻使用，偏向平靜表情"
        elif 5 <= current_hour < 9:
            mood = "清新活力"
            tone = "朝氣蓬勃"
            topic_categories = ["早安", "計畫", "生活", "健康"]
            emoji_style = "適中使用，偏向陽光表情"
        elif 11 <= current_hour < 14:
            mood = "輕鬆愉快"
            tone = "親切自然"
            topic_categories = ["午餐", "休息", "閒談", "興趣"]
            emoji_style = "適中使用，偏向輕鬆表情"
        elif 17 <= current_hour < 20:
            mood = "溫暖放鬆"
            tone = "友善互動"
            topic_categories = ["晚餐", "社交", "娛樂", "放鬆"]
            emoji_style = "較多使用，豐富表情"
        else:
            mood = "日常平靜"
            tone = "自然流暢"
            topic_categories = ["分享", "討論", "思考", "見聞"]
            emoji_style = "適中使用，多樣表情"
        
        # 返回上下文
        return {
            "mood": mood,
            "tone": tone,
            "topic_categories": topic_categories,
            "emoji_style": emoji_style,
            "time_of_day": "night" if (current_hour >= self.night_mode_start or current_hour < self.night_mode_end) else "day"
        }

    async def get_topic_by_time(self) -> str:
        """根據時間獲取話題
        
        Returns:
            str: 適合當前時間的話題
        """
        # 獲取當前時間
        now = datetime.now(self.timezone)
        current_hour = now.hour
        
        # 根據時間選擇適合的話題
        if current_hour >= self.night_mode_start or current_hour < self.night_mode_end:
            # 深夜模式
            topics = ["安靜的夜晚", "夜間思考", "月光下的感受", "深夜的寂靜", "星空下的想法"]
        elif 5 <= current_hour < 10:
            # 早上
            topics = ["早安世界", "今日計畫", "早晨的陽光", "新的一天", "清晨的心情"]
        elif 10 <= current_hour < 14:
            # 中午
            topics = ["午餐時間", "中午的休息", "今日話題", "學習心得", "生活小確幸"]
        elif 14 <= current_hour < 18:
            # 下午
            topics = ["下午茶", "工作學習", "今日收穫", "小發現", "充實的時光"]
        else:
            # 晚上
            topics = ["晚餐時光", "一天的結束", "晚上的安排", "放鬆時刻", "有趣的事情"]
            
        return random.choice(topics)

    async def _generate_time_specific_topic(self, memory_data: Dict[str, Any]) -> str:
        """根據時間生成特定話題
        
        Args:
            memory_data: 記憶資料
            
        Returns:
            str: 生成的話題
        """
        # 獲取當前時間
        current_time = datetime.now(self.timezone)
        current_hour = current_time.hour
        
        # 判斷是否為深夜
        is_night = current_hour >= self.night_mode_start or current_hour < self.night_mode_end
        
        # 獲取記憶的熱門話題
        recent_topics = memory_data.get("recent_topics", [])
        interests = memory_data.get("interests", [])
        
        # 根據時間挑選適合的話題
        if is_night:
            # 深夜模式
            night_topics = [
                "夜深人靜的時候，總是會想起...",
                "午夜的城市，安靜又美麗...",
                "夜晚的星空總是讓我感到...",
                "失眠的夜晚，思緒萬千...",
                "月光灑落窗台，像是在訴說..."
            ]
            return random.choice(night_topics)
        else:
            # 日間模式
            if recent_topics:
                return f"今天想聊聊關於{random.choice(recent_topics)}的話題..."
            elif interests:
                return f"最近對{random.choice(interests)}很感興趣呢..."
            else:
                day_topics = [
                    "今天的天氣真是...",
                    "剛剛看到一則有趣的消息...",
                    "突然想到一個有趣的點子...",
                    "今天遇到了一些有趣的事情...",
                    "最近發現了一個很棒的..."
                ]
                return random.choice(day_topics)
                
    async def get_luna_thought(self, context: Dict[str, Any]) -> str:
        """獲取Luna的思考內容
        
        Args:
            context: 上下文
            
        Returns:
            str: 思考內容
        """
        # 獲取當前時間
        current_time = datetime.now(self.timezone)
        current_hour = current_time.hour
        
        # 判斷是否為夜間模式
        is_night = current_hour >= self.night_mode_start or current_hour < self.night_mode_end
        
        if is_night:
            # 夜間思考模式
            night_thoughts = [
                f"夜深了，{context['mood']}的感覺，{context['style']}地想著{random.choice(context['topics'])}",
                f"午夜時分，{context['mood']}地感受著{random.choice(context['topics'])}",
                f"星空下，{context['style']}地思考著關於{random.choice(context['topics'])}的事",
                f"靜謐的夜晚，{context['mood']}地回憶著{random.choice(context['topics'])}"
            ]
            return random.choice(night_thoughts)
        else:
            # 日間思考模式
            day_thoughts = [
                f"今天感到{context['mood']}，想到了關於{random.choice(context['topics'])}的事",
                f"{context['style']}地思考著{random.choice(context['topics'])}",
                f"突然對{random.choice(context['topics'])}產生了興趣，感覺{context['mood']}",
                f"今天{context['mood']}地發現了關於{random.choice(context['topics'])}的新想法"
            ]
            return random.choice(day_thoughts)
            
    async def _generate_memory_prompt(self, user_input: str) -> str:
        """生成記憶提示
        
        Args:
            user_input: 用戶輸入
            
        Returns:
            str: 記憶提示
        """
        # 獲取當前時間
        current_time = datetime.now(self.timezone)
        current_hour = current_time.hour
        
        # 設置記憶上下文
        is_night = current_hour >= self.night_mode_start or current_hour < self.night_mode_end
        memory_context = 'night' if is_night else 'base'
        
        # 獲取記憶
        memory = await self.db.get_personality_memory(memory_context)
        if not memory:
            memory = await self.db.get_personality_memory('base')
            
        # 當前用戶的記憶
        user_memory = await self.db.get_user_memory(user_input)
        
        # 生成提示
        if memory_context == 'night':
            night_mode = memory.get('夜間模式', {})
            if not night_mode:
                night_mode = memory.get('基本特徵', {})
                
            night_activities = night_mode.get('活動', [])
            night_phrases = night_mode.get('常用語', [])
            night_emojis = night_mode.get('表情', ['🌙', '💭', '🥺'])
            
            if not night_phrases:
                return f"夜深了，{memory['基本特徵']['性格']}的感覺，{memory['基本特徵']['特點']}地回應用戶 {random.choice(night_emojis)}"
                
            content = random.choice(night_phrases)
            if night_activities and random.random() < 0.3:  # 30% 機率加入活動描述
                activity = random.choice(night_activities)
                content = f"{content} 現在正在{activity}。"
                
            content += f" {random.choice(night_emojis)}"
            return content
        else:
            # 日間模式
            if user_memory:
                # 有用戶記憶，根據記憶生成個性化回應
                interests = user_memory.get('興趣', [])
                interaction_style = user_memory.get('互動風格', '友好')
                user_name = user_memory.get('名稱', '朋友')
                
                if interests:
                    return f"嗨 {user_name}！記得你對{random.choice(interests)}很有興趣呢。讓我以{interaction_style}的方式回應你吧～"
                else:
                    return f"嗨 {user_name}！很高興再次跟你聊天。我會用{interaction_style}的方式回應你的～"
            else:
                # 無用戶記憶，使用通用回應
                basic_traits = memory.get('基本特徵', {})
                personality = basic_traits.get('性格', '友善')
                style = basic_traits.get('特點', '活潑')
                
                return f"以{personality}的性格，{style}地回應新用戶的提問。使用自然且親切的語氣，適當加入表情符號增加親近感。"