"""
Version: 2024.03.30
Author: ThreadsPoster Team
Description: Threads API 類別，負責與 Threads 平台的直接互動
Last Modified: 2024.03.30
Changes:
- 改用官方 Threads Graph API
- 加強錯誤處理
- 優化連接管理
- 統一日誌路徑
"""

import logging
import aiohttp
import asyncio
from typing import Optional, Dict, Any
from src.exceptions import ThreadsAPIError

class ThreadsAPI:
    """Threads API 類別"""
    
    def __init__(self, access_token: str, user_id: str):
        """初始化 Threads API
        
        Args:
            access_token: Threads API access token
            user_id: Threads 用戶 ID
        """
        self.access_token = access_token
        self.user_id = user_id
        self.session = None
        self.logger = logging.getLogger(__name__)
        self.api_version = "v1.0"
        self.base_url = f"https://graph.threads.net/{self.api_version}"
        
    async def initialize(self) -> bool:
        """初始化 API 連接
        
        Returns:
            bool: 是否初始化成功
        """
        try:
            self.session = aiohttp.ClientSession()
            self.logger.info("API 連接已初始化")
            return True
        except Exception as e:
            self.logger.error(f"API 初始化失敗：{str(e)}")
            return False
            
    async def close(self):
        """關閉 API 連接"""
        if self.session:
            await self.session.close()
            self.logger.info("API 連接已關閉")
            
    async def create_media_container(self, content: str) -> Optional[str]:
        """建立媒體容器
        
        Args:
            content: 貼文內容
            
        Returns:
            Optional[str]: 媒體容器 ID，如果建立失敗則返回 None
        """
        try:
            url = f"{self.base_url}/{self.user_id}/threads"
            params = {
                "media_type": "TEXT",
                "text": content,
                "access_token": self.access_token
            }
            
            async with self.session.post(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    container_id = data.get("id")
                    if container_id:
                        self.logger.info(f"媒體容器建立成功：{container_id}")
                        return container_id
                    else:
                        self.logger.error("無法獲取媒體容器 ID")
                        return None
                else:
                    error_text = await response.text()
                    self.logger.error(f"媒體容器建立失敗：{response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"建立媒體容器時發生錯誤：{str(e)}")
            return None
            
    async def publish_container(self, container_id: str) -> Optional[str]:
        """發布媒體容器
        
        Args:
            container_id: 媒體容器 ID
            
        Returns:
            Optional[str]: 貼文 ID，如果發布失敗則返回 None
        """
        try:
            url = f"{self.base_url}/{self.user_id}/threads_publish"
            params = {
                "creation_id": container_id,
                "access_token": self.access_token
            }
            
            async with self.session.post(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    post_id = data.get("id")
                    if post_id:
                        self.logger.info(f"貼文發布成功：{post_id}")
                        return post_id
                    else:
                        self.logger.error("無法獲取貼文 ID")
                        return None
                else:
                    error_text = await response.text()
                    self.logger.error(f"貼文發布失敗：{response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"發布貼文時發生錯誤：{str(e)}")
            return None
            
    async def publish_post(self, content: str) -> Optional[str]:
        """發布貼文
        
        Args:
            content: 貼文內容
            
        Returns:
            Optional[str]: 貼文 ID，如果發布失敗則返回 None
        """
        try:
            # 建立媒體容器
            container_id = await self.create_media_container(content)
            if not container_id:
                return None
                
            # 等待 30 秒讓伺服器處理媒體
            await asyncio.sleep(30)
            
            # 發布容器
            return await self.publish_container(container_id)
            
        except Exception as e:
            self.logger.error(f"發布貼文過程中發生錯誤：{str(e)}")
            return None
            
    async def get_post(self, post_id: str) -> Optional[Dict[str, Any]]:
        """獲取貼文資訊
        
        Args:
            post_id: 貼文 ID
            
        Returns:
            Optional[Dict[str, Any]]: 貼文資訊，如果獲取失敗則返回 None
        """
        try:
            url = f"{self.base_url}/{post_id}"
            params = {
                "fields": "id,text,timestamp",
                "access_token": self.access_token
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_text = await response.text()
                    self.logger.error(f"獲取貼文失敗：{response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"獲取貼文時發生錯誤：{str(e)}")
            return None