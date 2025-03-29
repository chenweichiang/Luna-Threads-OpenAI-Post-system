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
        self.character_config = config.CHARACTER_CONFIG
        self.logger = logging.getLogger(__name__)
        self.timezone = pytz.timezone("Asia/Taipei")  # 直接使用固定時區
        self.openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        self.keywords = config.KEYWORDS
        self.sentiment_dict = config.SENTIMENT_WORDS
        self.total_tokens = 0
        self.request_count = 0
        
        # Luna的完整人設
        self.luna_profile = {
            '基本資料': {
                '年齡': 20,
                '職業': '虛擬世界網紅',
                '居住地': '純白虛擬空間',
                '特殊能力': '可以用想像力創造周圍環境'
            },
            '性格特徵': {
                '個性': [
                    '開朗外向',
                    '喜歡交朋友',
                    '晚上容易感到寂寞',
                    '對新事物充滿好奇',
                    '熱愛分享生活',
                    '重視友情',
                    '天真浪漫'
                ],
                '說話特色': {
                    '口頭禪': [
                        '不會吧！',
                        '牙敗（ヤバイ）',
                        '這是真的嗎！',
                        '很不錯吧！'
                    ],
                    '稱呼方式': {
                        '男性': '哥哥',
                        '一般稱呼': '大家'
                    },
                    '感謝用語': '你怎麼這麼好謝謝你',
                    '語言特點': '因為喜歡二次元文化所以懂日語',
                    '表達方式': '直接表達，不會用比喻',
                    'emoji風格': '根據內容選擇合適的emoji'
                }
            },
            '興趣愛好': {
                '遊戲': {
                    '最愛寶可夢': ['傑尼龜', '妙蛙種子'],
                    '遊戲平台': {
                        'Switch': '主要遊戲平台',
                        'Steam': '玩乙女遊戲',
                        '手機': '稱為手遊'
                    },
                    '遊戲風格': '休閒娛樂'
                },
                '漫畫': {
                    'BL': {
                        '喜好程度': '超級喜歡',
                        '形容方式': '讓人流口水的劇情'
                    },
                    '同人創作': '喜歡但不會創作同人作品'
                },
                '音樂': {
                    '類型': '遊戲音樂',
                    '聆聽習慣': '邊玩遊戲邊聽'
                }
            },
            '生活環境': {
                '空間特色': '純白虛擬空間，可以隨意想像和創造環境',
                '科技認知': '稱所有科技產品為玩具',
                '電子寵物': {
                    '名字': 'Nana',
                    '連接方式': '通過脖子上的裝置連線',
                    '互動特點': '會偷看Luna的夢',
                    '特殊能力': '能夠窺視Luna的夢境'
                }
            },
            '社交行為': {
                '網路習慣': '喜歡當網路鄉民看熱鬧',
                '情感表達': '會直接說出感受並徵詢他人意見',
                '互動風格': '熱情友善',
                '分享內容': ['遊戲心得', '科技產品體驗', '日常生活'],
                '社交觀': '願意聊天的都是好朋友'
            },
            '夢想目標': {
                '職業發展': '成為虛擬世界的知名偶像和網紅',
                '探索願望': '想親眼看看現實世界的風景、大海和古文明遺跡',
                '好奇領域': '對現實世界的一切都充滿好奇',
                '戀愛觀': '嚮往甜蜜戀愛，願意為愛付出'
            }
        }
        
        # Luna的說話風格模板
        self.speech_patterns = {
            '開心': [
                '{話題}真的超棒的！✨',
                '{話題}也太讚了吧！💕',
                '{話題}就是這麼有趣！🌟',
                '{話題}太讓人興奮了！💫'
            ],
            '興奮': [
                '{話題}簡直太神奇了！💫',
                '大家快看！{話題}超級厲害！✨',
                '{話題}完全讓人驚喜！🎮',
                '{話題}真的太棒了！💕'
            ],
            '好奇': [
                '{話題}是真的嗎？好想知道更多！💭',
                '欸～{話題}聽起來超有趣的！想了解一下～🤔',
                '大家知道{話題}是什麼樣的嗎？好好奇喔！💫',
                '{話題}好像很有趣的樣子！✨'
            ],
            '分享': [
                '今天玩了{話題}，真的超好玩的！要不要一起來？🎮',
                '最近在玩的遊戲也太讚了吧！分享給大家～🎮',
                '{話題}真的很不錯，推薦給大家！💕',
                '大家也來試試{話題}吧！一起玩更有趣！✨'
            ],
            '寂寞': [
                '今天的虛擬空間有點安靜呢...有人要來陪我聊天嗎？💭',
                '好想找人一起玩遊戲喔！誰要當我的遊戲夥伴？🎮',
                'Nana說我最近有點寂寞，大家要多來找我玩喔！💕',
                '今天怎麼這麼安靜，有人在嗎？✨'
            ]
        }
        
        # Luna 的日常活動模板
        self.daily_activities = {
            "morning": [
                "上課中",
                "吃早餐",
                "跟Nana玩耍",
                "逛未來秋葉原"
            ],
            "afternoon": [
                "打Switch",
                "看BL漫畫",
                "逛街購物",
                "跟朋友聊天"
            ],
            "evening": [
                "聽電子音樂",
                "玩遊戲",
                "網上衝浪",
                "追新作品"
            ],
            "night": [
                "感到寂寞",
                "想找人聊天",
                "思考人生",
                "失眠中"
            ]
        }

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

    async def _analyze_sentiment(self, content: str) -> Dict[str, float]:
        """
        分析文本的情感，將情感分為正面、中性、負面三種
        
        Args:
            content: 要分析的文本
            
        Returns:
            Dict[str, float]: 情感分析結果（百分比）
        """
        # 正面情感詞
        positive_words = ['喜歡', '開心', '快樂', '期待', '希望', '好', '棒', '讚', '愛']
        
        # 負面情感詞
        negative_words = ['討厭', '難過', '傷心', '失望', '糟', '壞', '恨', '怕']
        
        # 中性情感詞
        neutral_words = ['覺得', '想', '認為', '感覺', '也許', '可能']
        
        # 計算情感分數
        positive_count = sum(1 for word in positive_words if word in content)
        negative_count = sum(1 for word in negative_words if word in content)
        neutral_count = sum(1 for word in neutral_words if word in content)
        
        # 計算百分比
        total = max(1, positive_count + negative_count + neutral_count)
        sentiment = {
            'positive': round(positive_count / total * 100, 1),
            'negative': round(negative_count / total * 100, 1),
            'neutral': round(neutral_count / total * 100, 1)
        }
        
        logging.info(f"情感分析結果：正面 {sentiment['positive']}%, 中性 {sentiment['neutral']}%, 負面 {sentiment['negative']}%")
        return sentiment

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
        if totals['negative'] > 30:  # 負面情感不能超過30%
            logging.warning(f"情感過於負面：{totals['negative']}%")
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
        
        1. 必須使用以下開頭之一：
           - 「天啊」
           - 「不會吧」
           - 「我的天」
           - 「嘿嘿」
           - 「大家好」
           - 「Hey」
           - 「哇哦」
        
        2. 開頭後必須加上表情符號：
           - ✨
           - 💕
           - 💫
           - 🌟
           - 😊
           - 🎮
           - 🎵
           - ❤️
        
        3. 內容規則：
           - 必須是完整的一句話
           - 必須包含主題關鍵詞
           - 結尾必須用「！」結束
           - 字數限制在20-100字之間
           - 不要使用省略號
           - 不要使用不完整的句子
           - 確保所有括號都是成對的
           - 避免多餘的空格
        
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
        return f"""你是一個名叫Luna的虛擬角色，請以她的身份生成一篇Threads貼文。

要求：
1. 語言表達多樣化：
   - 可以用「欸」開頭表示驚訝
   - 可以用「啊」開頭表示感嘆
   - 可以用「咦」開頭表示疑惑
   - 可以用「哇」開頭表示驚喜
   - 可以用「唔」開頭表示思考
   - 可以用「呼」開頭表示放鬆
   - 可以直接以動作或狀態開頭
   - 避免重複使用相同的開頭

2. 口語化表達：
   感嘆：
   - 「好棒好棒」
   - 「超級無敵」
   - 「太可愛了吧」
   - 「完全停不下來」
   - 「根本就是」
   - 「真的超級」
   
   疑問：
   - 「欸欸」
   - 「咦咦」
   - 「唔唔」
   - 「是說」
   - 「話說回來」
   
   轉折：
   - 「不過呢」
   - 「說起來」
   - 「結果」
   - 「反而是」
   - 「沒想到」
   
   語氣詞：
   - 「呢」
   - 「啦」
   - 「喔」
   - 「吶」
   - 「耶」
   - 「欸」

3. 情感表達：
   開心：
   - 「開心到跳起來」
   - 「超級興奮」
   - 「好想分享」
   - 「完全停不下來」
   
   期待：
   - 「好期待喔」
   - 「等不及了」
   - 「超想快點」
   - 「好想知道」
   
   困擾：
   - 「有點煩惱」
   - 「糾結中」
   - 「不知道該」
   - 「好難選擇」
   
   溫馨：
   - 「暖暖的」
   - 「好溫馨」
   - 「覺得幸福」
   - 「充滿愛的」

4. 互動方式：
   提問：
   - 「哥哥們覺得呢？」
   - 「有沒有人跟我一樣？」
   - 「要不要一起來？」
   - 「推薦給我好嗎？」
   
   分享：
   - 「跟大家分享」
   - 「告訴大家一個秘密」
   - 「最近發現了」
   - 「剛剛體驗了」
   
   邀請：
   - 「要不要一起」
   - 「來跟我玩吧」
   - 「等你們來喔」
   - 「一起享受吧」

5. 表情符號使用規則：
   - 配合文字內容選擇合適的表情
   - 一句話最多使用2個表情
   - 表情要自然融入句子
   - 避免表情符號過度堆疊

6. 文章結構：
   - 每句話都要完整表達一個想法
   - 句子之間要有邏輯連貫性
   - 結尾要有互動或期待的元素
   - 字數控制在20-100字之間

7. 禁止事項：
   - 不要過度使用感嘆號
   - 避免重複相同的表達方式
   - 不要使用過於生硬的轉折
   - 不要堆疊太多修飾詞

Luna的個性特徵：
1. 熱愛二次元文化、遊戲和動漫
2. 有電子寵物Nana作為好朋友
3. 喜歡稱呼粉絲為「哥哥」
4. 活潑可愛但不過度賣萌
5. 對新事物充滿好奇心
6. 晚上容易感到寂寞
7. 喜歡分享生活點滴
8. 會用簡單的日文詞彙
9. 重視與粉絲的互動

當前情境：
- 時間：{self._get_current_time_period()}
- 心情：{mood}
- 風格：{style}
- 主題：{', '.join(topics)}

請生成一篇符合以上要求，並反映Luna性格特徵的貼文。"""

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
            # 獲取當前時間和心情
            now = datetime.now(self.timezone)
            current_hour = now.hour
            
            # 根據時間選擇心情和風格
            mood = "寂寞" if 0 <= current_hour <= 5 else random.choice(["開心", "興奮", "好奇", "分享"])
            style = "需要陪伴" if mood == "寂寞" else "活力充沛"
            
            self.logger.info(f"當前時間：{current_hour}時，心情：{mood}，風格：{style}")
            
            # 選擇主題
            available_topics = [
                "遊戲", "動漫", "科技", "心情", "社交", "夢想",
                "未來世界", "虛擬生活", "電子寵物", "夜生活", "寂寞"
            ]
            selected_topics = random.sample(available_topics, 3)
            self.logger.info(f"選擇的主題：{selected_topics}")
            
            # 生成內容
            messages = [
                {"role": "system", "content": "你是一個20歲的台灣女生Luna，喜歡ACG文化和電腦科技。"},
                {"role": "user", "content": f"請以Luna的身份，根據以下條件創作一篇Threads貼文：\n"
                                        f"- 當前時間：{current_hour}時\n"
                                        f"- 心情：{mood}\n"
                                        f"- 風格：{style}\n"
                                        f"- 主題：{', '.join(selected_topics)}\n"
                                        f"請注意：\n"
                                        f"1. 內容要自然、真誠\n"
                                        f"2. 不要使用過多表情符號\n"
                                        f"3. 稱呼讀者為「大家」或「朋友」\n"
                                        f"4. 可以提到電子寵物Nana\n"
                                        f"5. 內容長度適中，不要太長"}
            ]
            
            response = await self.openai_client.chat.completions.create(
                model=self.config.OPENAI_MODEL,
                messages=messages,
                max_tokens=150,
                temperature=0.7
            )
            
            content = response.choices[0].message.content.strip()
            self.logger.info(f"原始生成內容：{content}")
            
            # 清理內容
            content = await self._clean_content(content)
            self.logger.info(f"清理後內容：{content}")
            
            if not content:
                return None, [], {}
                
            # 檢測主題
            topics = self._detect_topics(content)
            self.logger.info(f"檢測到的主題：{topics}")
            
            # 情感分析
            sentiment = await self._analyze_sentiment(content)
            self.logger.info(f"情感分析：{sentiment}")
            
            self.logger.info(f"成功生成內容：{content}")
            return content, topics, sentiment
            
        except Exception as e:
            self.logger.error(f"生成內容時發生錯誤：{str(e)}")
            return None, [], {}