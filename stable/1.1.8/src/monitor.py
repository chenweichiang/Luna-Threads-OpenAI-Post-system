"""
Version: 2024.03.31 (v1.1.6)
Author: ThreadsPoster Team
Description: 監控器類別，負責協調系統各個組件的運作
Last Modified: 2024.03.31
Changes:
- 實現基本監控功能
- 加強錯誤處理
- 改進日誌記錄
- 加入 AI 處理器支援
- 優化發文內容日誌記錄，顯示完整文章
- 提高發文上限以適應測試需求
"""

import logging
import asyncio
import signal
from datetime import datetime
from typing import Optional

from src.database import Database
from src.db_handler import DatabaseHandler
from src.threads_handler import ThreadsHandler
from src.content_generator import ContentGenerator
from src.time_controller import TimeController
from src.ai_handler import AIHandler

class Monitor:
    """監控器類別"""
    
    def __init__(
        self,
        threads_handler: ThreadsHandler,
        database: DatabaseHandler,
        content_generator: ContentGenerator,
        time_controller: TimeController,
        ai_handler: AIHandler,
        max_posts_per_day: int = 999
    ):
        """初始化監控器
        
        Args:
            threads_handler: Threads 處理器
            database: 資料庫處理器
            content_generator: 內容生成器
            time_controller: 時間控制器
            ai_handler: AI 處理器
            max_posts_per_day: 每日最大發文數
        """
        self.threads_handler = threads_handler
        self.database = database
        self.content_generator = content_generator
        self.time_controller = time_controller
        self.ai_handler = ai_handler
        self.max_posts_per_day = max_posts_per_day
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.shutdown_event = asyncio.Event()
        
    async def start(self):
        """開始監控並發文"""
        try:
            self.logger.info("開始監控發文系統")
            self.logger.info("每日最大發文數：%d", self.max_posts_per_day)
            self.logger.info("目前發文計數：%d", await self.database.get_today_posts_count())

            while True:
                try:
                    # 檢查是否達到每日發文上限
                    current_post_count = await self.database.get_today_posts_count()
                    if current_post_count >= self.max_posts_per_day:
                        self.logger.info("已達到每日發文上限")
                        await asyncio.sleep(3600)  # 休息一小時後再檢查
                        continue

                    # 取得下一篇要發布的文章
                    content = await self.content_generator.get_content()
                    if content is None:
                        self.logger.warning("無法生成文章內容")
                        await asyncio.sleep(300)  # 休息5分鐘後再試
                        continue

                    # 使用 AI 處理器分析內容情感
                    sentiment = await self.ai_handler.analyze_sentiment(content)
                    self.logger.info("內容情感分析：%s", sentiment)

                    # 發布文章
                    post_id = await self.threads_handler.post_content(content)
                    
                    if post_id is not None:
                        # 儲存發文記錄
                        post_data = {
                            "post_id": post_id,
                            "content": content,
                            "sentiment": sentiment,
                            "timestamp": datetime.now()
                        }
                        if await self.database.save_article(post_id, content, []):
                            # 更新發文計數
                            await self.database.increment_post_count()
                            
                            # 計算下次發文時間
                            next_post_time = self.time_controller.next_post_time
                            interval = self.time_controller.get_interval()
                            
                            self.logger.info("發文成功 - 文章ID：%s，內容：%s，下次發文時間：%s，間隔：%d 秒",
                                str(post_id),
                                content,
                                str(next_post_time),
                                interval
                            )
                        else:
                            self.logger.error("儲存發文失敗")
                    else:
                        self.logger.error("發文失敗")

                    # 等待到下一次發文時間
                    await self.time_controller.wait_until_next_post()

                except Exception as e:
                    self.logger.error("發文過程發生錯誤：%s", str(e))
                    await asyncio.sleep(300)  # 發生錯誤時休息5分鐘

        except Exception as e:
            self.logger.error("監控系統發生嚴重錯誤：%s", str(e))
            raise
        
    async def stop(self):
        """停止監控"""
        self.running = False
        self.shutdown_event.set()
        self.logger.info("監控器準備停止")
        
    async def handle_signal(self, sig: signal.Signals):
        """處理信號
        
        Args:
            sig: 信號類型
        """
        self.logger.info("收到信號：%s", sig.name)
        await self.stop() 