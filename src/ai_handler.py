"""
ThreadsPoster AI 處理模組
處理與 OpenAI 的所有互動
"""

import logging
from datetime import datetime
import pytz
from openai import AsyncOpenAI
from src.config import Config
import random
from typing import Optional, List, Dict

class AIError(Exception):
    """AI 相關錯誤"""
    pass

class AIHandler:
    """AI 處理器"""
    def __init__(self, config: Config):
        """初始化 AI 處理器"""
        self.config = config
        self.model = config.OPENAI_MODEL
        self.client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        self.logger = logging.getLogger(__name__)
        self.character_config = config.CHARACTER_CONFIG
        self.timezone = config.TIMEZONE

    def _build_system_prompt(self) -> str:
        """建立系統提示
        
        Returns:
            str: 系統提示
        """
        character = self.character_config["基本資料"]
        
        prompt = f"""你是一個 {character["年齡"]} 歲的{character["性別"]}，來自{character["國籍"]}。

興趣包括：{', '.join(character["興趣"])}

個性特徵：
{chr(10).join('- ' + trait for trait in character["個性特徵"])}

回覆規則：
- 字數限制：{self.character_config["回文規則"]["字數限制"]}
- 使用口語化的表達方式
- 保持輕鬆愉快的語氣
- 偶爾使用表情符號
- 根據對話歷史調整回應風格

請根據以上設定進行對話，確保回應符合角色設定和規則。"""

        return prompt

    async def generate_post(self) -> str:
        """生成新貼文
        
        Returns:
            str: 生成的貼文內容
        """
        try:
            # 取得當前時間
            current_time = datetime.now(self.timezone)
            hour = current_time.hour
            
            # 根據時間選擇主題
            if 5 <= hour < 11:
                topics = ["早安", "今天的計畫", "早餐", "通勤", "天氣"]
                mood = "精神飽滿"
            elif 11 <= hour < 14:
                topics = ["午餐", "工作", "休息", "心情"]
                mood = "放鬆愜意"
            elif 14 <= hour < 18:
                topics = ["下午茶", "工作", "休閒", "動漫", "遊戲"]
                mood = "專注投入"
            elif 18 <= hour < 22:
                topics = ["晚餐", "娛樂", "追劇", "放鬆", "心情"]
                mood = "放鬆愉快"
            else:
                topics = ["夜生活", "心情", "娛樂", "動漫", "遊戲"]
                mood = "慵懶放鬆"
                
            selected_topic = random.choice(topics)
            
            # 建立對話訊息
            messages = [
                {
                    "role": "system",
                    "content": f"""你是一個 {self.character_config['基本資料']['年齡']} 歲的{self.character_config['基本資料']['性別']}。
現在的心情是{mood}，請用自然的口吻分享一下關於「{selected_topic}」的想法或感受。

重要規則：
1. 絕對不要使用任何標籤（hashtag）
2. 不要用 @ 提及任何人
3. 使用口語化的表達方式，就像在跟朋友聊天
4. 可以使用 1-2 個表情符號，但不要過度
5. 字數限制在 20 字以內
6. 內容要反映出你的個性：{', '.join(self.character_config['基本資料']['個性特徵'])}
7. 要自然地融入你的興趣：{', '.join(self.character_config['基本資料']['興趣'])}

範例：
❌ "追新番中！#動漫迷 #宅女日常"
✅ "這季新番也太好看了吧，根本停不下來 😳"
❌ "@閨蜜 今天要一起打電動嗎？"
✅ "晚上要跟閨蜜開黑，期待 ✨"
"""
                },
                {
                    "role": "user",
                    "content": f"現在是 {current_time.strftime('%H:%M')}，請發表一則貼文。記住：不要使用 hashtag 和 @ 符號！"
                }
            ]
            
            # 呼叫 OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.9,  # 提高創意度
                max_tokens=50,
                top_p=1,
                frequency_penalty=0.5,  # 增加用詞變化
                presence_penalty=0.5    # 增加主題變化
            )
            
            # 取得回應文字
            post = response.choices[0].message.content.strip()
            
            # 確保貼文不超過 25 字且不含 hashtag
            if '#' in post:
                post = post[:post.find('#')].strip()
                
            # 如果超過25字，嘗試找到最後一個完整句子的結尾
            if len(post) > 25:
                # 尋找最後一個句號、感嘆號或問號的位置
                last_period = post[:25].rfind('。')
                last_exclaim = post[:25].rfind('！')
                last_question = post[:25].rfind('？')
                last_wave = post[:25].rfind('～')
                
                # 找出最後一個標點符號的位置
                end_pos = max(last_period, last_exclaim, last_question, last_wave)
                
                if end_pos > 0:
                    # 如果找到標點符號，截取到該位置
                    post = post[:end_pos + 1]
                else:
                    # 如果沒有找到標點符號，截取到25字並加上結尾
                    post = post[:25] + '～'
            elif not any(post.endswith(p) for p in ['。', '！', '？', '～']):
                # 如果文章沒有以標點符號結尾，加上波浪號
                post = post + '～'
                
            return post
            
        except Exception as e:
            self.logger.error(f"生成貼文時發生錯誤: {str(e)}")
            return None