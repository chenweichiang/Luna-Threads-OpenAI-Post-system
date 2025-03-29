"""
Version: 2024.03.30
Author: ThreadsPoster Team
Description: 主程式入口點
Last Modified: 2024.03.30
Changes:
- 優化系統初始化流程
- 加強錯誤處理
- 改進日誌記錄
"""

import asyncio
import logging
import os
from src.config import Config
from src.database import DatabaseHandler
from src.threads_handler import ThreadsHandler
from src.ai_handler import AIHandler
from src.time_controller import TimeController
from src.monitor import Monitor
from src.logger import setup_logger

# 設定日誌
logger = logging.getLogger(__name__)

async def main():
    """主程式入口點"""
    try:
        # 載入設定
        config = Config()
        setup_logger(config)
        logger.info("設定載入完成")
        
        # 初始化資料庫
        db = DatabaseHandler(
            mongodb_uri=config.MONGODB_URI,
            database=config.MONGODB_DB_NAME
        )
        await db.connect()
        logger.info("資料庫連接成功")
        
        # 重置今日發文計數
        count = await db.get_today_posts_count()
        logger.info(f"今日已發文數量：{count}")
        
        # 初始化 Threads 處理器
        threads_handler = ThreadsHandler(
            access_token=os.getenv("THREADS_ACCESS_TOKEN"),
            user_id=os.getenv("THREADS_USER_ID")
        )
        if not await threads_handler.initialize():
            logger.error("Threads 處理器初始化失敗")
            return
        logger.info("Threads 處理器初始化成功")
        
        # 初始化 AI 處理器
        ai_handler = AIHandler(config)
        await ai_handler.initialize(db)
        logger.info("AI 處理器初始化成功")
        
        # 初始化時間控制器
        time_controller = TimeController(
            timezone=str(config.TIMEZONE),
            post_interval=config.SYSTEM_CONFIG['post_interval']
        )
        
        # 初始化監控器
        monitor = Monitor(
            db=db,
            threads_handler=threads_handler,
            ai_handler=ai_handler,
            time_controller=time_controller,
            max_daily_posts=config.SYSTEM_CONFIG['max_daily_posts']
        )
        
        # 開始監控
        await monitor.start()
        
    except Exception as e:
        logger.error(f"系統執行時發生錯誤：{str(e)}")
        logger.error(f"系統異常終止：{str(e)}", exc_info=True)
    finally:
        # 關閉資料庫連接
        if 'db' in locals():
            await db.close()
            logger.info("資料庫連接已關閉")

if __name__ == "__main__":
    asyncio.run(main()) 