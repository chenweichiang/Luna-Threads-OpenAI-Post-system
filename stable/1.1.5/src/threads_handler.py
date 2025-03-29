"""
Version: 2024.03.30
Author: ThreadsPoster Team
Description: Threads 處理器類別，負責管理與 Threads 平台的互動
Last Modified: 2024.03.30
Changes:
- 改用官方 Threads Graph API
- 加強錯誤處理
- 優化連接管理
- 統一日誌路徑
"""

import logging
from typing import Optional, Dict, Any
from src.threads_api import ThreadsAPI
from src.exceptions import ThreadsAPIError

class ThreadsHandler:
    """Threads 處理器類別"""
    
    def __init__(self, access_token: str, user_id: str):
        """初始化 Threads 處理器
        
        Args:
            access_token: Threads API access token
            user_id: Threads 用戶 ID
        """
        self.api = ThreadsAPI(access_token, user_id)
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self) -> bool:
        """初始化處理器
        
        Returns:
            bool: 是否初始化成功
        """
        try:
            if await self.api.initialize():
                self.logger.info("Threads 處理器初始化成功")
                return True
            else:
                self.logger.error("Threads 處理器初始化失敗")
                return False
        except Exception as e:
            self.logger.error(f"初始化過程中發生錯誤：{str(e)}")
            return False
            
    async def close(self):
        """關閉處理器"""
        await self.api.close()
        self.logger.info("Threads 處理器已關閉")
        
    async def post_content(self, content: str) -> Optional[str]:
        """發布內容
        
        Args:
            content: 要發布的內容
            
        Returns:
            Optional[str]: 貼文 ID，如果發布失敗則返回 None
        """
        try:
            post_id = await self.api.publish_post(content)
            if post_id:
                self.logger.info(f"內容發布成功：{content[:30]}...")
                return post_id
            else:
                self.logger.error("內容發布失敗")
                return None
        except Exception as e:
            self.logger.error(f"發布內容時發生錯誤：{str(e)}")
            return None
            
    async def get_post(self, post_id: str) -> Optional[Dict[str, Any]]:
        """獲取貼文資訊
        
        Args:
            post_id: 貼文 ID
            
        Returns:
            Optional[Dict[str, Any]]: 貼文資訊，如果獲取失敗則返回 None
        """
        try:
            post_info = await self.api.get_post(post_id)
            if post_info:
                self.logger.info(f"成功獲取貼文資訊：{post_id}")
                return post_info
            else:
                self.logger.error(f"獲取貼文資訊失敗：{post_id}")
                return None
        except Exception as e:
            self.logger.error(f"獲取貼文資訊時發生錯誤：{str(e)}")
            return None
            
    async def delete_post(self, post_id: str) -> bool:
        """刪除貼文
        
        Args:
            post_id: 貼文 ID
            
        Returns:
            bool: 是否刪除成功
        """
        try:
            success = await self.api.delete_post(post_id)
            if success:
                self.logger.info(f"貼文刪除成功：{post_id}")
                return True
            else:
                self.logger.error(f"貼文刪除失敗：{post_id}")
                return False
        except Exception as e:
            self.logger.error(f"刪除貼文時發生錯誤：{str(e)}")
            return False 