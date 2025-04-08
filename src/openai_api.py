"""
Version: 2024.03.31 (v1.1.6)
Author: ThreadsPoster Team
Description: OpenAI API 介面，處理與 OpenAI 服務的所有互動
Last Modified: 2024.03.31
Changes:
- 升級至最新的 OpenAI API
- 優化提示詞處理
- 加強錯誤處理機制
- 支援接受外部 session
- 整合性能監控
"""

import logging
import asyncio
from typing import Optional, Dict, List
import aiohttp
from datetime import datetime
import pytz
from functools import lru_cache
import backoff
from aiohttp import ClientTimeout
from asyncio import Semaphore
from performance_monitor import performance_monitor, track_performance

logger = logging.getLogger(__name__)

class OpenAIAPI:
    """OpenAI API 處理類"""
    
    def __init__(self, api_key: str, session: Optional[aiohttp.ClientSession] = None):
        """初始化 OpenAI API 客戶端
        
        Args:
            api_key: OpenAI API 金鑰
            session: 可選的 HTTP session，如果提供則使用此 session
        """
        self.api_key = api_key
        self.model = "gpt-4-turbo-preview"  # 預設模型
        self.timezone = pytz.timezone("Asia/Taipei")
        self.performance_monitor = performance_monitor
        
        # 設置 API 請求的基本配置
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 使用提供的 session 或建立新的
        self.session = session
        self.own_session = session is None  # 標記是否為自己建立的 session
        
        # 並發控制
        self.semaphore = Semaphore(5)  # 限制最大並發請求數
        
        # 請求超時設置
        self.timeout = ClientTimeout(
            total=30,
            connect=10,
            sock_read=20
        )
        
    async def ensure_session(self):
        """確保 session 存在"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=self.timeout,
                connector=aiohttp.TCPConnector(
                    limit=10,
                    ttl_dns_cache=300,
                    use_dns_cache=True
                )
            )
            self.own_session = True

    @lru_cache(maxsize=24)
    def _get_base_prompt(self, current_hour: int) -> str:
        """獲取基本提示詞（使用快取）"""
        # 定義基於時間的心情模式
        mood_patterns = {
            "morning": {
                "mood": "精神飽滿",
                "topics": ["早安", "今天的計畫"],
                "style": "活力充沛"
            },
            "noon": {
                "mood": "悠閒放鬆",
                "topics": ["午餐", "休息", "工作"],
                "style": "輕鬆愉快"
            },
            "afternoon": {
                "mood": "專注認真",
                "topics": ["工作", "興趣", "學習"],
                "style": "認真思考"
            },
            "evening": {
                "mood": "放鬆愉快",
                "topics": ["晚餐", "娛樂", "心情"],
                "style": "溫柔體貼"
            },
            "night": {
                "mood": "安靜思考",
                "topics": ["星空", "音樂", "夢想"],
                "style": "溫柔安靜"
            }
        }
        
        # 確定當前時間段
        if 5 <= current_hour < 11:
            time_period = "morning"
        elif 11 <= current_hour < 14:
            time_period = "noon"
        elif 14 <= current_hour < 18:
            time_period = "afternoon"
        elif 18 <= current_hour < 22:
            time_period = "evening"
        else:
            time_period = "night"
            
        mood_pattern = mood_patterns[time_period]
        
        # 定義基本資料
        character_data = {
            "年齡": 20,
            "性別": "女性",
            "國籍": "台灣",
            "興趣": ["遊戲", "動漫", "收藏公仔"],
            "個性特徵": [
                "善良溫柔",
                "容易感到寂寞",
                "喜歡交朋友"
            ]
        }
        
        return f"""你是一個 {character_data['年齡']} 歲的{character_data['國籍']}{character_data['性別']}。
當前心情：{mood_pattern['mood']}
說話風格：{mood_pattern['style']}
興趣：{', '.join(character_data['興趣'])}
個性特徵：{', '.join(character_data['個性特徵'])}"""
    
    @track_performance("openai_api_request")
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=30
    )
    async def _make_api_request(self, messages: List[Dict], temperature: float = 0.7) -> str:
        """發送 API 請求（包含重試機制）"""
        async with self.semaphore:  # 控制並發
            try:
                self.performance_monitor.start_operation("openai_api_call")
                
                await self.ensure_session()
                
                async with self.session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=self.headers,
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": 50,
                        "temperature": temperature,
                        "presence_penalty": 0.6,
                        "frequency_penalty": 0.5
                    }
                ) as response:
                    call_time = self.performance_monitor.end_operation("openai_api_call")
                    
                    if response.status == 200:
                        data = await response.json()
                        content = data['choices'][0]['message']['content'].strip()
                        
                        # 估計 token 使用量
                        total_tokens = sum(len(m["content"].split()) for m in messages) + len(content.split())
                        
                        # 記錄 API 使用情況
                        self.performance_monitor.record_api_request(
                            "openai", 
                            success=True, 
                            tokens=total_tokens,
                            response_time=call_time
                        )
                        
                        return content
                    elif response.status == 429:  # Rate limit
                        retry_after = int(response.headers.get('Retry-After', 5))
                        logger.warning(f"達到 API 限制，等待 {retry_after} 秒後重試")
                        
                        self.performance_monitor.record_api_request(
                            "openai", 
                            success=False,
                            response_time=call_time
                        )
                        
                        await asyncio.sleep(retry_after)
                        raise aiohttp.ClientError("Rate limit exceeded")
                    else:
                        error_data = await response.text()
                        logger.error(f"OpenAI API 錯誤 {response.status}: {error_data}")
                        
                        self.performance_monitor.record_api_request(
                            "openai", 
                            success=False,
                            response_time=call_time
                        )
                        
                        raise Exception(f"OpenAI API 錯誤: {response.status}")
                        
            except asyncio.TimeoutError:
                logger.error("API 請求超時")
                self.performance_monitor.record_api_request("openai", success=False)
                raise
            except aiohttp.ClientError as e:
                logger.error(f"API 請求失敗: {str(e)}")
                self.performance_monitor.record_api_request("openai", success=False)
                raise
            except Exception as e:
                logger.error(f"未預期的錯誤: {str(e)}")
                self.performance_monitor.record_api_request("openai", success=False)
                raise
    
    @track_performance("generate_post")
    async def generate_post(self) -> str:
        """生成貼文內容"""
        try:
            current_hour = datetime.now(self.timezone).hour
            base_prompt = self._get_base_prompt(current_hour)
            
            messages = [
                {"role": "system", "content": base_prompt},
                {"role": "user", "content": "請根據當前的心情和興趣生成一則不超過20字的貼文。"}
            ]
            
            return await self._make_api_request(messages, temperature=0.7)
                    
        except Exception as e:
            logger.error(f"生成貼文內容時發生錯誤: {str(e)}")
            raise
    
    @track_performance("generate_reply")
    async def generate_reply(self, user_message: str, username: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """生成回覆內容"""
        try:
            current_hour = datetime.now(self.timezone).hour
            base_prompt = self._get_base_prompt(current_hour)
            
            # 建立對話歷史
            messages = [{"role": "system", "content": base_prompt}]
            
            if conversation_history:
                for conv in conversation_history[-3:]:  # 只使用最近3條對話
                    messages.extend([
                        {"role": "user", "content": conv["message"]},
                        {"role": "assistant", "content": conv["response"]}
                    ])
            
            messages.append({"role": "user", "content": user_message})
            
            return await self._make_api_request(messages, temperature=0.8)
                    
        except Exception as e:
            logger.error(f"生成回覆內容時發生錯誤: {str(e)}")
            raise
            
    async def close(self):
        """關閉 session"""
        if self.own_session and self.session and not self.session.closed:
            await self.session.close() 