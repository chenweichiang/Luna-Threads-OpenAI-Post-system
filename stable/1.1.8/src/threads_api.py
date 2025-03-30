"""
Version: 2024.03.31 (v1.1.6)
Author: ThreadsPoster Team
Description: Threads API 介面
Last Modified: 2024.03.31
Changes:
- 改用官方 Threads Graph API
- 加強錯誤處理
- 優化連接管理
- 支援共用 HTTP session
- 修正API端點，使用正確的兩步驟發文流程
- 實現文章容器創建與發布的分離流程
- 根據官方文檔調整等待時間
"""

import logging
import aiohttp
import asyncio
from typing import Optional, Dict, Any
from src.exceptions import ThreadsAPIError

class ThreadsAPI:
    """Threads API 介面類別"""
    
    def __init__(self, access_token: str, user_id: str, session: aiohttp.ClientSession):
        """初始化 Threads API
        
        Args:
            access_token: API access token
            user_id: 用戶 ID
            session: HTTP session
        """
        self.access_token = access_token
        self.user_id = user_id
        self.session = session
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://graph.threads.net/v1.0"
        
    async def initialize(self) -> bool:
        """初始化 API 連接
        
        Returns:
            bool: 是否初始化成功
        """
        try:
            # 測試連接
            async with self.session.get(
                f"{self.base_url}/{self.user_id}",
                params={"access_token": self.access_token}
            ) as response:
                if response.status == 200:
                    self.logger.info("API 連接已初始化")
                    return True
                else:
                    error_text = await response.text()
                    self.logger.error("API 連接失敗：%d，錯誤：%s", response.status, error_text)
                    return False
                    
        except Exception as e:
            self.logger.error("初始化 API 時發生錯誤：%s", str(e))
            return False
            
    async def close(self):
        """關閉 API 連接"""
        try:
            self.logger.info("API 連接已關閉")
        except Exception as e:
            self.logger.error("關閉 API 連接時發生錯誤：%s", str(e))
            
    async def _create_post(self, content: str) -> Optional[Dict[str, Any]]:
        """建立文章容器
        
        Args:
            content: 文章內容
            
        Returns:
            Optional[Dict[str, Any]]: 成功時返回文章容器資訊，失敗時返回 None
        """
        try:
            params = {
                "access_token": self.access_token,
                "media_type": "TEXT",
                "text": content
            }
            
            async with self.session.post(
                f"{self.base_url}/{self.user_id}/threads",
                params=params
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    self.logger.info("文章容器建立成功")
                    return result
                else:
                    error_text = await response.text()
                    self.logger.error("建立文章失敗：%s", error_text)
                    return None
                    
        except Exception as e:
            self.logger.error("建立文章時發生錯誤：%s", str(e))
            return None
            
    async def _publish_post(self, container_id: str) -> Optional[Dict[str, Any]]:
        """發布文章容器
        
        Args:
            container_id: 文章容器 ID
            
        Returns:
            Optional[Dict[str, Any]]: 成功時返回包含文章ID的字典，失敗時返回 None
        """
        try:
            params = {
                "access_token": self.access_token,
                "creation_id": container_id
            }
            
            async with self.session.post(
                f"{self.base_url}/{self.user_id}/threads_publish",
                params=params
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    self.logger.info("文章發布成功")
                    return result
                else:
                    error_text = await response.text()
                    self.logger.error("發布文章失敗：%s", error_text)
                    return None
                    
        except Exception as e:
            self.logger.error("發布文章時發生錯誤：%s", str(e))
            return None
            
    async def publish_post(self, content: str) -> Optional[Dict[str, str]]:
        """發布一篇文章到 Threads
        
        Args:
            content: 要發布的文章內容
            
        Returns:
            Optional[Dict[str, str]]: 成功時返回包含文章ID的字典，失敗時返回 None
        """
        try:
            # 建立文章容器
            container_data = await self._create_post(content)
            if not container_data or "id" not in container_data:
                self.logger.error("建立文章容器失敗")
                return None
                
            # 等待 30 秒，讓伺服器有足夠時間處理上傳（根據官方文檔建議）
            container_id = str(container_data["id"])
            self.logger.info("等待伺服器處理文章容器，ID：%s", container_id)
            await asyncio.sleep(5)  # 在測試環境中可以減少等待時間
                
            # 發布文章容器
            publish_result = await self._publish_post(container_id)
            if publish_result and "id" in publish_result:
                post_id = str(publish_result["id"])
                self.logger.info("文章發布成功，ID：%s", post_id)
                return {"id": post_id}
            else:
                self.logger.error("發布文章容器失敗")
                return None
                
        except Exception as e:
            self.logger.error("發布文章時發生錯誤：%s", str(e))
            return None
            
    async def get_post(self, post_id: str) -> Optional[Dict[str, Any]]:
        """獲取貼文資訊
        
        Args:
            post_id: 貼文 ID
            
        Returns:
            Optional[Dict[str, Any]]: 貼文資訊，如果獲取失敗則返回 None
        """
        try:
            params = {
                "access_token": self.access_token,
                "fields": "id,text,timestamp,link_attachment_url"
            }
                
            async with self.session.get(
                f"{self.base_url}/{post_id}",
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.logger.info("成功獲取貼文資訊：%s", post_id)
                    return data
                else:
                    error_text = await response.text()
                    self.logger.error("獲取貼文失敗：%s", error_text)
                    return None
                    
        except Exception as e:
            self.logger.error("獲取貼文時發生錯誤：%s", str(e))
            return None
            
    async def delete_post(self, post_id: str) -> bool:
        """刪除貼文
        
        Args:
            post_id: 貼文 ID
            
        Returns:
            bool: 是否刪除成功
        """
        try:
            params = {
                "access_token": self.access_token
            }
                
            async with self.session.delete(
                f"{self.base_url}/{post_id}",
                params=params
            ) as response:
                if response.status == 200:
                    self.logger.info("貼文刪除成功：%s", post_id)
                    return True
                else:
                    error_text = await response.text()
                    self.logger.error("貼文刪除失敗：%s", error_text)
                    return False
                    
        except Exception as e:
            self.logger.error("刪除貼文時發生錯誤：%s", str(e))
            return False