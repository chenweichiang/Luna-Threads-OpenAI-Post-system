"""
ThreadsPoster 主程式
整合所有組件並控制系統運行
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from contextlib import asynccontextmanager

from src.config import Config
from src.database import Database
from src.threads_api import ThreadsAPI
from src.ai_handler import AIHandler

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('threads_poster.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

class ThreadsPoster:
    """ThreadsPoster 系統主類"""
    
    def __init__(self):
        """初始化 ThreadsPoster 系統"""
        self.config = Config()
        self.db = Database(self.config)
        self.threads_api = ThreadsAPI(self.config)
        self.ai_handler = AIHandler(self.config)
        self._shutdown = False
        self.tasks = []
        self.max_retries = 3
        self._content_cache = {}  # 新增內容快取
        self._last_cleanup = datetime.now()
        self._post_cooldown = {}  # 新增發文冷卻時間追蹤

    async def initialize(self):
        """初始化系統組件"""
        try:
            # 並行初始化所有組件
            init_tasks = [
                self.db.init_db(),
                self.threads_api.initialize(),
                self._init_cache()
            ]
            await asyncio.gather(*init_tasks)
            logger.info("系統初始化完成")
            return True
        except Exception as e:
            logger.error(f"系統初始化失敗: {str(e)}")
            return False

    async def _init_cache(self):
        """初始化快取"""
        try:
            # 預載入常用數據
            self._content_cache['topics'] = await self.db.get_recent_topics(limit=50)
            self._content_cache['last_posts'] = await self.db.get_recent_posts(limit=20)
            logger.info("快取初始化完成")
        except Exception as e:
            logger.error(f"快取初始化失敗: {str(e)}")

    async def _update_cache(self):
        """更新快取數據"""
        try:
            current_time = datetime.now()
            # 每小時更新一次快取
            if (current_time - self._last_cleanup).total_seconds() > 3600:
                self._content_cache['topics'] = await self.db.get_recent_topics(limit=50)
                self._content_cache['last_posts'] = await self.db.get_recent_posts(limit=20)
                self._last_cleanup = current_time
                logger.info("快取更新完成")
        except Exception as e:
            logger.error(f"快取更新失敗: {str(e)}")

    async def _post_article_task(self):
        """定時發文任務"""
        while not self._shutdown:
            try:
                current_time = datetime.now(self.config.TIMEZONE)
                current_hour = current_time.hour
                
                # 檢查發文冷卻時間
                if self._post_cooldown.get(current_hour):
                    time_diff = (current_time - self._post_cooldown[current_hour]).total_seconds()
                    if time_diff < 1800:  # 30分鐘冷卻時間
                        await asyncio.sleep(300)
                        continue

                # 檢查是否在深夜時段（23:00-06:00）
                if 23 <= current_hour or current_hour < 6:
                    logger.info("深夜時段，暫停發文")
                    await asyncio.sleep(3600)
                    continue
                
                # 檢查今日發文數量（使用快取）
                if 'today_posts_count' not in self._content_cache or \
                   (current_time - self._content_cache.get('today_posts_time', current_time)).total_seconds() > 300:
                    self._content_cache['today_posts_count'] = await self.db.get_today_posts_count()
                    self._content_cache['today_posts_time'] = current_time

                if self._content_cache['today_posts_count'] >= self.config.SYSTEM_CONFIG['max_daily_posts']:
                    logger.info("已達到今日發文上限")
                    await asyncio.sleep(3600)
                    continue
                
                # 動態調整發文間隔
                post_interval = self._get_dynamic_interval(current_hour)
                
                # 使用快取的主題建議
                suggested_topics = self._content_cache.get('topics', [])
                if not suggested_topics:
                    suggested_topics = await self.db.get_topic_suggestions()
                    self._content_cache['topics'] = suggested_topics
                
                # 生成和發布文章
                content = await self._generate_and_validate_content(suggested_topics)
                if content:
                    success = await self._publish_content(content)
                    if success:
                        self._post_cooldown[current_hour] = current_time
                        await self._update_cache()
                        await asyncio.sleep(post_interval)
                    else:
                        await asyncio.sleep(300)
                else:
                    await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"發文任務執行失敗: {str(e)}")
                await asyncio.sleep(300)

    def _get_dynamic_interval(self, hour: int) -> int:
        """根據時間動態計算發文間隔"""
        if 6 <= hour < 9:  # 早上
            return 1800  # 30分鐘
        elif (12 <= hour < 14) or (17 <= hour < 19):  # 午餐和晚餐時間
            return 2700  # 45分鐘
        else:
            return 3600  # 1小時

    async def _generate_and_validate_content(self, suggested_topics: list) -> str:
        """生成並驗證文章內容"""
        for _ in range(self.max_retries):
            try:
                content = await self.ai_handler.generate_post(suggested_topics)
                if not content or len(content.strip()) < 10:
                    continue
                    
                # 使用快取檢查相似度
                if await self._is_content_similar(content):
                    continue
                    
                if not any(emoji in content for emoji in ['😊', '🥰', '✨', '💕', '🎮', '📱', '💻', '🎨', '🎧', '🤖', '🙈', '💫', '🎬']):
                    continue
                    
                return content
                
            except Exception as e:
                logger.error(f"生成內容時發生錯誤: {str(e)}")
                await asyncio.sleep(5)
                
        return None

    async def _is_content_similar(self, content: str) -> bool:
        """使用快取檢查內容相似度"""
        try:
            recent_posts = self._content_cache.get('last_posts', [])
            if not recent_posts:
                return await self.db.is_content_similar(content)
                
            # 簡單的文本相似度檢查
            content_words = set(content.split())
            for post in recent_posts:
                post_words = set(post['content'].split())
                similarity = len(content_words & post_words) / len(content_words | post_words)
                if similarity > 0.6:  # 60% 相似度閾值
                    return True
            return False
        except Exception as e:
            logger.error(f"相似度檢查失敗: {str(e)}")
            return False

    async def _publish_content(self, content: str) -> bool:
        """發布文章內容"""
        try:
            post_id = await self.threads_api.create_post(content)
            if post_id:
                # 並行執行儲存操作
                save_tasks = [
                    self.db.save_post(post_id, content),
                    self._update_post_stats(post_id, content)
                ]
                await asyncio.gather(*save_tasks)
                logger.info(f"成功發布文章，ID: {post_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"發布文章失敗: {str(e)}")
            return False

    async def _update_post_stats(self, post_id: str, content: str):
        """更新發文統計"""
        try:
            self._content_cache['today_posts_count'] = self._content_cache.get('today_posts_count', 0) + 1
            if 'last_posts' in self._content_cache:
                self._content_cache['last_posts'].insert(0, {'id': post_id, 'content': content})
                self._content_cache['last_posts'] = self._content_cache['last_posts'][:20]
        except Exception as e:
            logger.error(f"更新統計資料失敗: {str(e)}")

    async def _cleanup_task(self):
        """清理任務"""
        while not self._shutdown:
            try:
                # 清理過期數據
                await self.db.cleanup_old_records(
                    days=self.config.MEMORY_CONFIG['retention_days']
                )
                # 清理快取
                await self.db.cleanup_cache()
                logger.info("完成數據清理")
                
                # 每24小時執行一次
                await asyncio.sleep(86400)
                
            except Exception as e:
                logger.error(f"清理任務執行失敗: {str(e)}")
                await asyncio.sleep(3600)

    def _handle_shutdown(self, signum, frame):
        """處理關閉信號"""
        logger.info("接收到關閉信號，準備關閉系統...")
        self._shutdown = True

    async def start(self):
        """啟動系統"""
        try:
            # 初始化系統
            if not await self.initialize():
                logger.error("系統初始化失敗，無法啟動")
                return
            
            # 設置關閉信號處理
            signal.signal(signal.SIGINT, self._handle_shutdown)
            signal.signal(signal.SIGTERM, self._handle_shutdown)
            
            # 只啟動發文和清理任務
            self.tasks = [
                asyncio.create_task(self._post_article_task()),
                asyncio.create_task(self._cleanup_task())
            ]
            
            logger.info("ThreadsPoster 系統已啟動（僅發文模式）")
            
            # 等待任務完成或系統關閉
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"系統運行時發生錯誤: {str(e)}")
        finally:
            # 清理資源
            for task in self.tasks:
                task.cancel()
            await self.ai_handler.close()
            await self.db.close()
            logger.info("系統已關閉")

@asynccontextmanager
async def get_threads_poster():
    """獲取 ThreadsPoster 實例的上下文管理器"""
    poster = ThreadsPoster()
    try:
        yield poster
    finally:
        await poster.ai_handler.close()
        await poster.db.close()

async def main():
    """主程式入口"""
    try:
        async with get_threads_poster() as poster:
            await poster.start()
    except Exception as e:
        logger.error(f"主程式執行失敗: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 