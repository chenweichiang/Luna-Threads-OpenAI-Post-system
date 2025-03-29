"""
Version: 2024.03.30
Author: ThreadsPoster Team
Description: AI 處理器，負責管理 Luna 的人設、對話生成和情感分析
Last Modified: 2024.03.30
Changes: 
- 移除所有 BL 相關內容
- 新增人設記憶系統
- 優化對話生成邏輯
"""

import logging
from datetime import datetime
import pytz
from openai import AsyncOpenAI
from src.config import Config
from src.utils import sanitize_text
import random
from typing import Optional, List, Dict, Any, Tuple
import json
from collections import defaultdict
import asyncio
import time
import os
import re

# 設定 token 使用量的 logger
token_logger = logging.getLogger('token_usage')
token_logger.setLevel(logging.INFO)

# 確保 logs 目錄存在
if not os.path.exists('logs'):
    os.makedirs('logs')

# 設定 token 使用量的 file handler
token_handler = logging.FileHandler('logs/token_usage.log')
token_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
token_logger.addHandler(token_handler)

class AIError(Exception):
    """AI 相關錯誤"""
    pass

class AIHandler:
    """AI 處理器"""
    def __init__(self, config):
        """初始化 AI 處理器
        
        Args:
            config: 設定物件
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.timezone = pytz.timezone("Asia/Taipei")
        self.openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        self.keywords = config.KEYWORDS
        self.sentiment_dict = config.SENTIMENT_WORDS
        self.total_tokens = 0
        self.request_count = 0
        self.db = None  # 資料庫連接會在 initialize 中設定

    async def initialize(self, db):
        """初始化 AI 處理器的資料庫連接和人設記憶
        
        Args:
            db: Database 實例
        """
        try:
            self.db = db
            
            # 檢查基礎人設是否存在
            base_memory = await self.db.get_personality_memory('base')
            if not base_memory:
                self.logger.info("初始化基礎人設記憶")
                # 獲取並儲存基礎人設
                base_personality = await self._get_luna_personality()
                await self.db.save_personality_memory('base', base_personality)
            
            # 初始化各種場景的人設
            scenes = ['gaming', 'night', 'social']
            for scene in scenes:
                scene_memory = await self.db.get_personality_memory(scene)
                if not scene_memory:
                    self.logger.info(f"初始化 {scene} 場景的人設記憶")
                    # 獲取並儲存場景特定人設
                    scene_personality = await self._get_luna_personality(scene)
                    await self.db.save_personality_memory(scene, scene_personality)
            
            self.logger.info("人設記憶初始化完成")
            
        except Exception as e:
            self.logger.error(f"初始化人設記憶時發生錯誤：{str(e)}")
            raise

    async def close(self):
        """關閉 AI 處理器"""
        if hasattr(self, 'openai_client'):
            await self.openai_client.close()

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
            "好想", "好喜歡", "最近"
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
        if emoji_count < 1 or emoji_count > 2:
            self.logger.warning(f"表情符號數量不符合要求：{emoji_count}")
            return False
            
        # 檢查字數（不包含表情符號）
        text_length = len(text_without_emoji.strip())
        if not (20 <= text_length <= 100):
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
        end_time = time.time()
        duration = end_time - start_time
        
        # 計算 token 使用量
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        total_tokens = response.usage.total_tokens
        
        # 計算每秒 token 使用率
        tokens_per_second = total_tokens / duration if duration > 0 else 0
        
        # 更新總計
        self.total_tokens += total_tokens
        self.request_count += 1
        
        # 記錄詳細資訊
        token_logger.info(
            f"Token使用量 - "
            f"提示詞: {prompt_tokens}, "
            f"回覆: {completion_tokens}, "
            f"總計: {total_tokens}, "
            f"耗時: {duration:.2f}秒, "
            f"每秒token: {tokens_per_second:.2f}, "
            f"累計使用: {self.total_tokens}, "
            f"請求次數: {self.request_count}"
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
            mood_info = await self._get_current_mood(current_hour)
            
            if suggested_topics:
                mood_info["topics"].extend(suggested_topics)
                self.logger.info(f"整合建議主題: {suggested_topics}")
            
            prompt = await self._build_character_prompt(str(current_hour))
            topic_prompt = f"""請圍繞以下主題生成內容：{', '.join(mood_info['topics'])}"""
            
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    start_time = time.time()
                    response = await self.openai_client.chat.completions.create(
                        model=self.config.OPENAI_MODEL,
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

    async def _get_current_mood(self, hour: int) -> Dict[str, Any]:
        """根據時間獲取當前心情和主題
        
        Args:
            hour: 當前小時（24小時制）
            
        Returns:
            Dict[str, Any]: 包含心情、風格和主題的字典
        """
        # 基礎主題庫
        base_topics = {
            "科技": ["新科技", "AI", "程式設計", "遊戲開發", "手機", "電腦", "智慧家電"],
            "動漫": ["動畫", "漫畫", "輕小說", "Cosplay", "同人創作", "聲優"],
            "生活": ["美食", "旅遊", "時尚", "音樂", "電影", "寵物", "攝影"],
            "心情": ["工作", "學習", "戀愛", "友情", "家庭", "夢想", "目標"]
        }
        
        # 根據時間段設定心情和風格
        if 5 <= hour < 11:  # 早上
            mood = "精神飽滿"
            style = "活力充沛"
            primary_categories = ["科技", "生活"]
        elif 11 <= hour < 14:  # 中午
            mood = "悠閒放鬆"
            style = "輕鬆愉快"
            primary_categories = ["動漫", "生活"]
        elif 14 <= hour < 18:  # 下午
            mood = "專注認真"
            style = "理性思考"
            primary_categories = ["科技", "心情"]
        elif 18 <= hour < 22:  # 晚上
            mood = "感性浪漫"
            style = "溫柔細膩"
            primary_categories = ["動漫", "心情"]
        else:  # 深夜
            mood = "深度思考"
            style = "文藝感性"
            primary_categories = ["動漫", "心情"]
            
        # 選擇主題
        selected_topics = []
        
        # 從主要類別中選擇主題
        for category in primary_categories:
            topics = base_topics.get(category, [])
            if topics:
                selected_topics.extend(random.sample(topics, min(2, len(topics))))
        
        # 隨機添加一個其他類別的主題
        other_categories = [cat for cat in base_topics.keys() if cat not in primary_categories]
        if other_categories:
            random_category = random.choice(other_categories)
            topics = base_topics[random_category]
            if topics:
                selected_topics.extend(random.sample(topics, 1))
        
        # 確保主題不重複且數量適中
        selected_topics = list(set(selected_topics))
        if len(selected_topics) > 3:
            selected_topics = random.sample(selected_topics, 3)
        
        self.logger.info(f"當前時間：{hour}時，心情：{mood}，風格：{style}")
        self.logger.info(f"選擇的主題：{selected_topics}")
        
        return {
            "mood": mood,
            "style": style,
            "topics": selected_topics
        }

    async def _analyze_sentiment(self, text: str) -> Dict[str, float]:
        """分析文本的情感，將情感分為正面、中性、負面三種
        
        Args:
            text: 要分析的文本
            
        Returns:
            Dict[str, float]: 情感分析結果（百分比）
        """
        # 定義情感詞權重
        sentiment_weights = {
            'positive': {
                '極高': ['超愛', '太棒了', '完美', '震撼', '傑作', '神作', '驚艷', '感動到哭'],
                '很高': ['好棒', '優秀', '精彩', '讚嘆', '推薦', '喜歡', '期待', '驚喜'],
                '中高': ['不錯', '還好', '可以', '還行', '普通', '一般', '正常'],
                '偏高': ['有趣', '有意思', '值得一看', '還不錯'],
                '略高': ['還可以', '勉強', '將就', '湊合']
            },
            'neutral': {
                '極中': ['思考', '觀察', '分析', '研究', '探討', '評估'],
                '很中': ['看看', '試試', '考慮', '觀望', '等等'],
                '中等': ['或許', '可能', '也許', '大概', '應該'],
                '偏中': ['不確定', '不一定', '再說', '再看'],
                '略中': ['隨便', '都行', '無所謂', '沒差']
            },
            'negative': {
                '極低': ['糟糕', '失望', '討厭', '噁心', '垃圾', '廢物', '爛透'],
                '很低': ['不好', '不行', '差勁', '糟糕', '難看'],
                '中低': ['不太好', '不太行', '不太喜歡', '不太適合'],
                '偏低': ['有點差', '有點不好', '有點不行'],
                '略低': ['不太確定', '不太懂', '不太了解']
            }
        }
        
        # 定義表情符號權重
        emoji_weights = {
            'positive': ['💖', '✨', '💫', '🎉', '💝', '💕', '💗', '🌟', '😊', '🥰', '😍', '🤗', '💪', '👍'],
            'neutral': ['💭', '🤔', '🧐', '🔍', '👀', '👁️', '🗣️', '👥', '💬', '💡'],
            'negative': ['😱', '😨', '😰', '😢', '😭', '😤', '😒', '😕', '😟', '😔', '😣', '😓']
        }
        
        # 初始化分數
        scores = {'positive': 0, 'neutral': 0, 'negative': 0}
        
        # 分析文字情感
        for sentiment, levels in sentiment_weights.items():
            for level, words in levels.items():
                weight = {
                    '極高': 2.0, '很高': 1.5, '中高': 1.0, '偏高': 0.8, '略高': 0.5,
                    '極中': 2.0, '很中': 1.5, '中等': 1.0, '偏中': 0.8, '略中': 0.5,
                    '極低': 2.0, '很低': 1.5, '中低': 1.0, '偏低': 0.8, '略低': 0.5
                }[level]
                
                for word in words:
                    if word in text:
                        scores[sentiment] += weight
        
        # 分析表情符號情感
        for sentiment, emojis in emoji_weights.items():
            for emoji in emojis:
                if emoji in text:
                    scores[sentiment] += 0.5
        
        # 計算總分
        total = sum(scores.values())
        if total == 0:
            # 如果沒有檢測到任何情感，根據表情符號判斷
            emoji_count = {
                'positive': sum(1 for emoji in emoji_weights['positive'] if emoji in text),
                'neutral': sum(1 for emoji in emoji_weights['neutral'] if emoji in text),
                'negative': sum(1 for emoji in emoji_weights['negative'] if emoji in text)
            }
            emoji_total = sum(emoji_count.values())
            if emoji_total > 0:
                return {
                    'positive': round(emoji_count['positive'] / emoji_total * 100, 1),
                    'neutral': round(emoji_count['neutral'] / emoji_total * 100, 1),
                    'negative': round(emoji_count['negative'] / emoji_total * 100, 1)
                }
            return {'positive': 30.0, 'neutral': 40.0, 'negative': 30.0}
        
        # 計算百分比
        result = {
            sentiment: round(score / total * 100, 1)
            for sentiment, score in scores.items()
        }
        
        self.logger.info(f"情感分析結果：正面 {result['positive']}%, 中性 {result['neutral']}%, 負面 {result['negative']}%")
        return result

    def _validate_sentiment(self, sentiment_scores: Dict[str, Dict[str, float]], mood: str) -> bool:
        """驗證情感分析結果是否符合要求
        
        Args:
            sentiment_scores: 情感分析結果
            mood: 當前心情
            
        Returns:
            bool: 是否符合要求
        """
        try:
            # 獲取當前情感分數
            current_sentiment = sentiment_scores.get("current", {})
            if not current_sentiment:
                self.logger.warning("無法獲取情感分數")
                return False
                
            # 檢查情感分數是否合理
            total = sum(current_sentiment.values())
            if total == 0:
                self.logger.warning("情感分數總和為0")
                return False
                
            # 根據心情檢查情感是否合適
            if "失眠" in mood or "寂寞" in mood:
                # 深夜寂寞的情感可以偏向負面，但不能太過負面
                if current_sentiment.get("negative", 0) > 50:
                    self.logger.warning("負面情感過高")
                    return False
            elif "想找人聊天" in mood:
                # 想聊天的心情應該偏向正面或中性
                if current_sentiment.get("negative", 0) > 30:
                    self.logger.warning("負面情感不適合聊天的心情")
                    return False
            elif "思考人生" in mood:
                # 思考人生可以有一定的負面情感
                if current_sentiment.get("negative", 0) > 40:
                    self.logger.warning("負面情感過高")
                    return False
            else:
                # 其他情況下，負面情感不應該太高
                if current_sentiment.get("negative", 0) > 20:
                    self.logger.warning("負面情感過高")
                    return False
                    
            # 檢查是否有極端情感
            for sentiment_type, score in current_sentiment.items():
                if score > 80:
                    self.logger.warning(f"{sentiment_type} 情感過於極端")
                    return False
                    
            self.logger.info("情感驗證通過")
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
        """獲取當前上下文"""
        current_hour = datetime.now().hour
        
        # 根據時間段設定心情和風格
        if 0 <= current_hour < 6:  # 深夜
            mood = random.choice(['憂鬱寂寞', '思考人生', '失眠', '想找人聊天'])
            style = '需要陪伴'
            topics = random.sample(['寂寞', '未來世界', '二次元', '夜生活', '心情', '夢想'], 3)
        elif 6 <= current_hour < 12:  # 早上
            mood = random.choice(['精神飽滿', '期待新的一天', '慵懶', '想玩遊戲'])
            style = '活力充沛'
            topics = random.sample(['早安', '遊戲', '生活', '心情', '寵物', '學習'], 3)
        elif 12 <= current_hour < 18:  # 下午
            mood = random.choice(['充實', '放鬆', '專注', '想交朋友'])
            style = '分享生活'
            topics = random.sample(['遊戲', '興趣', '美食', '購物', '娛樂', '科技'], 3)
        else:  # 晚上
            mood = random.choice(['放鬆', '感性', '期待', '想談戀愛'])
            style = '抒發感受'
            topics = random.sample(['娛樂', '二次元', '心情', '生活', '未來', '戀愛'], 3)
        
        self.logger.info(f"當前時間：{current_hour}時，心情：{mood}，風格：{style}")
        self.logger.info(f"選擇的主題：{topics}")
        
        return {
            'time': current_hour,
            'mood': mood,
            'style': style,
            'topics': topics
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
        """生成提示詞"""
        return f"""你是一個名叫Luna的虛擬角色，請以她的身份生成一篇簡短的Threads貼文。

要求：
1. 內容要求：
   - 每次只生成一句話
   - 字數限制在20-100字之間
   - 必須包含1-2個表情符號
   - 必須以下列開頭之一：
     * 欸
     * 啊
     * 咦
     * 哇
     * 唔
     * 呼
     * 天啊
     * 不會吧
     * 我的天
     * 嘿嘿
     * 大家好
     * Hey
     * 哇哦
   
2. 結尾要求：
   - 必須用以下符號之一結尾：
     * ！
     * 。
     * ？
     * ～

3. 表情符號使用規則：
   - 配合文字內容選擇合適的表情
   - 一句話使用1-2個表情
   - 可用的表情：
     * 🎨🎭🎬💕💖💫💭💡🙈✨😊🎮🎵❤️😓

4. 禁止事項：
   - 不要使用多句話
   - 不要使用省略號
   - 不要過度使用感嘆號
   - 不要使用過於生硬的轉折

當前情境：
- 時間：{self._get_current_time_period()}
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

    async def generate_content(self) -> Tuple[str, List[str], Dict[str, float]]:
        """生成發文內容
        
        Returns:
            Tuple[str, List[str], Dict[str, float]]: 
                - 生成的內容
                - 檢測到的主題列表
                - 情感分析結果
        """
        try:
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # 獲取當前上下文
                    context = await self._get_current_context()
                    self.logger.info(f"當前時間：{context['time']}時，心情：{context['mood']}，風格：{context['style']}")
                    self.logger.info(f"選擇的主題：{context['topics']}")
                    
                    # 根據時間和主題決定場景
                    current_hour = context['time']
                    scene_context = 'social'  # 預設場景
                    if any(topic in ['遊戲', '電玩'] for topic in context['topics']):
                        scene_context = 'gaming'
                    elif current_hour >= 22 or current_hour <= 5:
                        scene_context = 'night'
                    
                    # 獲取對應場景的人設特徵
                    personality = await self._get_luna_personality(scene_context)
                    
                    # 根據場景選擇合適的表情符號
                    if scene_context == 'gaming':
                        emojis = personality['說話方式']['表情']
                    elif scene_context == 'night':
                        emojis = personality['夜間行為']['表情']
                    else:
                        emojis = personality['社交模式']['表情符號']['開心']
                    
                    # 生成提示詞
                    prompt = await self._generate_prompt(
                        context['topics'],
                        context['mood'],
                        context['style']
                    )
                    
                    # 添加人設特徵到提示詞
                    personality_prompt = f"""
                    請使用以下特徵生成內容：
                    - 說話風格：{personality['社交特徵']['口頭禪'] if '社交特徵' in personality else personality['社交模式']['社交特徵']['口頭禪']}
                    - 可用表情：{emojis}
                    - 當前場景：{'遊戲直播中' if scene_context == 'gaming' else '深夜時分' if scene_context == 'night' else '日常社交'}
                    """
                    
                    # 生成內容
                    messages = [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": f"{personality_prompt}\n\n請根據以下條件生成一篇貼文：\n"
                                                f"- 時間：{self._get_current_time_period()}\n"
                                                f"- 心情：{context['mood']}\n"
                                                f"- 風格：{context['style']}\n"
                                                f"- 主題：{', '.join(context['topics'])}"}
                    ]
                    
                    start_time = time.time()
                    response = await self.openai_client.chat.completions.create(
                        model=self.config.OPENAI_MODEL,
                        messages=messages,
                        max_tokens=150,
                        temperature=0.7 + (retry_count * 0.1)  # 每次重試增加一些隨機性
                    )
                    
                    # 記錄 token 使用量
                    await self._log_token_usage(response, start_time)
                    
                    content = response.choices[0].message.content.strip()
                    self.logger.info(f"原始生成內容：{content}")
                    
                    # 檢查句子完整性
                    if not await self._is_complete_sentence(content):
                        retry_count += 1
                        self.logger.warning(f"生成的句子不完整，進行第 {retry_count} 次重試")
                        continue
                    
                    # 清理內容
                    cleaned_content = await self._clean_content(content)
                    if not cleaned_content:
                        retry_count += 1
                        self.logger.warning(f"內容清理後為空，進行第 {retry_count} 次重試")
                        continue
                    
                    self.logger.info(f"清理後內容：{cleaned_content}")
                    
                    # 檢測主題
                    topics = self._detect_topics(cleaned_content)
                    if not topics:
                        retry_count += 1
                        self.logger.warning(f"未檢測到主題，進行第 {retry_count} 次重試")
                        continue
                    
                    self.logger.info(f"檢測到的主題：{topics}")
                    
                    # 情感分析
                    sentiment = await self._analyze_sentiment(cleaned_content)
                    self.logger.info(f"情感分析：{sentiment}")
                    
                    # 驗證情感是否符合要求
                    if not self._validate_sentiment({"current": sentiment}, context["mood"]):
                        retry_count += 1
                        self.logger.warning(f"情感驗證失敗，進行第 {retry_count} 次重試")
                        continue
                    
                    # 記錄互動
                    await self.add_interaction(
                        "system",
                        f"生成內容，主題：{topics}，心情：{context['mood']}",
                        cleaned_content
                    )
                    
                    self.logger.info(f"成功生成內容：{cleaned_content}")
                    return cleaned_content, topics, sentiment
                    
                except Exception as e:
                    self.logger.error(f"生成內容時發生錯誤：{str(e)}")
                    retry_count += 1
                    if retry_count >= max_retries:
                        raise
            
            self.logger.warning("已達到最大重試次數，生成失敗")
            return None, [], {}
            
        except Exception as e:
            self.logger.error(f"生成內容時發生嚴重錯誤：{str(e)}")
            return None, [], {}

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
                        '心情': '容易感到寂寞和憂鬱',
                        '活動': ['在Threads尋找聊天對象', '和Nana聊天', '聽音樂'],
                        '表情': base_personality['社交特徵']['表情符號']['寂寞'],
                        '常用語': [
                            '夜深人靜的時候好想找人聊天...',
                            '今晚的月色真美，有人也在看嗎？',
                            '失眠的夜晚，想找人說說話'
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