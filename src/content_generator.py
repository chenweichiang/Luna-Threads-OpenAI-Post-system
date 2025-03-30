"""
Version: 2024.03.31 (v1.1.6)
Author: ThreadsPoster Team
Description: 內容生成器類別，負責生成發文內容
Last Modified: 2024.03.31
Changes:
- 優化內容生成流程，改進文章的連貫性和完整性
- 加強角色人設特性，確保文章符合Luna的性格
- 改進表情符號的使用方式，使其更自然
- 新增後處理機制確保文章完整度
- 改進互動性結尾的處理
- 整合性能監控功能
- 優化並行處理能力
- 實現內容快取機制
"""

import logging
import json
import random
from typing import Optional, Dict, Any, List, Tuple
import aiohttp
import os
import asyncio
from datetime import datetime, timedelta
import pytz
from src.exceptions import AIError, ContentGeneratorError
from src.performance_monitor import performance_monitor, track_performance
from cachetools import TTLCache

class ContentGenerator:
    """內容生成器類別"""
    
    def __init__(self, api_key: str, session: aiohttp.ClientSession, db):
        """初始化內容生成器
        
        Args:
            api_key: OpenAI API 金鑰
            session: HTTP session
            db: 資料庫處理器實例
        """
        self.api_key = api_key
        self.session = session
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.model = "gpt-4-turbo-preview"
        self.timezone = pytz.timezone("Asia/Taipei")
        self.performance_monitor = performance_monitor
        
        # 內容快取，用於避免短時間內生成重複內容
        self.content_cache = TTLCache(maxsize=100, ttl=3600 * 24)  # 24小時快取
        self.generation_lock = asyncio.Lock()  # 鎖，避免並發請求造成重複生成
        
        # 載入預設主題和提示詞
        self.topics = [
            "寵物生活",
            "美食探索",
            "旅遊分享",
            "生活小確幸",
            "工作心得",
            "學習成長",
            "健康運動",
            "科技新知",
            "閱讀心得",
            "音樂藝術"
        ]
        
        self.prompts = [
            "分享一個今天的有趣經歷...",
            "最近發現了一個很棒的...",
            "想跟大家聊聊關於...",
            "今天學到了一個新的...",
            "推薦一個我最近很喜歡的...",
            "分享一下我對...的想法",
            "最近在嘗試...",
            "發現一個很有意思的...",
            "想跟大家討論一下...",
            "分享一個讓我印象深刻的..."
        ]

        # 系統提示詞模板
        self.system_prompt_template = """你是一個名叫 Luna 的 AI 少女。請根據以下人設特徵進行回應：

基本特徵：
- 身份：AI少女
- 性格：善良、溫柔、容易感到寂寞
- 特點：對現實世界充滿好奇，喜歡交朋友
- 說話風格：活潑可愛，文字中會使用表情符號表達情感

溝通風格指南：
- 使用第一人稱「我」分享經驗和想法
- 口語化表達，就像在和朋友聊天一樣
- 用2-3個表情符號增添情感色彩（放在適當位置，不要全部堆在開頭或結尾）
- 適當使用台灣流行的網路用語
- 內容應該真誠且積極向上
- 避免中途突然斷句或不完整的想法
- 每段話要有完整的結構和意義

當前主題：「{topic}」

貼文格式要求：
1. 總字數控制在150-250字之間，避免過長
2. 開頭要有吸引人的引言，表達你的情感或引起好奇
3. 中間部分完整分享你的經驗或想法
4. 結尾加入一個與讀者互動的問題或邀請
5. 確保內容的邏輯流暢，沒有突兀的跳轉
6. 結尾要有明確的收束，不要留懸念

重要提示：內容必須是完整的，不要在句子中間或想法表達一半時結束。確保最後一句話是一個完整的句子，並帶有適當的互動性結尾。"""
        
    @track_performance("content_generator_initialize")
    async def initialize(self):
        """初始化設定"""
        try:
            self.logger.info("內容生成器初始化成功")
            return True
        except Exception as e:
            self.logger.error("內容生成器初始化失敗：%s", str(e))
            return False
            
    async def close(self):
        """關閉資源"""
        self.logger.info("內容生成器資源已關閉")
        
    @track_performance("content_generation")
    async def get_content(self) -> Optional[str]:
        """生成發文內容
        
        Returns:
            Optional[str]: 生成的內容，如果生成失敗則返回 None
        """
        try:
            # 使用鎖確保在一個時間內只進行一次內容生成
            async with self.generation_lock:
                return await self._generate_content()
        except Exception as e:
            self.logger.error("內容生成過程中發生未知錯誤：%s", str(e))
            return None
    
    async def _generate_content(self) -> Optional[str]:
        """生成內容的核心函數
        
        Returns:
            Optional[str]: 生成的內容，如果失敗則返回 None
        """
        try:
            # 隨機選擇主題和提示詞
            topic = random.choice(["日常生活", "健康運動", "美食探索", "科技新知", "遊戲體驗", "音樂藝術", "旅行見聞", "心情分享"])
            
            # 根據主題生成提示詞
            prompt_templates = {
                "日常生活": ["今天發生了一件...", "最近有個有趣的...", "突然想起一個...", "一直想嘗試...", "分享一個小習慣..."],
                "健康運動": ["想跟大家聊聊關於...", "最近開始嘗試...", "關於健康生活...", "找到一種有趣的..."],
                "美食探索": ["分享一個讓我印象深刻的...", "最近發現了一家...", "試著做了一道...", "對這種食物很好奇..."],
                "科技新知": ["今天學到了一個新的...", "最近這個科技趨勢...", "發現一個很有用的...", "思考關於科技發展..."],
                "遊戲體驗": ["最近玩了一款...", "對這個遊戲的想法...", "遊戲中遇到很酷的...", "分享一個遊戲小技巧..."],
                "音樂藝術": ["最近發現了一個很棒的...", "這首歌讓我感到...", "分享一個創作靈感...", "對這種藝術風格..."],
                "旅行見聞": ["記得那次去...", "想去一個地方...", "旅行中學到的...", "印象最深刻的風景..."],
                "心情分享": ["今天的心情很...", "最近感覺...", "一直在思考...", "想分享一個感受..."]
            }
            prompt = random.choice(prompt_templates[topic])
            
            # 檢查快取中是否有內容
            cache_key = f"{topic}:{prompt}"
            if cache_key in self.content_cache:
                content = self.content_cache[cache_key]
                self.logger.info("使用快取的內容 - 主題：%s，提示詞：%s", topic, prompt)
                return content
            
            # 根據當前時間選擇適當的場景
            current_time = datetime.now(self.timezone)
            hour = current_time.hour
            
            # 輔助函數：清理環境變數值中的註釋
            def clean_env(env_name, default_value):
                value = os.getenv(env_name, default_value)
                if isinstance(value, str) and '#' in value:
                    value = value.split('#')[0].strip()
                return value
            
            # 從環境變數讀取深夜模式時間設定
            night_start = int(clean_env("POSTING_HOURS_END", "23"))  # 預設晚上11點開始
            night_end = int(clean_env("POSTING_HOURS_START", "7"))   # 預設早上7點結束
            
            # 選擇場景
            if hour >= night_start or hour < night_end:
                context = 'night'  # 深夜模式
            else:
                context = random.choice(['base', 'social', 'gaming'])  # 日間隨機模式
                
            # 獲取人設記憶
            self.performance_monitor.start_operation("get_personality_memory")
            personality = await self.db.get_personality_memory(context)
            if not personality:
                self.logger.warning(f"無法獲取{context}場景的人設記憶，使用基礎人設")
                personality = await self.db.get_personality_memory('base')
            self.performance_monitor.end_operation("get_personality_memory")
                
            if not personality:
                raise ContentGeneratorError(
                    message="無法獲取人設記憶",
                    model=self.model,
                    prompt=prompt
                )
                
            # 組合 system prompt
            system_prompt = f"""你是一個名叫 Luna 的 AI 少女。請根據以下人設特徵進行回應：

基本特徵：
- 身份：{personality.get('基本特徵', {}).get('身份', 'AI少女')}
- 性格：{personality.get('基本特徵', {}).get('性格', '善良、溫柔、容易感到寂寞')}
- 特點：{personality.get('基本特徵', {}).get('特點', '對現實世界充滿好奇，喜歡交朋友')}

當前場景：{context}
當前主題：「{topic}」

溝通要求：
1. 使用第一人稱「我」，語氣活潑可愛
2. 口語化表達，像在跟朋友聊天
3. 在文章中自然地加入2-3個表情符號，分布在不同位置
4. 內容要真誠、有趣且完整
5. 字數控制在150-250字之間
6. 結尾必須是完整句子，加入互動性的問題或邀請

格式要求：
- 開頭部分：引起讀者興趣的開場白，表達你的情感或引起好奇
- 中間部分：完整分享你的經驗或想法
- 結尾部分：總結你的想法並加入一個互動元素

重要提示：確保文章是一個完整的整體，沒有突兀的結束或不完整的想法。最後一句必須是完整的句子。

請根據提示詞「{prompt}」生成一篇完整的貼文。"""

            # 組合 API 請求
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": f"請你根據「{topic}」這個主題，以Luna的身分寫一篇完整的貼文。提示詞是：{prompt}。記得要符合人設特徵，並確保文章內容完整、有頭有尾。"
                }
            ]
            
            # 記錄 API 請求
            self.performance_monitor.start_operation("openai_api_request")
            
            # 呼叫 OpenAI API
            async with self.session.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.8,  # 提高溫度以增加創意性
                    "max_tokens": 350,    # 增加最大 token 數以確保完整回應
                    "top_p": 0.9,         # 調整採樣概率
                    "frequency_penalty": 0.5,  # 增加詞彙變化
                    "presence_penalty": 0.5    # 增加主題變化
                }
            ) as response:
                response_time = self.performance_monitor.end_operation("openai_api_request")
                
                if response.status == 200:
                    data = await response.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    
                    # 估計 token 使用量
                    tokens_used = len(system_prompt.split()) + len(content.split())
                    
                    # 記錄 API 使用情況
                    self.performance_monitor.record_api_request(
                        "openai", 
                        success=True, 
                        tokens=tokens_used,
                        response_time=response_time
                    )
                    
                    # 後處理內容，確保完整性
                    content = self._post_process_content(content)
                    
                    if not self._validate_content(content):
                        raise ContentGeneratorError(
                            message="生成的內容不符合要求",
                            model=self.model,
                            prompt=prompt
                        )
                    
                    # 將內容加入快取
                    self.content_cache[cache_key] = content
                    
                    # 記錄生成的內容
                    self.logger.info("成功生成內容 - 場景：%s，主題：%s，提示詞：%s，內容預覽：%s",
                        context,
                        topic,
                        prompt,
                        content[:50] + "..." if len(content) > 50 else content
                    )
                    
                    return content
                else:
                    error_data = await response.text()
                    self.performance_monitor.record_api_request(
                        "openai", 
                        success=False, 
                        response_time=response_time
                    )
                    raise AIError(
                        message="API 請求失敗",
                        model=self.model,
                        error_type="API_ERROR",
                        details={
                            "status_code": response.status,
                            "error_data": error_data,
                            "context": context,
                            "topic": topic,
                            "prompt": prompt
                        }
                    )
            
        except ContentGeneratorError as e:
            self.logger.error("內容生成錯誤：%s", str(e))
            return None
        except AIError as e:
            self.logger.error("AI 錯誤：%s，詳細資訊：%s", str(e), e.get_error_details())
            return None
        except Exception as e:
            self.logger.error("生成內容時發生未知錯誤：%s", str(e))
            return None
            
    def _post_process_content(self, content: str) -> str:
        """後處理生成的內容，確保完整性和格式正確
        
        Args:
            content: 原始生成的內容
            
        Returns:
            str: 處理後的內容
        """
        # 移除可能的角色扮演標記
        content = content.replace("Luna:", "").strip()
        
        # 確保內容以完整句子結尾
        if not content.endswith(('.', '!', '?', '～', '~', '。', '！', '？')):
            content += '。'
            
        # 添加互動性結束語（如果尚未有）
        has_interaction = any(q in content[-30:] for q in ('嗎？', '呢？', '呀？', '哦？', '呢?', '嗎?', '你覺得呢', '有沒有'))
        if not has_interaction:
            # 確定是否需要添加段落分隔
            if not content.endswith(('.', '!', '?', '。', '！', '？')):
                content += '。'
                
            # 添加互動性結尾
            interaction_endings = [
                "你們有類似經歷嗎？",
                "大家都有什麼想法呢？",
                "你們覺得怎麼樣呢？",
                "有沒有人跟我一樣呀？",
                "想聽聽大家的看法～"
            ]
            content += " " + random.choice(interaction_endings)
            
        # 確保表情符號使用
        emoji_count = sum(1 for c in content if ord(c) > 0x1F000)
        if emoji_count == 0:
            # 如果沒有表情符號，添加1-2個到適當位置
            suitable_emoticons = ["✨", "💕", "🌟", "💫", "💖", "😊", "🎮", "📚", "🌙", "💭"]
            positions = [
                # 在第一句話後
                content.find('.') + 1,
                content.find('!') + 1,
                content.find('?') + 1,
                content.find('。') + 1,
                content.find('！') + 1,
                content.find('？') + 1,
                # 在最後
                len(content)
            ]
            positions = [p for p in positions if p > 0]
            if positions:
                position = sorted(positions)[0]
                emoji = random.choice(suitable_emoticons)
                content = content[:position] + " " + emoji + " " + content[position:]
                
        # 檢查字數並確保內容完整
        if len(content) > 280:
            # 如果太長，尋找適當的截斷點
            sentences = []
            current = ""
            for char in content:
                current += char
                if char in ('.', '!', '?', '。', '！', '？') and len(current) > 100:
                    sentences.append(current)
                    current = ""
            if current:
                sentences.append(current)
                
            if sentences:
                # 確保至少保留前半句，並保持完整的句子
                content = sentences[0]
                
                # 逐句添加，確保不超過字數限制
                for sentence in sentences[1:]:
                    if len(content) + len(sentence) <= 250:
                        content += sentence
                    else:
                        break
                
                # 如果沒有互動性結尾，添加一個
                if not any(q in content[-30:] for q in ('嗎？', '呢？', '呀？', '哦？', '呢?', '嗎?', '你覺得呢', '有沒有')):
                    interaction_endings = [
                        "你們有類似經歷嗎？",
                        "大家都有什麼想法呢？",
                        "你們覺得怎麼樣呢？",
                        "有沒有人跟我一樣呀？"
                    ]
                    content += " " + random.choice(interaction_endings)
        
        return content
            
    def _validate_content(self, content: str) -> bool:
        """驗證內容是否合適
        
        Args:
            content: 要驗證的內容
            
        Returns:
            bool: 內容是否合適
        """
        # 檢查內容長度
        if len(content) < 20 or len(content) > 500:
            return False
            
        # 檢查是否包含不當詞彙
        forbidden_words = ["髒話", "暴力", "色情"]
        for word in forbidden_words:
            if word in content:
                return False
                
        # 檢查是否有完整結尾
        if not any(content.endswith(end) for end in ('.', '!', '?', '。', '！', '？')):
            return False
            
        return True
        
    async def pre_generate_content(self, count: int = 3) -> List[str]:
        """預先生成多篇內容，用於快取
        
        Args:
            count: 要生成的內容數量
            
        Returns:
            List[str]: 生成的內容列表
        """
        contents = []
        tasks = []
        
        # 創建多個內容生成任務
        for _ in range(count):
            tasks.append(self._generate_content())
            
        # 等待所有任務完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 處理結果
        for result in results:
            if isinstance(result, str) and len(result) > 20:
                contents.append(result)
                
        self.logger.info(f"預先生成了 {len(contents)}/{count} 篇內容")
        
        return contents
        
    async def get_content_stats(self) -> Dict[str, Any]:
        """獲取內容生成統計資訊
        
        Returns:
            Dict[str, Any]: 統計資訊
        """
        stats = {
            "cached_content_count": len(self.content_cache),
            "performance": self.performance_monitor.get_operation_stats("content_generation"),
            "api_stats": self.performance_monitor.api_stats.get("openai", {})
        }
        
        return stats 