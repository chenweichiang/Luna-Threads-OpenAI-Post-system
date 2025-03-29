"""
ThreadsPoster AI 處理模組
處理與 OpenAI 的所有互動，整合記憶系統功能
Version: 1.1.0
Last Updated: 2025-03-29
"""

import logging
from datetime import datetime
import pytz
from openai import AsyncOpenAI
from src.config import Config
from src.utils import sanitize_text
import random
from typing import Optional, List, Dict, Any
import json
from collections import defaultdict
import asyncio
import time
import os

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
        self.character_config = config.CHARACTER_CONFIG
        self.logger = logging.getLogger(__name__)
        self.timezone = pytz.timezone("Asia/Taipei")  # 直接使用固定時區
        self.openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        self.keywords = config.KEYWORDS
        self.sentiment_dict = config.SENTIMENT_WORDS
        self.total_tokens = 0
        self.request_count = 0

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
            return False
            
        # 檢查結尾標點
        if not text.endswith("！"):
            return False
            
        # 檢查開頭詞
        valid_starts = ["天啊✨", "✨天啊", "我的天💫", "💫我的天"]
        if not any(text.startswith(start) for start in valid_starts):
            return False
            
        # 檢查表情符號數量
        emoji_count = sum(1 for c in text if c in "🎨🎭🎬💕💖💫💭💡🙈✨")
        if emoji_count < 1 or emoji_count > 2:
            return False
            
        # 檢查字數
        text_without_emoji = ''.join(c for c in text if c not in "🎨🎭🎬💕💖💫💭💡🙈✨")
        if len(text_without_emoji) > 20:
            return False
            
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
                    cleaned_text = sanitize_text(text, self.character_config["回文規則"]["字數限制"])
                    
                    if not await self._is_complete_sentence(cleaned_text):
                        self.logger.warning(f"生成的文本不完整，重試第 {retry_count + 1} 次")
                        retry_count += 1
                        continue
                    
                    sentiment = await self._analyze_sentiment(cleaned_text)
                    
                    if mood_info["mood"] == "精神飽滿" and sentiment["負面"] > 20:
                        self.logger.warning("情感過於負面，不符合精神飽滿的心情")
                        retry_count += 1
                        continue
                    elif mood_info["mood"] == "悠閒放鬆" and sentiment["負面"] > 30:
                        self.logger.warning("情感過於負面，不符合悠閒放鬆的心情")
                        retry_count += 1
                        continue
                    elif mood_info["mood"] == "感性浪漫" and sentiment["正面"] < 50:
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
            "BL": ["BL漫畫", "BL小說", "美劇", "CP", "同人文"],
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
            primary_categories = ["BL", "動漫"]
        else:  # 深夜
            mood = "深度思考"
            style = "文藝感性"
            primary_categories = ["BL", "心情"]
            
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
        """
        分析文本的情感，將情感分為正面、中性、負面三種
        
        Args:
            text: 要分析的文本
            
        Returns:
            Dict[str, float]: 情感分析結果（百分比）
        """
        # 定義情感關鍵詞權重
        sentiment_weights = {
            '正面': {
                '極高': ['超愛', '太棒了', '完美', '震撼', '傑作', '神作', '驚艷', '感動到哭'],
                '很高': ['好棒', '優秀', '精彩', '讚嘆', '推薦', '喜歡', '期待', '驚喜'],
                '中高': ['不錯', '還好', '可以', '還行', '普通', '一般', '正常'],
                '偏高': ['有趣', '有意思', '值得一看', '還不錯'],
                '略高': ['還可以', '勉強', '將就', '湊合']
            },
            '中性': {
                '極中': ['思考', '觀察', '分析', '研究', '探討', '評估'],
                '很中': ['看看', '試試', '考慮', '觀望', '等等'],
                '中等': ['或許', '可能', '也許', '大概', '應該'],
                '偏中': ['不確定', '不一定', '再說', '再看'],
                '略中': ['隨便', '都行', '無所謂', '沒差']
            },
            '負面': {
                '極低': ['糟糕', '失望', '討厭', '噁心', '垃圾', '廢物', '爛透'],
                '很低': ['不好', '不行', '差勁', '糟糕', '難看'],
                '中低': ['不太好', '不太行', '不太喜歡', '不太適合'],
                '偏低': ['有點差', '有點不好', '有點不行'],
                '略低': ['不太確定', '不太懂', '不太了解']
            }
        }
        
        # 定義表情符號權重
        emoji_weights = {
            '正面': {
                '極高': ['💖', '✨', '💫', '🎉', '💝', '💕', '💗', '🌟'],
                '很高': ['😊', '🥰', '😍', '🤗', '💪', '👍'],
                '中高': ['😌', '😃', '😄', '😁', '🙂'],
                '偏高': ['🙃', '😉', '😏', '😼'],
                '略高': ['🤔', '🤨', '🧐', '🤓']
            },
            '中性': {
                '極中': ['💭', '🤔', '🧐', '📝', '🔍'],
                '很中': ['👀', '👁️', '🗣️', '👥'],
                '中等': ['💬', '💡', '💫', '✨'],
                '偏中': ['🌐', '📊', '📈', '📉'],
                '略中': ['⚖️', '🔄', '🔁', '↔️']
            },
            '負面': {
                '極低': ['😱', '😨', '😰', '😢', '😭', '😤'],
                '很低': ['😒', '😕', '😟', '😔', '😣'],
                '中低': ['😐', '😑', '😶', '🤐'],
                '偏低': ['😅', '😓', '😥', '😮'],
                '略低': ['🤨', '🧐', '🤔', '❓']
            }
        }

        # 初始化情感分數
        sentiment_scores = {
            '正面': {'極高': 0, '很高': 0, '中高': 0, '偏高': 0, '略高': 0},
            '中性': {'極中': 0, '很中': 0, '中等': 0, '偏中': 0, '略中': 0},
            '負面': {'極低': 0, '很低': 0, '中低': 0, '偏低': 0, '略低': 0}
        }
        
        # 分析文字情感
        for sentiment in sentiment_weights:
            for level in sentiment_weights[sentiment]:
                for word in sentiment_weights[sentiment][level]:
                    if word in text:
                        sentiment_scores[sentiment][level] += 1
        
        # 分析表情符號情感
        for sentiment in emoji_weights:
            for level in emoji_weights[sentiment]:
                for emoji in emoji_weights[sentiment][level]:
                    if emoji in text:
                        sentiment_scores[sentiment][level] += 0.5  # 表情符號權重為0.5
        
        # 計算總分
        total_score = sum(sum(scores.values()) for scores in sentiment_scores.values())
        if total_score == 0:
            # 如果沒有檢測到任何情感，設為中性
            return {'正面': 0.0, '中性': 100.0, '負面': 0.0}
        
        # 計算每種情感的總百分比
        result = {}
        for sentiment in sentiment_scores:
            total_sentiment = sum(sentiment_scores[sentiment].values())
            result[sentiment] = round((total_sentiment / total_score) * 100, 1)
        
        logging.info(f"情感分析結果：正面 {result['正面']}%, 中性 {result['中性']}%, 負面 {result['負面']}%")
        return result

    def _validate_sentiment(self, sentiment_scores: Dict[str, Dict[str, float]], mood: str) -> bool:
        """
        驗證情感分析結果是否符合要求
        
        Args:
            sentiment_scores: 情感分析結果
            mood: 當前心情
            
        Returns:
            bool: 是否符合要求
        """
        # 計算各情感類型的總分
        totals = {
            sentiment: sum(scores.values())
            for sentiment, scores in sentiment_scores.items()
        }
        
        # 檢查是否過於負面
        if totals['負面'] > 30:  # 負面情感不能超過30%
            logging.warning(f"情感過於負面：{totals['負面']}%")
            return False
            
        # 檢查是否情感太過極端
        for sentiment in sentiment_scores:
            if sentiment_scores[sentiment].get('極高', 0) > 50 or \
               sentiment_scores[sentiment].get('極低', 0) > 50:
                logging.warning(f"情感過於極端：{sentiment}")
                return False
                
        # 檢查是否情感分布太過集中
        for sentiment in sentiment_scores:
            for level, score in sentiment_scores[sentiment].items():
                if score > 70:  # 單一等級不能超過70%
                    logging.warning(f"情感分布過於集中：{sentiment} {level} {score}%")
                    return False
        
        return True

    async def _build_character_prompt(self, current_hour: str) -> str:
        """建立角色提示詞
        
        Args:
            current_hour: 當前小時
            
        Returns:
            str: 角色提示詞
        """
        character_info = self.character_config["基本資料"]
        
        prompt = f"""你是一個{character_info["年齡"]}歲的{character_info["國籍"]}{character_info["性別"]}。
        個性特徵：{', '.join(character_info["個性特徵"])}
        興趣：{', '.join(character_info["興趣"])}
        
        嚴格按照以下格式生成一句話回覆：
        
        1. 必須使用以下開頭（二選一）：
           - 「天啊✨」或「✨天啊」
           - 「我的天💫」或「💫我的天」
        
        2. 內容規則：
           - 必須是完整的一句話
           - 必須包含主題關鍵詞
           - 結尾必須用「！」結束
           - 字數限制在20字以內
           - 必須加入1-2個表情符號（🎨 🎭 🎬 💕 💖 💫 💭 💡 🙈 ✨）
        
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
        for interest in self.character_config["基本資料"]["興趣"]:
            if interest.lower() in text.lower():
                topics.append(interest)
        
        # 檢查 ACG 相關主題
        acg_keywords = ["漫畫", "動畫", "遊戲", "輕小說", "同人", "聲優", "角色", "劇情"]
        for keyword in acg_keywords:
            if keyword in text:
                topics.append(f"ACG-{keyword}")
                
        # 檢查 BL 相關主題
        bl_keywords = ["CP", "BL", "配對", "耽美", "糖分", "攻受"]
        for keyword in bl_keywords:
            if keyword in text:
                topics.append(f"BL-{keyword}")
                
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

    async def generate_content(self) -> tuple[str, List[str], Dict[str, float]]:
        """生成內容
        
        Returns:
            tuple[str, List[str], Dict[str, float]]: 生成的內容、主題列表和情感分析結果
        """
        try:
            current_hour = datetime.now(self.timezone).hour
            mood_info = await self._get_current_mood(current_hour)
            
            prompt = await self._build_character_prompt(str(current_hour))
            topic_prompt = f"""請圍繞以下主題生成內容：{', '.join(mood_info['topics'])}
            記住：必須以「天啊✨」、「✨天啊」、「我的天💫」或「💫我的天」開頭，並以「！」結尾。
            範例：
            - 天啊✨這部BL漫畫太甜了💕！
            - ✨天啊這個CP好有愛💫！
            - 我的天💫這個劇情好感人💕！
            - 💫我的天這個結局太美好了✨！
            """
            
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
                        max_tokens=50,
                        temperature=0.7,
                        presence_penalty=0.6,
                        frequency_penalty=0.6
                    )
                    
                    # 記錄 token 使用量
                    await self._log_token_usage(response, start_time)
                    
                    text = response.choices[0].message.content.strip()
                    self.logger.info(f"原始生成內容：{text}")
                    
                    cleaned_text = sanitize_text(text, self.character_config["回文規則"]["字數限制"])
                    self.logger.info(f"清理後內容：{cleaned_text}")
                    
                    # 檢查文本完整性
                    if not await self._is_complete_sentence(cleaned_text):
                        self.logger.warning(f"文本完整性檢查失敗：{cleaned_text}")
                        retry_count += 1
                        continue
                    
                    # 檢查主題關鍵詞
                    topics = await self._extract_topics(cleaned_text)
                    if not topics:
                        self.logger.warning(f"未檢測到主題關鍵詞：{cleaned_text}")
                        retry_count += 1
                        continue
                    
                    # 分析情感
                    sentiment = await self._analyze_sentiment(cleaned_text)
                    
                    # 檢查情感是否符合心情
                    if mood_info["mood"] == "深度思考" and sentiment["負面"] > 30:
                        self.logger.warning(f"情感不符合深度思考心情：{sentiment}")
                        retry_count += 1
                        continue
                    
                    self.logger.info(f"成功生成內容：{cleaned_text}")
                    self.logger.info(f"檢測到的主題：{topics}")
                    self.logger.info(f"情感分析：{sentiment}")
                    
                    return cleaned_text, topics, sentiment
                    
                except Exception as e:
                    self.logger.error(f"生成內容時發生錯誤：{str(e)}")
                    retry_count += 1
            
            raise AIError("生成的內容不符合完整性要求")
            
        except Exception as e:
            self.logger.error(f"生成內容時發生錯誤：{str(e)}")
            raise AIError(f"生成內容失敗：{str(e)}")