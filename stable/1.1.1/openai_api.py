"""
OpenAI API 處理模組
處理與 OpenAI API 的所有互動
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

logger = logging.getLogger(__name__)

class OpenAIAPI:
    """OpenAI API 處理類"""
    
    def __init__(self, config):
        """初始化 OpenAI API 客戶端
        
        Args:
            config: 設定物件
        """
        self.config = config
        self.api_key = config.OPENAI_API_KEY
        self.model = config.OPENAI_MODEL
        self.timezone = pytz.timezone("Asia/Taipei")
        
        # 設置 API 請求的基本配置
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 建立共用的 session
        self.session = None
        
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
    
    @lru_cache(maxsize=24)
    def _get_base_prompt(self, current_hour: int) -> str:
        """獲取基本提示詞（使用快取）"""
        mood_pattern = self.config.get_mood_pattern(current_hour)
        character_config = self.config.CHARACTER_CONFIG
        
        return f"""你是一個 {character_config['基本資料']['年齡']} 歲的{character_config['基本資料']['國籍']}{character_config['基本資料']['性別']}。
當前心情：{mood_pattern['mood']}
說話風格：{mood_pattern['style']}
興趣：{', '.join(character_config['基本資料']['興趣'])}
個性特徵：{', '.join(character_config['基本資料']['個性特徵'])}"""
    
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
                await self.ensure_session()
                
                async with self.session.post(
                    "https://api.openai.com/v1/chat/completions",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": 50,
                        "temperature": temperature,
                        "presence_penalty": 0.6,
                        "frequency_penalty": 0.5
                    }
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['choices'][0]['message']['content'].strip()
                    elif response.status == 429:  # Rate limit
                        retry_after = int(response.headers.get('Retry-After', 5))
                        logger.warning(f"達到 API 限制，等待 {retry_after} 秒後重試")
                        await asyncio.sleep(retry_after)
                        raise aiohttp.ClientError("Rate limit exceeded")
                    else:
                        error_data = await response.text()
                        logger.error(f"OpenAI API 錯誤 {response.status}: {error_data}")
                        raise Exception(f"OpenAI API 錯誤: {response.status}")
                        
            except asyncio.TimeoutError:
                logger.error("API 請求超時")
                raise
            except aiohttp.ClientError as e:
                logger.error(f"API 請求失敗: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"未預期的錯誤: {str(e)}")
                raise
    
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
        if self.session and not self.session.closed:
            await self.session.close() 