"""
Version: 2025.03.31 (v1.1.9)
Author: ThreadsPoster Team
Description: 主程式入口點
Copyright (c) 2025 Chiang, Chenwei. All rights reserved.
License: MIT License
Last Modified: 2025.03.31
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
- 引入獨立的說話模式模組
"""

import asyncio
import logging
import os
import signal
import sys
import aiohttp
import pytz
from datetime import datetime, timedelta
import gc

from src.config import Config
from src.database import Database
from src.db_handler import DatabaseHandler
from src.ai_handler import AIHandler
from src.threads_handler import ThreadsHandler
from src.threads_api import ThreadsAPI
from src.openai_api import OpenAIAPI
from src.monitor import Monitor, LunaThreadsMonitor
from src.time_controller import TimeController
from src.content_generator import ContentGenerator
from src.performance_monitor import performance_monitor, track_performance
from src.speaking_patterns import SpeakingPatterns
from src.logger import setup_logger

# 設定環境變數
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONLEGACYWINDOWSSTDIO"] = "utf-8"

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

class ThreadsPosterApp:
    def __init__(self):
        # 設定日誌
        self.logger = setup_logger(__name__)
        self.logger.info("========== 初始化 ThreadsPoster 應用 ==========")
        
        # 基本配置
        self.config = Config()
        self.running = False
        self.debug = self.config.LOG_LEVEL.upper() == "DEBUG"  # 使用LOG_LEVEL判斷
        
        # 資料庫
        self.db_handler = None
        
        # 時間控制器
        self.time_controller = None
        
        # 監控器
        self.monitor = None
        
        # 統計數據
        self.stats = {
            "start_time": datetime.now(pytz.timezone("Asia/Taipei")),
            "posts_count": 0,
            "errors_count": 0,
            "last_db_stats_time": datetime.now(pytz.timezone("Asia/Taipei"))
        }
        # 資料庫統計輸出間隔 (秒)
        self.db_stats_interval = int(os.getenv("DB_STATS_INTERVAL", "3600"))  # 默認每小時
        
    async def initialize(self):
        """初始化應用"""
        try:
            # 初始化資料庫處理器
            self.logger.info("初始化資料庫連接...")
            self.db_handler = DatabaseHandler(self.config)
            await self.db_handler.initialize()
            
            # 初始化說話模式模組
            self.logger.info("初始化說話模式模組...")
            self.speaking_patterns = SpeakingPatterns()
            self.speaking_patterns.set_db_handler(self.db_handler)
            await self.speaking_patterns.initialize()
            
            # 初始化AI處理器
            self.openai_api = OpenAIAPI(self.config.OPENAI_API_KEY)
            await self.openai_api.ensure_session()  # 確保session已初始化
            
            self.ai_handler = AIHandler(self.config.OPENAI_API_KEY, self.openai_api.session, self.db_handler, self.config)
            # 設置說話模式模組
            self.ai_handler.speaking_patterns = self.speaking_patterns
            
            # 初始化Threads API
            self.threads_api = ThreadsAPI(self.config.THREADS_ACCESS_TOKEN, self.config.THREADS_USER_ID, self.openai_api.session)
            await self.threads_api.initialize()  # 確保API完全初始化
            
            # 初始化Threads處理器
            self.threads_handler = ThreadsHandler(self.config, self.threads_api, self.db_handler)
            await self.threads_handler.initialize()  # 確保完全初始化
            
            # 初始化內容生成器
            self.content_generator = ContentGenerator(self.config.OPENAI_API_KEY, self.openai_api.session, self.db_handler)
            # 設置說話模式模組
            self.content_generator.speaking_patterns = self.speaking_patterns
            # 設置Threads處理器
            self.content_generator.set_threads_handler(self.threads_handler)
            
            # 初始化時間控制器
            self.time_controller = TimeController(self.config)
            
            # 初始化監控器
            self.monitor = LunaThreadsMonitor(
                self.config,
                self.db_handler,
                self.time_controller,
                self.content_generator,
                self.threads_handler
            )
            
            # 設定定期輸出資料庫統計
            asyncio.create_task(self._schedule_db_stats_output())
            
            self.logger.info("ThreadsPoster 初始化完成")
            return True
        except Exception as e:
            self.logger.error(f"初始化失敗: {str(e)}")
            return False
            
    async def _schedule_db_stats_output(self):
        """定期輸出資料庫統計資訊"""
        while self.running:
            await asyncio.sleep(60)  # 每分鐘檢查一次是否需要輸出統計
            now = datetime.now(pytz.timezone("Asia/Taipei"))
            time_elapsed = (now - self.stats["last_db_stats_time"]).total_seconds()
            
            if time_elapsed >= self.db_stats_interval:
                await self._output_db_stats()
                self.stats["last_db_stats_time"] = now
    
    async def _output_db_stats(self):
        """輸出資料庫統計資訊"""
        try:
            if not self.db_handler or not self.db_handler.database:
                return
                
            stats = await self.db_handler.database.get_database_stats()
            
            # 輸出簡潔的統計摘要
            self.logger.info("========== 資料庫統計摘要 ==========")
            self.logger.info(f"文章總數: {stats.get('articles_count', 0)}")
            self.logger.info(f"用戶總數: {stats.get('users_count', 0)}")
            
            # 輸出快取統計
            cache_stats = stats.get("cache", {})
            self.logger.info("快取使用情況:")
            for cache_name, size in cache_stats.items():
                self.logger.info(f"  - {cache_name}: {size} 項")
                
            # 輸出流量統計
            traffic_stats = stats.get("traffic", {})
            if traffic_stats:
                self.logger.info("流量統計:")
                self.logger.info(f"  - 總讀取操作: {traffic_stats.get('read_operations', 0)}")
                self.logger.info(f"  - 總寫入操作: {traffic_stats.get('write_operations', 0)}")
                self.logger.info(f"  - 快取命中率: {traffic_stats.get('cache_hit_rate', 0):.2f}%")
                
                # 格式化流量數據
                def format_bytes(bytes_count):
                    if bytes_count < 1024:
                        return f"{bytes_count} B"
                    elif bytes_count < 1024 * 1024:
                        return f"{bytes_count/1024:.2f} KB"
                    else:
                        return f"{bytes_count/(1024*1024):.2f} MB"
                        
                sent = format_bytes(traffic_stats.get('total_bytes_sent', 0))
                received = format_bytes(traffic_stats.get('total_bytes_received', 0))
                self.logger.info(f"  - 總發送流量: {sent}")
                self.logger.info(f"  - 總接收流量: {received}")
                
            self.logger.info("=====================================")
            
        except Exception as e:
            self.logger.error(f"輸出資料庫統計時發生錯誤: {str(e)}")
            
    async def start(self):
        """啟動應用"""
        if self.running:
            self.logger.warning("應用已經在運行中")
            return
            
        if not await self.initialize():
            self.logger.error("初始化失敗，無法啟動應用")
            return
            
        self.running = True
        self.logger.info("========== 啟動 ThreadsPoster 應用 ==========")
        
        # 輸出初始資料庫統計
        await self._output_db_stats()
        
        try:
            # 啟動監控器
            await self.monitor.start()
        except Exception as e:
            self.logger.error(f"啟動監控器時發生錯誤: {str(e)}")
        finally:
            self.running = False
            await self.shutdown()
    
    async def shutdown(self):
        """關閉應用"""
        self.logger.info("========== 關閉 ThreadsPoster 應用 ==========")
        self.running = False
        
        # 關閉監控器
        if self.monitor:
            await self.monitor.stop()
            
        # 關閉性能監控器
        performance_monitor.shutdown()
        
        # 關閉資料庫連接
        if self.db_handler:
            # 輸出最終資料庫統計
            await self._output_db_stats()
            await self.db_handler.close()
            
        self.logger.info("ThreadsPoster 已關閉")
        
    def handle_exit(self, sig, frame):
        """處理退出信號"""
        self.logger.info(f"接收到信號 {sig}，準備退出")
        self.running = False
        loop = asyncio.get_event_loop()
        loop.create_task(self.shutdown())
        
async def main():
    app = ThreadsPosterApp()
    
    # 注冊信號處理器
    signal.signal(signal.SIGINT, app.handle_exit)
    signal.signal(signal.SIGTERM, app.handle_exit)
    
    # 啟動應用
    await app.start()
    
# 主程式入口點
if __name__ == "__main__":
    try:
        # 確保日誌目錄存在
        os.makedirs("logs", exist_ok=True)
        
        # 建立並啟動事件循環
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 啟動系統
        loop.run_until_complete(main())
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