"""
Version: 2024.03.30
Author: ThreadsPoster Team
Description: 主程式入口，負責初始化和啟動所有服務
Last Modified: 2024.03.30
Changes:
- 優化初始化流程
- 加入人設記憶系統初始化
- 改進錯誤處理機制
"""

import asyncio
import logging
import os
from src.ai_handler import AIHandler
from src.threads_api import ThreadsAPI
from src.database import Database
from src.config import Config
from src.time_controller import TimeController
from src.db_handler import DBHandler
from src.threads_handler import ThreadsHandler

# 設定基本的日誌格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class ThreadsPoster:
    """ThreadsPoster 主類"""
    
    def __init__(self):
        """初始化 ThreadsPoster"""
        # 載入配置
        self.config = Config()
        
        # 初始化各個控制器
        self.time_controller = TimeController(self.config)
        self.db_handler = DBHandler(self.config)
        self.ai_handler = AIHandler(self.config)
        self.threads_handler = ThreadsHandler(self.config)
        
        # 設定日誌
        self._setup_logging()
        
        # 初始化狀態
        self.is_running = False
        self.current_post_id = None
        self.current_post_content = None
        
    def _setup_logging(self):
        """設定日誌系統"""
        # 確保日誌目錄存在
        log_dir = os.path.dirname(self.config.LOG_PATH)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # 設定日誌格式
        log_file = os.path.join(log_dir, 'threads_poster.log')
        logging.basicConfig(
            level=getattr(logging, self.config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        # 設定根日誌器
        logger.setLevel(getattr(logging, self.config.LOG_LEVEL))
        
    async def initialize(self):
        """初始化系統"""
        # 初始化資料庫
        await self.db_handler.initialize()
        logger.info("資料庫初始化完成")
        
        # 初始化 AI 處理器
        await self.ai_handler.initialize(self.db_handler.database)
        logger.info("AI 處理器初始化完成")
        
        # 重置每日發文計數
        await self.db_handler.reset_today_posts()
        today_posts = await self.db_handler.get_today_posts_count()
        self.time_controller._daily_post_count = today_posts
        logger.info(f"重置每日發文計數，今日已發文：{today_posts}篇")
        
        # 計算下一次發文時間
        next_post_time = self.time_controller.calculate_next_post_time()
        logger.info(f"計算下一次發文時間：{next_post_time}")
        
        logger.info("系統初始化完成")
            
    async def should_post(self) -> bool:
        """檢查是否應該發文"""
        # 檢查今日發文次數
        today_posts = await self.db_handler.get_today_posts_count()
        max_posts = self.config.MAX_POSTS_PER_DAY
        
        # 更新時間控制器的發文計數
        self.time_controller._daily_post_count = today_posts
        
        # 檢查是否應該發文
        return self.time_controller.should_post()
        
    async def run(self):
        """執行主程序"""
        try:
            await self.initialize()
            
            # 檢查是否應該發文
            if not await self.should_post():
                logger.info("本次不進行發文")
                return
            
            # 生成並發布貼文
            content, topics, sentiment = await self.ai_handler.generate_content()
            
            if content:
                logger.info(f"生成內容：{content}")
                logger.info(f"主題：{topics}")
                logger.info(f"情感分析：{sentiment}")
                
                # 發布貼文
                post_id = await self.threads_handler.create_post(content)
                if post_id:
                    # 儲存文章
                    await self.db_handler.save_article(post_id, content, topics, sentiment)
                    logger.info("發文成功")
                    
                    # 更新發文時間和統計
                    self.time_controller.update_last_post_time()
                    today_posts = await self.db_handler.get_today_posts_count()
                    current_time = self.time_controller.get_current_time()
                    is_prime_time = self.time_controller.is_prime_time()
                    logger.info(f"本次發文時間：{current_time.strftime('%Y-%m-%d %H:%M:%S')}，"
                             f"今日已發文：{today_posts} 篇，"
                             f"是否為主要時段：{'是' if is_prime_time else '否'}")
                else:
                    logger.error("發布貼文失敗")
            else:
                logger.error("生成內容失敗")
                
        except Exception as e:
            logger.error(f"執行過程中發生錯誤：{str(e)}")
        finally:
            # 關閉資源
            await self.db_handler.close()
            await self.ai_handler.close()
            await self.threads_handler.close()
            logger.info("系統正常關閉")

async def main():
    """主函數"""
    poster = ThreadsPoster()
    await poster.run()

if __name__ == "__main__":
    asyncio.run(main()) 