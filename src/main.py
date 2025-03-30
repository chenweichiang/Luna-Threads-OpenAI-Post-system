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
- 整合性能監控功能
- 優化記憶體使用
- 預先生成內容以提高回應速度
"""

import asyncio
import logging
import os
import signal
import sys
import aiohttp
import pytz
from datetime import datetime
import gc

from src.config import Config
from src.database import Database
from src.db_handler import DatabaseHandler
from src.ai_handler import AIHandler
from src.threads_handler import ThreadsHandler
from src.threads_api import ThreadsAPI
from src.openai_api import OpenAIAPI
from src.monitor import Monitor
from src.time_controller import TimeController
from src.content_generator import ContentGenerator
from src.performance_monitor import performance_monitor, track_performance

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/threads_poster.log")
    ]
)

logger = logging.getLogger(__name__)

# 創建 event loop 和 signal handlers
loop = None

@track_performance("main_startup")
async def startup():
    """啟動系統"""
    # 記錄啟動時間
    start_time = datetime.now(pytz.timezone("Asia/Taipei"))
    logger.info("系統啟動，時間：%s", start_time.strftime("%Y-%m-%d %H:%M:%S"))
    performance_monitor.start_operation("system_initialize")
    
    # 載入設定
    logger.info("載入設定...")
    config = Config()
    logger.info("設定載入完成")
    
    # 建立 HTTP session
    logger.info("建立網路連接...")
    session = aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(
            limit=100,  # 增加連接數上限
            ttl_dns_cache=300,  # DNS 快取 5 分鐘
            keepalive_timeout=60,  # keepalive 時間增加
            enable_cleanup_closed=True  # 自動清理關閉的連接
        )
    )
    
    # 建立資料庫連接
    logger.info("建立資料庫連接...")
    db_handler = DatabaseHandler(config)
    await db_handler.initialize()
    logger.info("資料庫連接成功")
    
    # 初始化 API 處理器
    logger.info("初始化 API 處理器...")
    threads_api = ThreadsAPI(
        config.THREADS_ACCESS_TOKEN, 
        config.THREADS_USER_ID,
        session
    )
    
    # 初始化內容生成器
    logger.info("初始化內容生成器...")
    content_generator = ContentGenerator(config.OPENAI_API_KEY, session, db_handler)
    await content_generator.initialize()
    
    # 初始化 AI 處理器
    logger.info("初始化 AI 處理器...")
    ai_handler = AIHandler(
        config.OPENAI_API_KEY,
        session,
        db_handler
    )
    await ai_handler.initialize()
    
    # 初始化 Threads 處理器
    logger.info("初始化 Threads 處理器...")
    threads_handler = ThreadsHandler(threads_api, session)
    
    # 初始化時間控制器
    logger.info("初始化時間控制器...")
    time_controller = TimeController()
    
    # 初始化監控器
    logger.info("初始化監控器...")
    monitor = Monitor(
        threads_handler,
        db_handler,
        content_generator,
        time_controller,
        ai_handler,
        config.MAX_POSTS_PER_DAY
    )
    
    # 設定系統資源限制
    logger.info("設定系統資源限制...")
    
    # 執行垃圾收集，減少內存佔用
    gc.collect()
    
    # 預先生成一些內容，提高回應速度
    logger.info("預先生成內容...")
    try:
        await content_generator.pre_generate_content(2)
    except Exception as e:
        logger.warning(f"預先生成內容失敗：{str(e)}")
    
    # 完成初始化
    initialize_time = performance_monitor.end_operation("system_initialize")
    logger.info("所有組件初始化完成，耗時 %.2f 秒", initialize_time)
    
    # 開始監控
    logger.info("開始監控系統...")
    
    # 處理信號
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s, monitor, db_handler, session)))
    
    try:
        # 啟動監控器
        await monitor.start()
    except Exception as e:
        logger.error("監控系統發生錯誤：%s", str(e))
        await shutdown(signal.SIGTERM, monitor, db_handler, session)
    
@track_performance("main_shutdown")
async def shutdown(sig, monitor, db_handler, session):
    """關閉系統
    
    Args:
        sig: 信號
        monitor: 監控器
        db_handler: 資料庫處理器
        session: HTTP session
    """
    performance_monitor.start_operation("system_shutdown")
    logger.info("開始關閉系統...")
    
    try:
        # 關閉監控器
        logger.info("關閉監控器...")
        await monitor.stop()
        
        # 關閉資料庫連接
        logger.info("關閉資料庫連接...")
        await db_handler.close()
        
        # 關閉 HTTP session
        logger.info("關閉網路連接...")
        await session.close()
        
        # 儲存性能指標
        logger.info("儲存性能指標...")
        try:
            performance_monitor.save_metrics()
        except Exception as e:
            logger.error(f"儲存性能指標失敗：{str(e)}")
        
        # 取得事件循環
        loop = asyncio.get_running_loop()
        
        # 取消所有剩餘任務
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        logger.info("取消 %d 個剩餘任務...", len(tasks))
        
        for task in tasks:
            task.cancel()
            
        # 等待所有任務取消
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # 計算關閉時間
        shutdown_time = performance_monitor.end_operation("system_shutdown")
        logger.info("系統已成功關閉，耗時 %.2f 秒", shutdown_time)
        
        # 停止事件循環
        loop.stop()
    except Exception as e:
        logger.error(f"關閉系統時發生錯誤：{str(e)}")
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.stop()

# 主程式入口點
if __name__ == "__main__":
    try:
        # 確保日誌目錄存在
        os.makedirs("logs", exist_ok=True)
        
        # 建立並啟動事件循環
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 啟動系統
        loop.run_until_complete(startup())
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("接收到使用者中斷，準備關閉系統...")
    except Exception as e:
        logger.critical("系統發生嚴重錯誤：%s", str(e), exc_info=True)
    finally:
        # 確保事件循環已關閉
        if loop and not loop.is_closed():
            loop.close()
        logger.info("事件循環已關閉，程式結束")
        sys.exit(0) 