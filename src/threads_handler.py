"""
Version: 2024.03.30
Author: ThreadsPoster Team
Description: Threads 處理器，負責管理 Threads 平台操作的高層邏輯
Last Modified: 2024.03.30
Changes:
- 優化發文邏輯
- 改進錯誤處理
- 加強回應處理機制
"""

import logging
import aiohttp
from typing import Optional, Dict, Any
from src.config import Config

logger = logging.getLogger(__name__)

class ThreadsHandler:
    def __init__(self, config: Config):
        """初始化 Threads API 處理器"""
        self.config = config
        self.session = None
        self.headers = {
            "Authorization": f"Bearer {self.config.THREADS_ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def initialize(self):
        """初始化 HTTP 會話"""
        self.session = aiohttp.ClientSession(headers=self.headers)
        logger.info("Threads API 會話已初始化")

    async def close(self):
        """關閉 HTTP 會話"""
        if self.session:
            await self.session.close()
            logger.info("Threads API 會話已關閉")

    async def create_post(self, content: str) -> Optional[str]:
        """建立新貼文
        
        根據 Threads API 文件，發文是兩步驟過程：
        1. 建立媒體容器
        2. 發布容器
        """
        try:
            if not self.session:
                await self.initialize()

            # 步驟 1: 建立媒體容器
            container_url = f"{self.config.API_BASE_URL}/{self.config.THREADS_USER_ID}/threads"
            container_data = {
                "text": content,
                "media_type": "TEXT"
            }

            async with self.session.post(container_url, json=container_data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"建立媒體容器失敗: {response.status} - {error_text}")
                    return None
                    
                container_result = await response.json()
                container_id = container_result.get("id")
                
                if not container_id:
                    logger.error("無法獲取媒體容器 ID")
                    return None

                # 步驟 2: 發布容器
                publish_url = f"{self.config.API_BASE_URL}/{self.config.THREADS_USER_ID}/threads_publish"
                publish_data = {
                    "creation_id": container_id
                }

                async with self.session.post(publish_url, json=publish_data) as publish_response:
                    if publish_response.status == 200:
                        result = await publish_response.json()
                        post_id = result.get("id")
                        logger.info(f"貼文發布成功: {post_id}")
                        return post_id
                    else:
                        error_text = await publish_response.text()
                        logger.error(f"發布貼文失敗: {publish_response.status} - {error_text}")
                        return None

        except Exception as e:
            logger.error(f"建立貼文過程中發生錯誤: {e}")
            return None

    async def get_post(self, post_id: str) -> Optional[Dict[str, Any]]:
        """獲取貼文資訊"""
        try:
            if not self.session:
                await self.initialize()

            url = f"{self.config.API_BASE_URL}/{post_id}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    post_data = await response.json()
                    return post_data
                else:
                    error_text = await response.text()
                    logger.error(f"獲取貼文失敗: {response.status} - {error_text}")
                    return None
        except Exception as e:
            logger.error(f"獲取貼文過程中發生錯誤: {e}")
            return None

    async def delete_post(self, post_id: str) -> bool:
        """刪除貼文"""
        try:
            if not self.session:
                await self.initialize()

            url = f"{self.config.API_BASE_URL}/{post_id}"
            async with self.session.delete(url) as response:
                if response.status == 200:
                    logger.info(f"貼文刪除成功: {post_id}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"貼文刪除失敗: {response.status} - {error_text}")
                    return False
        except Exception as e:
            logger.error(f"刪除貼文過程中發生錯誤: {e}")
            return False 