"""
ThreadsPoster API 處理模組
處理與 Threads API 的所有互動
"""

import logging
import aiohttp
from datetime import datetime
import asyncio
from typing import Optional

class ThreadsAPI:
    """Threads API 客戶端"""
    
    def __init__(self, config):
        """初始化 Threads API 客戶端"""
        self.config = config
        self.access_token = config.API_CONFIG["access_token"]
        self.base_url = "https://graph.threads.net/v1.0"
        self.user_id = config.API_CONFIG["user_id"]
        self.logger = logging.getLogger(__name__)
        
        # API 設定
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # API 限制
        self.LIMITS = {
            "text": {
                "max_length": 500
            }
        }
        
        # 建立 aiohttp session
        self._session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """獲取或建立 aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def create_media_container(self, text: str) -> Optional[str]:
        """建立媒體容器

        Args:
            text (str): 貼文內容

        Returns:
            Optional[str]: 媒體容器 ID
        """
        try:
            url = f"{self.base_url}/{self.user_id}/threads"
            params = {
                "media_type": "TEXT",
                "text": text,
                "access_token": self.access_token
            }
            
            self.logger.info(f"正在建立媒體容器，URL: {url}")
            self.logger.info(f"參數: {params}")
            
            session = await self._get_session()
            async with session.post(url, params=params) as response:
                response_text = await response.text()
                self.logger.info(f"API 回應: {response.status} - {response_text}")
                
                if response.status != 200:
                    self.logger.error(f"建立媒體容器失敗: {response.status}, {response_text}")
                    return None
                    
                data = await response.json()
                container_id = data.get("id")
                self.logger.info(f"成功建立媒體容器，ID: {container_id}")
                return container_id

        except Exception as e:
            self.logger.error(f"建立媒體容器時發生錯誤: {str(e)}", exc_info=True)
            return None

    async def publish_container(self, container_id: str) -> Optional[str]:
        """發布媒體容器

        Args:
            container_id (str): 媒體容器 ID

        Returns:
            Optional[str]: 貼文 ID
        """
        try:
            # 等待 5 秒讓伺服器處理
            self.logger.info(f"等待 5 秒讓伺服器處理媒體容器 {container_id}")
            await asyncio.sleep(5)
            
            url = f"{self.base_url}/{self.user_id}/threads_publish"
            params = {
                "creation_id": container_id,
                "access_token": self.access_token
            }
            
            self.logger.info(f"正在發布媒體容器，URL: {url}")
            self.logger.info(f"參數: {params}")
            
            session = await self._get_session()
            async with session.post(url, params=params) as response:
                response_text = await response.text()
                self.logger.info(f"API 回應: {response.status} - {response_text}")
                
                if response.status != 200:
                    self.logger.error(f"發布媒體容器失敗: {response.status}, {response_text}")
                    return None
                    
                data = await response.json()
                post_id = data.get("id")
                self.logger.info(f"成功發布媒體容器，貼文 ID: {post_id}")
                return post_id

        except Exception as e:
            self.logger.error(f"發布媒體容器時發生錯誤: {str(e)}", exc_info=True)
            return None

    async def create_post(self, text: str) -> Optional[str]:
        """建立新的貼文

        Args:
            text (str): 貼文內容

        Returns:
            Optional[str]: 貼文 ID，如果建立失敗則返回 None
        """
        try:
            # 檢查文字長度
            if len(text) > 500:
                self.logger.error("貼文內容超過 500 字元限制")
                return None

            # 步驟 1: 建立媒體容器
            container_id = await self.create_media_container(text)
            if not container_id:
                return None

            # 步驟 2: 發布媒體容器
            return await self.publish_container(container_id)

        except Exception as e:
            self.logger.error(f"建立貼文時發生錯誤: {str(e)}")
            return None