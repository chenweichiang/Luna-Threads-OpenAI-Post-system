"""
Version: 2024.03.30
Author: ThreadsPoster Team
Description: 監控器類別，負責協調系統各個組件的運作
Last Modified: 2024.03.30
Changes:
- 實現基本監控功能
- 加強錯誤處理
- 改進日誌記錄
"""

import logging
import asyncio
from datetime import datetime
from typing import Optional

from src.database import DatabaseHandler
from src.threads_handler import ThreadsHandler
from src.ai_handler import AIHandler
from src.time_controller import TimeController

class Monitor:
    """監控器類別"""
    
    def __init__(
        self,
        db: DatabaseHandler,
        threads_handler: ThreadsHandler,
        ai_handler: AIHandler,
        time_controller: TimeController,
        max_daily_posts: int = 999
    ):
        """初始化監控器
        
        Args:
            db: 資料庫處理器
            threads_handler: Threads 處理器
            ai_handler: AI 處理器
            time_controller: 時間控制器
            max_daily_posts: 每日最大發文數量
        """
        self.db = db
        self.threads_handler = threads_handler
        self.ai_handler = ai_handler
        self.time_controller = time_controller
        self.max_daily_posts = max_daily_posts
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        
    async def start(self):
        """開始監控"""
        self.is_running = True
        self.logger.info("監控器開始運作")
        
        try:
            while self.is_running:
                try:
                    # 檢查今日發文數量
                    post_count = await self.db.get_today_posts_count()
                    if post_count >= self.max_daily_posts:
                        self.logger.info("已達到今日發文上限")
                        await asyncio.sleep(3600)  # 休息一小時
                        continue
                        
                    # 檢查是否需要發文
                    next_post_time = await self.time_controller.get_next_post_time()
                    if next_post_time > datetime.now(self.time_controller.timezone):
                        wait_seconds = (next_post_time - datetime.now(self.time_controller.timezone)).total_seconds()
                        self.logger.info(f"等待下一次發文時間，休息 {wait_seconds} 秒")
                        await asyncio.sleep(wait_seconds)
                        continue
                        
                    # 生成並發布內容
                    content, topics, sentiment = await self.ai_handler.generate_content()
                    if not content:
                        self.logger.error("內容生成失敗")
                        await asyncio.sleep(300)  # 休息5分鐘
                        continue
                        
                    # 發布貼文
                    post_id = await self.threads_handler.post_content(content)
                    if not post_id:
                        self.logger.error("貼文發布失敗")
                        await asyncio.sleep(300)  # 休息5分鐘
                        continue
                        
                    # 儲存文章
                    article = {
                        "post_id": post_id,
                        "content": content,
                        "topics": topics,
                        "sentiment": sentiment,
                        "created_at": datetime.now(self.time_controller.timezone)
                    }
                    await self.db.save_article(article)
                    
                    # 增加發文計數
                    await self.db.increment_post_count()
                    
                    # 更新下一次發文時間
                    await self.time_controller.update_next_post_time()
                    
                    self.logger.info(f"發文成功：{content[:30]}...")
                    
                except Exception as e:
                    self.logger.error(f"監控過程中發生錯誤：{str(e)}")
                    await asyncio.sleep(300)  # 休息5分鐘
                    
        except asyncio.CancelledError:
            self.logger.info("監控器收到取消信號")
        except Exception as e:
            self.logger.error(f"監控器發生嚴重錯誤：{str(e)}")
        finally:
            self.is_running = False
            self.logger.info("監控器停止運作")
            
    async def stop(self):
        """停止監控"""
        self.is_running = False
        self.logger.info("監控器準備停止") 