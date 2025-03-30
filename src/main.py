"""
Version: 2024.03.31 (v1.1.6)
Author: ThreadsPoster Team
Description: 主程式入口點
Last Modified: 2024.03.31
Changes:
- 改進錯誤處理
- 優化資源管理
- 加強日誌記錄
- 修正資料庫處理器類別名稱
- 優化組件初始化流程
- 加強資源關閉處理
- 提高系統穩定性
"""

import os
import asyncio
import logging
import aiohttp
from datetime import datetime
import pytz

from src.config import Config
from src.monitor import Monitor
from src.threads_handler import ThreadsHandler
from src.content_generator import ContentGenerator
from src.time_controller import TimeController
from src.ai_handler import AIHandler
from src.db_handler import DatabaseHandler

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/threads_poster.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def initialize_components(config: Config, session: aiohttp.ClientSession, database: DatabaseHandler):
    """初始化系統組件
    
    Args:
        config: 設定物件
        session: HTTP會話
        database: 資料庫處理器
        
    Returns:
        tuple: (threads_handler, content_generator, time_controller, ai_handler)
    """
    try:
        # 初始化 Threads 處理器
        threads_handler = ThreadsHandler(
            access_token=config.THREADS_ACCESS_TOKEN,
            user_id=config.THREADS_USER_ID,
            database=database,
            session=session
        )
        
        # 初始化 AI 處理器
        ai_handler = AIHandler(config)
        await ai_handler.initialize(database)
        
        # 初始化內容生成器
        content_generator = ContentGenerator(
            api_key=config.OPENAI_API_KEY,
            session=session,
            db=database
        )
        
        # 初始化時間控制器
        time_controller = TimeController()
        
        return threads_handler, content_generator, time_controller, ai_handler
        
    except Exception as e:
        logger.error(f"初始化組件時發生錯誤：{str(e)}")
        raise

async def main():
    """主函數"""
    try:
        # 載入設定
        config = Config()
        logger.info("設定載入完成")
        
        # 初始化資料庫
        database = DatabaseHandler(config=config)
        await database.initialize()
        logger.info("資料庫連接成功")
        
        # 建立 HTTP 會話
        async with aiohttp.ClientSession() as session:
            # 初始化所有組件
            threads_handler, content_generator, time_controller, ai_handler = await initialize_components(
                config=config,
                session=session,
                database=database
            )
            logger.info("所有組件初始化完成")
            
            # 初始化監控器
            monitor = Monitor(
                threads_handler=threads_handler,
                database=database,
                content_generator=content_generator,
                time_controller=time_controller,
                ai_handler=ai_handler,
                max_posts_per_day=999
            )
            
            try:
                # 開始監控
                await monitor.start()
            except KeyboardInterrupt:
                logger.info("收到中斷信號，準備關閉系統")
            finally:
                # 關閉監控器
                await monitor.stop()
                logger.info("監控器已關閉")
                
                # 關閉資料庫連接
                await database.close()
                logger.info("資料庫連接已關閉")
                
                # 關閉 AI 處理器
                await ai_handler.close()
                logger.info("AI 處理器已關閉")
                
    except Exception as e:
        logger.error(f"系統執行時發生錯誤：{str(e)}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程式已正常結束")
    except Exception as e:
        logger.error(f"程式執行時發生錯誤：{str(e)}")
        raise 