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
- 整合性能監控功能
"""

import logging
import asyncio
from typing import Optional, Dict, Any
import aiohttp
import pytz
from datetime import datetime

from threads_api import ThreadsAPI
from performance_monitor import performance_monitor, track_performance

class ThreadsHandler:
    """Threads 處理器類別，負責管理與 Threads 平台的互動"""
    
    def __init__(self, config=None, api=None, db_handler=None, session=None):
        """初始化 Threads 處理器
        
        Args:
            config: 設定物件
            api: ThreadsAPI 實例
            db_handler: 資料庫處理器
            session: HTTP 會話
        """
        self.config = config
        self.db_handler = db_handler
        self.api = api
        self.session = session
        self.logger = logging.getLogger(__name__)
        self.timezone = pytz.timezone("Asia/Taipei")
        self.performance_monitor = performance_monitor
        
    async def initialize(self) -> bool:
        """初始化 Threads 處理器
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            result = await self.api.initialize()
            if result:
                self.logger.info("Threads 處理器初始化成功")
            else:
                self.logger.error("Threads 處理器初始化失敗")
            return result
        except Exception as e:
            self.logger.error("初始化 Threads 處理器時發生錯誤：%s", str(e))
            return False
            
    async def close(self):
        """關閉資源"""
        try:
            await self.api.close()
            self.logger.info("Threads 處理器資源已關閉")
        except Exception as e:
            self.logger.error("關閉 Threads 處理器資源時發生錯誤：%s", str(e))
            
    @track_performance("post_content")
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
            self.performance_monitor.start_operation("threads_api_post")
            result = await self.api.publish_post(content)
            post_time = self.performance_monitor.end_operation("threads_api_post")
            
            if result is not None and "id" in result:
                post_id = result["id"]
                # 記錄完整文章內容
                self.logger.info("發文成功：%s", content)
                
                # 記錄 API 使用
                self.performance_monitor.record_api_request(
                    "threads", 
                    success=True, 
                    response_time=post_time
                )
                
                return post_id
                
            self.logger.error("發文失敗：無法獲取文章ID")
            self.performance_monitor.record_api_request("threads", success=False)
            return None
            
        except Exception as e:
            self.logger.error("發文時發生錯誤：%s", str(e))
            self.performance_monitor.record_api_request("threads", success=False)
            return None
            
    async def post(self, content: str) -> Optional[str]:
        """發布文章到 Threads (post_content的別名)
        
        Args:
            content: 要發布的文章內容
            
        Returns:
            Optional[str]: 成功時返回文章ID，失敗時返回 None
        """
        return await self.post_content(content)
            
    @track_performance("get_post")
    async def get_post(self, post_id: str) -> Optional[Dict[str, Any]]:
        """獲取文章詳情
        
        Args:
            post_id: 文章ID
            
        Returns:
            Optional[Dict[str, Any]]: 文章詳情
        """
        try:
            self.performance_monitor.start_operation("threads_api_get")
            result = await self.api.get_post(post_id)
            get_time = self.performance_monitor.end_operation("threads_api_get")
            
            if result is not None:
                self.performance_monitor.record_api_request(
                    "threads", 
                    success=True, 
                    response_time=get_time
                )
                return result
                
            self.performance_monitor.record_api_request("threads", success=False)
            return None
            
        except Exception as e:
            self.logger.error("獲取文章詳情時發生錯誤：%s", str(e))
            self.performance_monitor.record_api_request("threads", success=False)
            return None
            
    @track_performance("delete_post")  
    async def delete_post(self, post_id: str) -> bool:
        """刪除文章
        
        Args:
            post_id: 文章ID
            
        Returns:
            bool: 是否刪除成功
        """
        try:
            self.performance_monitor.start_operation("threads_api_delete")
            result = await self.api.delete_post(post_id)
            delete_time = self.performance_monitor.end_operation("threads_api_delete")
            
            if result:
                self.logger.info("刪除文章成功：%s", post_id)
                self.performance_monitor.record_api_request(
                    "threads", 
                    success=True, 
                    response_time=delete_time
                )
                return True
                
            self.logger.error("刪除文章失敗：%s", post_id)
            self.performance_monitor.record_api_request("threads", success=False)
            return False
            
        except Exception as e:
            self.logger.error("刪除文章時發生錯誤：%s", str(e))
            self.performance_monitor.record_api_request("threads", success=False)
            return False 