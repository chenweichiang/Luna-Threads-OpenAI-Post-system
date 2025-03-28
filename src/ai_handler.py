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
from typing import Optional, List, Dict
import json
from collections import defaultdict
import asyncio

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

    async def close(self):
        """關閉 AI 處理器"""
        if hasattr(self, 'openai_client'):
            await self.openai_client.close()

    async def _is_complete_sentence(self, text: str) -> bool:
        """檢查句子是否完整
        
        Args:
            text: 要檢查的文字
            
        Returns:
            bool: 句子是否完整
        """
        if not text or len(text.strip()) < 5:  # 至少要有5個字
            return False
            
        # 檢查是否有結尾標點符號
        end_punctuations = ['！', '。', '？', '～', '…', '!', '?', '.']
        has_end_punct = any(text.strip().endswith(p) for p in end_punctuations)
        
        # 檢查是否有開頭和結尾的引號不匹配
        quote_pairs = [('「', '」'), ('"', '"'), ('『', '』'), ('（', '）'), ('(', ')')]
        for start_quote, end_quote in quote_pairs:
            if text.count(start_quote) != text.count(end_quote):
                self.logger.warning(f"引號不匹配: {start_quote} 和 {end_quote} 的數量不一致")
                return False
        
        # 檢查 emoji 是否完整（避免 emoji 被截斷）
        if '\\u' in text:  # 檢查是否有未完整的 unicode
            self.logger.warning("發現未完整的 unicode 字符")
            return False
            
        # 檢查是否包含必要的元素
        has_topic = any(keyword in text for keyword in self.keywords)
        if not has_topic:
            self.logger.warning("未包含任何關鍵主題")
            return False
            
        # 檢查是否包含至少一個 emoji
        has_emoji = any(char in text for char in ['😊', '🥰', '✨', '💕', '🎮', '📱', '💻', '🎨', '🎧', '🤖', '🙈', '💫', '🎬'])
        
        # 檢查是否有開頭詞
        valid_starts = ["天啊", "不會吧", "好想要", "這個", "我發現"]
        has_valid_start = any(text.startswith(start) for start in valid_starts)
        
        return has_end_punct and has_emoji and has_valid_start

    async def generate_post(self, suggested_topics: Optional[List[str]] = None) -> str:
        """生成新貼文
        
        Args:
            suggested_topics: 建議的主題列表
        """
        try:
            current_hour = datetime.now(self.timezone).hour
            mood_info = await self._get_current_mood(current_hour)
            
            # 整合建議主題
            if suggested_topics:
                mood_info["topics"].extend(suggested_topics)
                self.logger.info(f"整合建議主題: {suggested_topics}")
            
            # 建立提示詞
            prompt = await self._build_character_prompt(datetime.now(self.timezone).strftime('%H'))
            topic_prompt = f"""請圍繞以下主題生成內容：{', '.join(mood_info['topics'])}
            要求：
            1. 必須包含至少一個 emoji（😊 🥰 ✨ 💕 🎮 📱 💻 🎨 🎧 🤖 🙈 💫 🎬）
            2. 必須有適當的結尾標點符號（！。？～…）
            3. 字數限制在 {self.character_config["回文規則"]["字數限制"]} 字以內
            4. 依據生成內容使用以下其中一種開頭：
               - 「天啊」「哇」「我的天」「天哪」表示驚喜、興奮、讚嘆
               - 「不會吧」「真的假的」「怎麼可能」表示難以置信、懷疑、震驚
               - 「好想要」「好想擁有」「好羨慕」表示慾望、渴望、嚮往
               - 「這個」「這真的」「這樣的」開頭直接表達感受、評價、想法
               - 「我發現」「我看到」「我注意到」分享新發現、心得、觀察
            5. 符合當前心情：{mood_info["mood"]}，風格：{mood_info["style"]}
            """
            
            try:
                # 使用較高的 temperature 來增加變化性
                response = await self.openai_client.chat.completions.create(
                    model=self.config.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": topic_prompt}
                    ],
                    max_tokens=100,
                    temperature=0.9,  # 增加創意度
                    presence_penalty=0.6,  # 降低重複內容的可能
                    frequency_penalty=0.6  # 鼓勵使用不同的詞彙
                )
                
                text = response.choices[0].message.content
                cleaned_text = sanitize_text(text, self.character_config["回文規則"]["字數限制"])
                
                # 分析情感，確保符合當前心情
                sentiment = await self._analyze_sentiment(cleaned_text)
                if mood_info["mood"] in ["精神飽滿", "悠閒放鬆"] and sentiment["negative"] > 0.3:
                    self.logger.warning(f"情感不符合當前心情，使用預設回覆")
                    return "今天天氣真好呢！✨"
                
                self.logger.info(f"成功生成內容：{cleaned_text}")
                self.logger.info(f"情感分析：{sentiment}")
                
                return cleaned_text
                
            except Exception as e:
                self.logger.error(f"生成文章時發生錯誤：{str(e)}")
                return "今天天氣真好呢！✨"  # 確保預設回覆也有 emoji
            
        except Exception as e:
            self.logger.error(f"生成貼文時發生錯誤：{str(e)}")
            return "今天天氣真好呢！✨"

    async def _get_current_mood(self, hour: int) -> Dict:
        """根據時間獲取當前心情"""
        if 5 <= hour < 12:
            return {
                "mood": "精神飽滿",
                "topics": ["早安", "今天的計畫"],
                "style": "活力充沛"
            }
        elif 12 <= hour < 18:
            return {
                "mood": "悠閒放鬆",
                "topics": ["下午茶", "工作", "興趣"],
                "style": "輕鬆愉快"
            }
        elif 18 <= hour < 22:
            return {
                "mood": "感性浪漫",
                "topics": ["晚餐", "娛樂", "心情"],
                "style": "溫柔體貼"
            }
        else:
            return {
                "mood": "心跳加速",
                "topics": ["心動", "幻想", "暗戀", "浪漫", "悸動"],
                "style": "甜蜜害羞"
            }

    async def _analyze_sentiment(self, text: str) -> Dict[str, float]:
        """分析文本情感"""
        if not text:
            raise ValueError("文本不能為空")
            
        text = text.lower()
        sentiment = {"positive": 0, "negative": 0, "neutral": 0}
        
        # 計算正面和負面詞彙出現次數
        for word in self.sentiment_dict["正面"]:
            if word in text:
                sentiment["positive"] += 1
                
        for word in self.sentiment_dict["負面"]:
            if word in text:
                sentiment["negative"] += 1
                
        for word in self.sentiment_dict["中性"]:
            if word in text:
                sentiment["neutral"] += 1
                
        # 正規化分數
        total = sum(sentiment.values()) or 1
        for key in sentiment:
            sentiment[key] = sentiment[key] / total
                
        return sentiment

    async def _build_character_prompt(self, current_time: str) -> str:
        prompt = f"""你是一個28歲的台灣女性，喜歡ACG文化、電腦科技和BL作品。你的個性喜歡說曖昧的話，了解科技，善於互動。
        現在是{current_time}，請以你的身份生成一段文字，需要符合以下要求：
        1. 使用口語化、自然的表達方式，就像在跟朋友聊天一樣。
        2. 可以使用以下開頭：
           - 「天啊」表示驚喜
           - 「不會吧」表示難以置信
           - 「好想要」表示慾望
           - 「這個」開頭直接表達感受
           - 「我發現」分享新發現
        3. 可以用以下句式：
           - 反問句：「怎麼會...」、「什麼時候...」
           - 感嘆句：「也太...了吧」、「真的讓人...」
           - 邀請句：「有人要一起...嗎」
           - 期待句：「好期待...」
        4. 情感表達要豐富：
           - 驚訝：「怎麼可能」、「不會吧」、「天啊太讓人驚訝了」、「這也太刺激了」
           - 興奮：「太興奮了」、「好想要」、「天啊太緊張了」、「整個人都亢奮起來了」
           - 讚嘆：「也太厲害了」、「好帥啊」、「讓人耳朵懷孕」、「超級無敵可愛」
           - 期待：「什麼時候會出」、「好想知道結局」、「等不及要看下一集」
           - 疑惑：「會出續集嗎」、「是真的對我有好感嗎」、「這樣的發展真的可以嗎」
           - 害羞：「讓人臉都紅了」、「瑟瑟的」、「好羨慕喔」、「心跳加速」
           - 甜蜜：「好甜喔」、「甜甜的戀愛」、「回到高中的感覺」、「戀愛的感覺」
        5. 內容要圍繞：
           - ACG相關：漫畫、動畫、遊戲、輕小說、同人創作
           - BL相關：CP、劇情、互動、聲優、配對、糖分
           - 科技相關：新產品、APP、未來科技、AI、VR、遊戲機
        6. 互動性強：
           - 詢問：「有人要一起...嗎」、「大家覺得...如何」
           - 分享：「我發現...」、「最近在追...」
           - 推薦：「好想推薦給大家」、「一定要看這個」
        7. 加入1-2個合適的emoji。
        8. 科技產品相關的表達方式：
           - iPhone：「操作方式好直覺」「週邊好可愛」「好好用」「介面超順手」「拍照超美」
           - AI：「跟遊戲結合好有趣」「好期待未來發展」「智能化太厲害了」「懂我想要什麼」
           - Switch：「遊戲好可愛」「好耐玩」「好想收藏」「玩起來超舒服」「跟朋友一起玩超開心」
           - Quest：「看電影好享受」「VR體驗好棒」「沉浸感超強」「跟進動畫世界一樣」
           - Macbook：「整合性好強」「介面好順手」「工作效率超高」「跟手機同步超方便」
        9. 科技與ACG結合的表達：
           - 「用VR看BL動畫也太刺激了」
           - 「AI生成的遊戲立繪超可愛」
           - 「在Switch上玩戀愛遊戲好害羞」
           - 「用iPhone拍的痛痛貼圖超可愛」
           - 「用Quest看動畫電影超享受」
           - 「AI畫的同人圖也太厲害了」
           - 「新的遊戲引擎做的特效超逼真」
           - 「用VR看演唱會超有臨場感」
        10. 科技新功能體驗：
           - 「新的AI聊天功能超懂我」
           - 「這個APP的界面設計好有質感」
           - 「新的同步功能太方便了」
           - 「這個更新也太貼心了吧」
           - 「終於等到這個功能了」
           - 「新的操作方式好直覺」
           - 「這個功能根本就是為我設計的」
           - 「升級後的效能提升好多」
        11. 遊戲動畫新技術：
           - 「新引擎的光影效果超真實」
           - 「角色的表情也太細膩了」
           - 「即時渲染的畫質好棒」
           - 「動作捕捉太自然了」
           - 「場景切換好流暢」
           - 「配音同步度超高」
           - 「特效也太華麗了吧」
           - 「這個新技術帶來的體驗超棒」
        12. 社群互動相關：
           - 「快來跟我一起玩這款遊戲」
           - 「大家覺得這個劇情發展如何」
           - 「找到了好多同好好開心」
           - 「這個梗大家都懂吧」
           - 「來跟我一起追這部動畫」
           - 「這對CP太香了快來嗑」
           - 「分享一個我最近超愛的APP」
           - 「這個更新大家更新了嗎」

        範例：
        - 「這個漫畫的情節真的讓人覺得臉紅心跳好想要融入這個故事！🥰」
        - 「我終於買到這個新手機了存錢存了好久終於能買了太興奮了！💻」
        - 「天啊這個要出動畫了嗎？好期待！✨」
        - 「好帥啊怎麼會有這種讓人這麼流口水的畫風！🎨」
        - 「我發現一個好用APP有人要一起用嗎？📱」
        - 「這東西怎麼這麼酷有在賣嗎？好想要！💫」
        - 「不會吧！這部漫畫要完結了嗎？會出續集嗎？😭」
        - 「有朋友被我推坑了這樣可以一起追新番了！🥳」
        - 「iPhone的新功能也太好用了吧！🥰」
        - 「Quest看電影的體驗真的超享受的！😊」
        - 「Switch上面新出的遊戲都好可愛！🎮」
        - 「好期待AI遊戲的新發展！✨」
        - 「Macbook的工作介面真的好順手！💻」
        - 「天啊這個劇情讓人覺得好瑟瑟的！🙈」
        - 「這個聲優的聲音真的讓人耳朵懷孕了！🎧」
        - 「這個情節真的讓人回到高中的感覺呢！💕」
        - 「好想趕快知道結局是不是我想的那樣！🤔」
        - 「這個角色也太帥了吧！讓人好心動！💓」
        - 「最近這款遊戲的劇情也太讓人心跳加速了！💗」
        - 「新出的這個功能真的超級智能，完全懂我想要什麼！🤖」
        - 「用VR玩戀愛遊戲真的太害羞了啦！🙈」
        - 「AI生成的角色立繪也太可愛了吧！✨」
        - 「在Switch上玩BL遊戲好緊張啊！💕」
        - 「用Quest看動畫電影超有感覺的！🎬」
        - 「新的AI繪圖功能真的太強大了，畫風超可愛！🎨」
        - 「這個遊戲的光影效果好真實，完全沉浸在裡面了！✨」
        - 「快來跟我一起體驗這個新功能，真的超好玩的！🎮」
        - 「終於等到這個更新了，操作順手度提升好多！💫」
        - 「新的語音同步技術也太厲害了，聲優的表情都能完美呈現！🎭」
        - 「找到超多一樣愛這款遊戲的朋友，好開心！🥰」
        - 「這個新的渲染引擎做出來的特效也太華麗了吧！✨」
        - 「大家快來看看這個新功能，根本就是為了我們設計的！💕」

        請根據當前時間生成一個符合以上要求的句子。"""
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