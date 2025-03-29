"""
ThreadsPoster 主程式
Version: 1.1.2
Last Updated: 2025-03-30
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
import pytz
from src.ai_handler import AIHandler
from src.threads_api import ThreadsAPI
from src.database import Database
from src.config import Config
import argparse

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
        try:
            self.timezone = pytz.timezone(str(self.config.TIMEZONE))
        except Exception as e:
            logger.error(f"時區設定錯誤：{str(e)}，使用預設時區 Asia/Taipei")
            self.timezone = pytz.timezone('Asia/Taipei')
        
    async def initialize(self):
        """初始化系統"""
        await self.db.initialize()
        logger.info("資料庫初始化完成")
        
        # 重置每日發文計數
        today_posts = await self.db.get_today_posts_count()
        logger.info(f"重置每日發文計數，今日已發文：{today_posts}篇")
        
        # 計算下一次發文時間
        next_post_time = self._calculate_next_post_time()
        logger.info(f"計算下一次發文時間：{next_post_time}")
        
        logger.info("系統初始化完成")
        
    def _calculate_next_post_time(self) -> datetime:
        """計算下一次發文時間"""
        now = datetime.now(self.timezone)
        current_hour = now.hour
        
        # 如果當前時間在凌晨2點之後，下一次發文時間應該在晚上8點之後
        if 2 < current_hour < 20:
            next_time = now.replace(hour=20, minute=0, second=0, microsecond=0)
            # 加上隨機延遲（0-60分鐘）
            delay_minutes = random.randint(0, 60)
            next_time += timedelta(minutes=delay_minutes)
        else:
            # 在發文時段內，生成30-90分鐘的隨機延遲
            delay_minutes = random.randint(30, 90)
            next_time = now + timedelta(minutes=delay_minutes)
            
            # 確保不會超過凌晨2點
            if next_time.hour > 2 and next_time.hour < 20:
                next_time = next_time.replace(hour=20, minute=0, second=0, microsecond=0)
                delay_minutes = random.randint(0, 60)
                next_time += timedelta(minutes=delay_minutes)
        
        return next_time
        
    def _is_posting_time(self) -> bool:
        """檢查是否在發文時段"""
        now = datetime.now(self.timezone)
        current_hour = now.hour
        
        # 主要發文時段：20:00-02:00
        prime_time = 20 <= current_hour <= 23 or 0 <= current_hour <= 2
        
        if prime_time:
            # 主要時段：70% 發文機率
            should_post = random.random() < self.config.PRIME_TIME_POST_RATIO
            if should_post:
                logger.info("當前為主要發文時段")
            return should_post
        else:
            # 非主要時段：30% 發文機率
            should_post = random.random() < (1 - self.config.PRIME_TIME_POST_RATIO)
            if should_post:
                logger.info("當前為非主要發文時段")
            return should_post
            
    async def _should_post(self) -> bool:
        """檢查是否應該發文"""
        # 檢查今日發文次數
        today_posts = await self.db.get_today_posts_count()
        max_posts = random.randint(
            self.config.MIN_POSTS_PER_DAY,
            self.config.MAX_POSTS_PER_DAY
        )
        
        if today_posts >= max_posts:
            logger.info(f"今日已發文 {today_posts} 次，達到上限 {max_posts} 次")
            return False
            
        # 檢查是否在發文時段
        if not self._is_posting_time():
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
                    
                    # 記錄發文時間和統計
                    now = datetime.now(self.timezone)
                    today_posts = await self.db.get_today_posts_count()
                    is_prime_time = 20 <= now.hour <= 23 or 0 <= now.hour <= 2
                    logger.info(f"本次發文時間：{now.strftime('%Y-%m-%d %H:%M:%S')}，"
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