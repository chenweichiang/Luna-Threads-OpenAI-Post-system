"""
Version: 2024.03.31 (v1.1.6)
Author: ThreadsPoster Team
Description: Threads 處理器類別，負責管理與 Threads 平台的互動
Last Modified: 2024.03.31
Changes:
- 改用官方 Threads Graph API
- 加強錯誤處理
- 優化連接管理
- 統一日誌路徑
- 支援共用 HTTP session
- 改進文章發布日誌記錄，顯示完整內容
- 確保文章內容在日誌中正確顯示
"""

import logging
from typing import Optional, Dict, Any
import aiohttp
from src.threads_api import ThreadsAPI
from src.exceptions import ThreadsAPIError
from datetime import datetime, timezone

class ThreadsHandler:
    """Threads 處理器類別"""
    
    def __init__(self, access_token: str, user_id: str, database, session: aiohttp.ClientSession):
        """初始化 Threads 處理器
        
        Args:
            access_token: Threads API access token
            user_id: Threads 用戶 ID
            database: 資料庫處理器
            session: HTTP session
        """
        self.api = ThreadsAPI(access_token, user_id, session)
        self.database = database
        self.logger = logging.getLogger(__name__)
        self._session = session
        
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
            self.logger.error("初始化過程中發生錯誤：%s", str(e))
            return False
            
    async def close(self):
        """關閉處理器"""
        try:
            await self.api.close()
            self.logger.info("Threads 處理器已關閉")
        except Exception as e:
            self.logger.error("關閉處理器時發生錯誤：%s", str(e))
        
    async def post_content(self, content: str) -> Optional[str]:
        """發布文章到 Threads
        
        Args:
            content: 要發布的文章內容
            
        Returns:
            Optional[str]: 成功時返回文章ID，失敗時返回 None
        """
        try:
            # 檢查內容長度
            if len(content) < 10:
                self.logger.error("文章內容太短")
                return None
            elif len(content) > 500:
                self.logger.error("文章內容超過長度限制")
                return None
                
            # 發布文章
            result = await self.api.publish_post(content)
            if result is not None and "id" in result:
                post_id = result["id"]
                # 記錄完整文章內容
                self.logger.info("發文成功：%s", content)
                return post_id
                
            self.logger.error("發文失敗：無法獲取文章ID")
            return None
            
        except ThreadsAPIError as e:
            self.logger.error("Threads API 錯誤：%s", str(e))
            return None
        except Exception as e:
            self.logger.error("發文過程發生錯誤：%s", str(e))
            return None
            
    async def get_post(self, post_id: str) -> Optional[Dict[str, Any]]:
        """獲取貼文資訊
        
        Args:
            post_id: 貼文 ID
            
        Returns:
            Optional[Dict[str, Any]]: 貼文資訊，如果獲取失敗則返回 None
        """
        try:
            # 先從資料庫查詢
            post_data = await self.database.get_post(post_id)
            if post_data is not None:
                return post_data
                
            # 如果資料庫沒有，從 API 獲取
            post_info = await self.api.get_post(post_id)
            if post_info is not None:
                self.logger.info("成功獲取貼文資訊：%s", post_id)
                return post_info
            else:
                self.logger.error("獲取貼文資訊失敗：%s", post_id)
                return None
                
        except ThreadsAPIError as e:
            self.logger.error("Threads API 錯誤：%s", str(e))
            return None
        except Exception as e:
            self.logger.error("獲取貼文資訊時發生錯誤：%s", str(e))
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
                self.logger.info("貼文刪除成功：%s", post_id)
                return True
            else:
                self.logger.error("貼文刪除失敗：%s", post_id)
                return False
                
        except ThreadsAPIError as e:
            self.logger.error("Threads API 錯誤：%s", str(e))
            return False
        except Exception as e:
            self.logger.error("刪除貼文時發生錯誤：%s", str(e))
            return False 