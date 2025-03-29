"""
ThreadsPoster 主程式
Version: 1.1.3
Last Updated: 2025-03-30
"""

import asyncio
import logging
from src.ai_handler import AIHandler
from src.threads_api import ThreadsAPI
from src.database import Database
from src.config import Config
from src.time_controller import TimeController

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
        self.config = Config()
        self.db = Database(self.config)
        self.ai_handler = AIHandler(self.config)
        self.threads_api = ThreadsAPI(self.config)
        self.time_controller = TimeController(str(self.config.TIMEZONE))
        
    async def initialize(self):
        """初始化系統"""
        await self.db.initialize()
        logger.info("資料庫初始化完成")
        
        # 重置每日發文計數
        today_posts = await self.db.get_today_posts_count()
        self.time_controller._daily_post_count = today_posts
        logger.info(f"重置每日發文計數，今日已發文：{today_posts}篇")
        
        # 計算下一次發文時間
        next_post_time = self.time_controller.calculate_next_post_time()
        logger.info(f"計算下一次發文時間：{next_post_time}")
        
        logger.info("系統初始化完成")
            
    async def _should_post(self) -> bool:
        """檢查是否應該發文"""
        # 檢查今日發文次數
        today_posts = await self.db.get_today_posts_count()
        max_posts = self.config.MAX_POSTS_PER_DAY
        
        # 更新時間控制器的發文計數
        self.time_controller._daily_post_count = today_posts
        
        # 使用時間控制器檢查是否應該發文
        should_post = self.time_controller.should_post(max_posts)
        
        if not should_post:
            logger.info(f"今日已發文 {today_posts} 次，達到上限 {max_posts} 次")
            return False
            
        # 檢查是否在發文時段
        if not self.time_controller.is_prime_time():
            logger.info("當前不在發文時段")
            return False
            
        return True
        
    async def run(self):
        """執行主程序"""
        try:
            await self.initialize()
            
            # 檢查是否應該發文
            if not await self._should_post():
                logger.info("本次不進行發文")
                return
            
            # 生成並發布貼文
            content, topics, sentiment = await self.ai_handler.generate_content()
            
            if content:
                logger.info(f"生成內容：{content}")
                logger.info(f"主題：{topics}")
                logger.info(f"情感分析：{sentiment}")
                
                # 發布貼文
                post_id = await self.threads_api.create_post(content)
                if post_id:
                    # 儲存文章
                    await self.db.save_article(post_id, content, topics, sentiment)
                    logger.info("發文成功")
                    
                    # 更新發文時間和統計
                    self.time_controller.update_last_post_time()
                    today_posts = await self.db.get_today_posts_count()
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
            await self.db.close()
            await self.ai_handler.close()
            await self.threads_api.close()
            logger.info("系統正常關閉")

async def main():
    """主函數"""
    poster = ThreadsPoster()
    await poster.run()

if __name__ == "__main__":
    asyncio.run(main()) 