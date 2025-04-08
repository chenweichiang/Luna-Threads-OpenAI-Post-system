"""
Version: 2025.04.02 (v1.2.1)
Author: ThreadsPoster Team
Description: 監控器類別，負責協調系統運行
Copyright (c) 2025 Chiang, Chenwei. All rights reserved.
License: MIT License
Last Modified: 2025.04.02
Changes:
- 實現基本監控功能
- 加強錯誤處理
- 改進日誌記錄
- 加入 AI 處理器支援
- 優化發文內容日誌記錄，顯示完整文章
- 調整發文上限為每日5次
- 適配新的發文計劃系統
"""

import logging
import asyncio
import signal
from datetime import datetime
from typing import Optional

from database import Database
from db_handler import DatabaseHandler
from threads_handler import ThreadsHandler
from content_generator import ContentGenerator
from time_controller import TimeController
from ai_handler import AIHandler

class Monitor:
    """監控器類別"""
    
    def __init__(
        self,
        threads_handler: ThreadsHandler,
        database: DatabaseHandler,
        content_generator: ContentGenerator,
        time_controller: TimeController,
        ai_handler: AIHandler,
        max_posts_per_day: int = 5
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

class LunaThreadsMonitor:
    """Luna Threads 監控器，用於監控 Luna 的發文系統"""
    
    def __init__(
        self,
        config,
        db_handler: DatabaseHandler,
        time_controller: TimeController,
        content_generator: ContentGenerator,
        threads_handler: ThreadsHandler
    ):
        """初始化 Luna Threads 監控器
        
        Args:
            config: 設定物件
            db_handler: 資料庫處理器
            time_controller: 時間控制器
            content_generator: 內容生成器
            threads_handler: Threads 處理器
        """
        self.config = config
        self.db_handler = db_handler
        self.time_controller = time_controller
        self.content_generator = content_generator
        self.threads_handler = threads_handler
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.shutdown_event = asyncio.Event()
        self.max_posts_per_day = 5  # 固定為每日最多5篇
        
    async def start(self):
        """開始監控發文系統"""
        try:
            self.running = True
            self.logger.info("========== 開始監控 Luna Threads 發文系統 ==========")
            self.logger.info("每日最大發文數：%d", self.max_posts_per_day)
            today_count = await self.db_handler.get_today_posts_count()
            self.logger.info("目前今日發文計數：%d", today_count)

            while self.running and not self.shutdown_event.is_set():
                try:
                    # 檢查是否應該發文
                    if not self.time_controller.should_post():
                        # 取得等待時間
                        wait_time = self.time_controller.get_wait_time()
                        
                        # 顯示等待信息
                        if wait_time > 60:
                            minutes = int(wait_time / 60)
                            seconds = int(wait_time % 60)
                            self.logger.info("等待下次發文時間 %d 分 %d 秒", minutes, seconds)
                        else:
                            self.logger.info("等待下次發文時間 %d 秒", int(wait_time))
                            
                        # 等待一段時間再檢查
                        await asyncio.sleep(min(wait_time, 300))  # 最多等待5分鐘再檢查一次
                        continue
                    
                    self.logger.info("正在進行新一輪發文檢查...")
                    
                    # 檢查是否達到每日發文上限
                    current_post_count = await self.db_handler.get_today_posts_count()
                    if current_post_count >= self.max_posts_per_day:
                        self.logger.info("已達到每日發文上限 (%d/%d)", current_post_count, self.max_posts_per_day)
                        # 等待一段時間後再檢查
                        await asyncio.sleep(1800)  # 30分鐘
                        continue
                    
                    # 取得下一篇要發布的文章
                    self.logger.info("正在生成發文內容...")
                    content = await self.content_generator.get_content()
                    
                    if content is None or not content.strip():
                        self.logger.warning("無法生成有效的文章內容")
                        await asyncio.sleep(300)  # 休息5分鐘後再試
                        continue
                    
                    # 發布文章
                    self.logger.info("正在發布文章...")
                    self.logger.info("文章內容: %s", content)
                    post_id = await self.threads_handler.post(content)
                    
                    if post_id:
                        # 儲存發文記錄
                        self.logger.info("發文成功，ID: %s", post_id)
                        await self.db_handler.save_post({
                            "post_id": post_id,
                            "content": content,
                            "timestamp": datetime.now(),
                            "status": "published"
                        })
                        
                        # 儲存文章內容
                        await self.db_handler.save_article({
                            "post_id": post_id,
                            "content": content,
                            "created_at": datetime.now()
                        })
                        
                        # 更新發文計數並計算下次發文時間
                        await self.time_controller.wait_until_next_post()
                        
                        # 顯示發文計劃資訊
                        time_info = self.time_controller.get_current_time_info()
                        self.logger.info("發文計劃: 今日已發文 %s，下次發文時間: %s", 
                                        time_info["today_post_count"],
                                        time_info["next_post_time"])
                    else:
                        self.logger.error("發文失敗")
                        # 失敗後等待一段時間再試
                        await asyncio.sleep(600)  # 10分鐘

                except Exception as e:
                    self.logger.error("發文過程發生錯誤：%s", str(e), exc_info=True)
                    # 遇到錯誤時等待一段時間
                    await asyncio.sleep(600)  # 10分鐘
            
            self.logger.info("監控器循環已結束")
            
        except Exception as e:
            self.logger.error("監控系統發生嚴重錯誤：%s", str(e), exc_info=True)
            raise
        finally:
            self.logger.info("========== Luna Threads 監控器已停止 ==========")
            
    async def stop(self):
        """停止監控"""
        self.logger.info("接收到停止監控命令")
        self.running = False
        self.shutdown_event.set()
        self.logger.info("已設置關閉信號，等待監控器循環結束") 