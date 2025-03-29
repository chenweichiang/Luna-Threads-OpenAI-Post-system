"""
回覆管理系統
處理所有回覆相關的邏輯
"""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, List

from .database import Database
from .threads_api import ThreadsAPI
from .openai_api import OpenAIAPI

logger = logging.getLogger(__name__)

class ReplyManager:
    def __init__(self, db: Database, threads_api: ThreadsAPI, openai_api: OpenAIAPI):
        self.db = db
        self.threads_api = threads_api
        self.openai_api = openai_api
        
    async def check_new_replies(self):
        """檢查新回覆"""
        try:
            # 從 Threads API 獲取新回覆
            replies = await self.threads_api.get_new_replies()
            
            if not replies:
                logger.info("沒有新回覆")
                return
                
            logger.info(f"發現 {len(replies)} 個新回覆")
            
            # 保存新回覆到資料庫
            for reply in replies:
                await self.db.save_reply(
                    reply_id=reply["id"],
                    post_id=reply["post_id"],
                    content=reply["content"],
                    username=reply["username"],
                    created_at=datetime.now()
                )
                
        except Exception as e:
            logger.error(f"檢查新回覆時發生錯誤: {str(e)}")
            
    async def process_replies(self):
        """處理未處理的回覆"""
        try:
            # 獲取未處理的回覆
            unprocessed_replies = await self.db.get_unprocessed_replies()
            
            if not unprocessed_replies:
                logger.info("沒有未處理的回覆")
                return
                
            logger.info(f"開始處理 {len(unprocessed_replies)} 個回覆")
            
            for reply in unprocessed_replies:
                try:
                    # 使用 OpenAI 生成回覆內容
                    response = await self.openai_api.generate_reply(
                        user_message=reply["content"],
                        username=reply["username"]
                    )
                    
                    # 發送回覆
                    await self.threads_api.reply_to_post(
                        post_id=reply["post_id"],
                        content=response
                    )
                    
                    # 標記回覆為已處理
                    await self.db.mark_reply_as_processed(reply["reply_id"])
                    
                    logger.info(f"已回覆 {reply['username']}")
                    
                except Exception as e:
                    logger.error(f"處理回覆時發生錯誤: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"處理回覆時發生錯誤: {str(e)}")
            
    async def get_reply_history(self, username: str) -> List[Dict]:
        """獲取與特定用戶的回覆歷史"""
        try:
            return await self.db.get_user_reply_history(username)
        except Exception as e:
            logger.error(f"獲取回覆歷史時發生錯誤: {str(e)}")
            return [] 