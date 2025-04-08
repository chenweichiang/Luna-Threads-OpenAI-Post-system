"""
Version: 2025.03.31 (v1.1.9)
Author: ThreadsPoster Team
Description: 內容生成器類別，負責生成發文內容
Copyright (c) 2025 Chiang, Chenwei. All rights reserved.
License: MIT License
Last Modified: 2025.03.31
Changes:
- 優化內容生成流程，改進文章的連貫性和完整性
- 加強角色人設特性，確保文章符合Luna的性格
- 改進表情符號的使用方式，使其更自然
- 新增後處理機制確保文章完整度
- 改進互動性結尾的處理
- 整合性能監控功能
- 優化並行處理能力
- 實現內容快取機制
- 引入獨立的說話模式模組
"""

import logging
import json
import random
import re
from typing import Optional, Dict, Any, List, Tuple
import aiohttp
import os
import asyncio
from datetime import datetime, timedelta
import pytz
from exceptions import AIError, ContentGeneratorError
from performance_monitor import performance_monitor, track_performance
from speaking_patterns import SpeakingPatterns
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
        self.speaking_patterns = None  # 將在 main.py 中設置
        self.threads_handler = None  # 將在 main.py 中設置
        
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
            
            # 檢查快取中是否有內容
            cache_key = f"{topic}"
            if cache_key in self.content_cache:
                content = self.content_cache[cache_key]
                self.logger.info("使用快取的內容 - 主題：%s", topic)
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
                    prompt=""
                )
                
            # 從說話模式模組獲取系統提示詞
            system_prompt = self.speaking_patterns.get_system_prompt(context, topic)
            
            # 從說話模式模組獲取用戶提示詞
            user_prompt = self.speaking_patterns.get_user_prompt(topic)

            # 組合 API 請求
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
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
                    
                    # 獲取內容驗證標準
                    validation_criteria = self.speaking_patterns.get_content_validation_criteria()
                    if not self._validate_content(content, validation_criteria):
                        raise ContentGeneratorError(
                            message="生成的內容不符合要求",
                            model=self.model,
                            prompt=""
                        )
                    
                    # 將內容加入快取
                    self.content_cache[cache_key] = content
                    
                    # 記錄生成的內容
                    self.logger.info("成功生成內容 - 場景：%s，主題：%s，內容預覽：%s",
                        context,
                        topic,
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
                            "topic": topic
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
            
        # 檢查字數，如果太長則截斷
        text_without_emoji = ''.join(c for c in content if ord(c) < 0x1F000)
        if len(text_without_emoji) > 40:
            # 尋找適當的截斷點
            cutoff_indices = []
            for punct in ['。', '！', '？', '.', '!', '?']:
                idx = content.rfind(punct, 0, 40)
                if idx > 0:
                    cutoff_indices.append(idx + 1)
            
            if cutoff_indices:
                content = content[:max(cutoff_indices)]
            else:
                # 找不到適當的截斷點，硬截斷並添加句點
                words = content[:40]
                content = words + ('。' if not words.endswith(('.', '!', '?', '。', '！', '？')) else '')
                
        # 添加互動性結束語（如果尚未有）
        has_interaction = any(q in content[-15:] for q in ('嗎？', '呢？', '呀？', '哦？', '呢?', '嗎?', '你覺得呢', '有沒有'))
        if not has_interaction:
            # 確定是否需要添加段落分隔
            if not content.endswith(('.', '!', '?', '。', '！', '？')):
                content += '。'
                
            # 添加簡短互動性結尾
            interaction_endings = [
                "你呢？",
                "同意嗎？",
                "如何？",
                "對吧？",
                "是吧～"
            ]
            content += " " + random.choice(interaction_endings)
            
        # 確保表情符號使用
        emoji_count = sum(1 for c in content if ord(c) > 0x1F000)
        if emoji_count == 0:
            # 如果沒有表情符號，添加1個到適當位置
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
        
        # 再次檢查長度，確保不超過40字
        text_without_emoji = ''.join(c for c in content if ord(c) < 0x1F000)
        if len(text_without_emoji) > 40:
            # 如果互動性結尾導致超過字數限制，使用更簡短的結尾
            content = content.split()[0]  # 保留第一部分
            if not content.endswith(('.', '!', '?', '。', '！', '？')):
                content += '。'
            content += " 你呢？"
            
        return content
            
    def _validate_content(self, content: str, criteria: Dict[str, Any] = None) -> bool:
        """驗證生成的內容是否符合要求
        
        Args:
            content: 生成的內容
            criteria: 驗證標準
            
        Returns:
            bool: 是否符合要求
        """
        if criteria is None:
            criteria = {
                "min_length": 100,
                "max_length": 280,
                "min_emoticons": 1,
                "max_emoticons": 3,
                "required_ending_chars": ["！", "。", "？", "～", "!", "?", "~"],
                "incomplete_patterns": [
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
            }
        
        # 移除表情符號以檢查文本長度
        text_without_emoji = content
        for c in text_without_emoji:
            if ord(c) > 0x1F000:
                text_without_emoji = text_without_emoji.replace(c, '')
        
        # 檢查文本長度
        if len(text_without_emoji) < criteria["min_length"]:
            self.logger.warning(f"文本太短：{len(text_without_emoji)} 字符")
            return False
            
        if len(content) > criteria["max_length"]:
            self.logger.warning(f"文本太長：{len(content)} 字符")
            return False
            
        # 檢查表情符號數量
        emoji_count = sum(1 for c in content if ord(c) > 0x1F000)
        if emoji_count < criteria["min_emoticons"]:
            self.logger.warning(f"表情符號太少：{emoji_count}")
            return False
            
        if emoji_count > criteria["max_emoticons"]:
            self.logger.warning(f"表情符號太多：{emoji_count}")
            return False
            
        # 檢查結尾字符
        if not any(content.endswith(char) for char in criteria["required_ending_chars"]):
            self.logger.warning(f"缺少結尾標點：{content[-1]}")
            return False
            
        # 檢查不完整句子模式
        text_for_pattern = content.rstrip("！。？～!?~")
        for pattern in criteria["incomplete_patterns"]:
            if re.search(pattern, text_for_pattern):
                self.logger.warning(f"檢測到不完整句子模式：{pattern}")
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

    def set_threads_handler(self, threads_handler):
        """設置 Threads 處理器
        
        Args:
            threads_handler: Threads 處理器實例
        """
        self.threads_handler = threads_handler
        self.logger.info("已設置 Threads 處理器") 