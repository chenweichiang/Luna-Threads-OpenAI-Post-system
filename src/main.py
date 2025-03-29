"""
ThreadsPoster 主程式
整合所有組件並控制系統運行
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import List, Dict
import pytz

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
    """Threads 自動發文系統"""
    
    def __init__(self, config: Config):
        """初始化 Threads 發文系統
        
        Args:
            config: 設定物件
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.timezone = pytz.timezone("Asia/Taipei")  # 直接使用固定時區
        self.api_client = None
        self.db = None
        self.ai_handler = None
        self._is_shutting_down = False
        self._shutdown_flag = False
        
    async def initialize(self):
        """初始化系統組件"""
        try:
            # 初始化 API 客戶端
            self.api_client = ThreadsAPI(self.config)
            
            # 初始化資料庫
            self.db = Database(self.config)
            await self.db.init_db()
            
            # 初始化 AI 處理器
            self.ai_handler = AIHandler(self.config)
            
            self.logger.info("系統初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"系統初始化失敗：{str(e)}")
            return False
            
    async def _shutdown(self):
        """關閉系統，確保資源正確釋放"""
        if self._is_shutting_down:
            return
            
        try:
            self._is_shutting_down = True
            
            # 關閉 API 客戶端
            if self.api_client:
                await self.api_client.close()
                self.api_client = None
                
            # 關閉資料庫連接
            if self.db:
                await self.db.close()
                self.db = None
                
            # 關閉 AI 處理器
            if self.ai_handler:
                await self.ai_handler.close()
                self.ai_handler = None
                
            self.logger.info("系統正常關閉")
            
        except Exception as e:
            self.logger.error(f"系統關閉時發生錯誤: {e}")
        finally:
            self._is_shutting_down = False
            
    async def _post_article(self, content: str, topics: List[str], sentiment: Dict[str, float]) -> bool:
        """發布文章
        
        Args:
            content: 文章內容
            topics: 文章主題列表
            sentiment: 情感分析結果
            
        Returns:
            bool: 是否發布成功
        """
        try:
            # 發布文章
            post_id = await self.api_client.create_post(content)
            if not post_id:
                self.logger.error("文章發布失敗")
                return False
                
            # 儲存到資料庫
            if await self.db.save_post(post_id, content, topics, sentiment):
                # 驗證文章是否成功儲存
                saved_post = await self.db.get_post(post_id)
                if not saved_post:
                    self.logger.error("無法從資料庫讀取已儲存的文章")
                    return False
                    
                if saved_post["content"] != content:
                    self.logger.error("儲存的文章內容與原始內容不符")
                    return False
                    
                self.logger.info(f"成功發布文章並寫入資料庫，ID: {post_id}")
                return True
            else:
                self.logger.error("文章儲存失敗")
                return False
                
        except Exception as e:
            self.logger.error(f"發布文章時發生錯誤：{str(e)}")
            return False
            
    async def _post_article_task(self):
        """執行發文任務"""
        try:
            # 檢查是否達到每日發文上限
            if await self.db.check_daily_post_limit():
                self.logger.warning("已達到每日發文上限")
                return
                
            # 生成文章內容
            content, topics, sentiment = await self.ai_handler.generate_content()
            
            # 發布文章
            success = await self._post_article(content, topics, sentiment)
            if success:
                self.logger.info("發文成功，系統正常關閉")
            else:
                self.logger.error("發文失敗")
                
        except Exception as e:
            self.logger.error(f"發文任務執行失敗: {e}")
            raise
            
    async def run(self):
        """運行系統"""
        try:
            # 初始化系統
            if not await self.initialize():
                return False
                
            self.logger.info("系統啟動完成，開始發文流程")
            
            # 註冊信號處理
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(self._handle_signal(s)))
                
            # 執行發文任務
            await self._post_article_task()
            
            # 正常關閉
            await self._shutdown()
            return True
            
        except Exception as e:
            self.logger.error(f"系統運行時發生錯誤: {e}")
            await self._shutdown()
            return False
            
    async def _handle_signal(self, sig):
        """處理系統信號"""
        self.logger.info(f"收到信號 {sig.name}，準備關閉系統")
        self._shutdown_flag = True
        
async def main():
    """主程式進入點"""
    is_test = "--test" in sys.argv
    poster = None
    
    try:
        # 初始化設定
        config = Config()
        
        # 設定日誌
        logging.basicConfig(
            level=config.SYSTEM_CONFIG["log_level"],
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 初始化系統
        poster = ThreadsPoster(config)
        await poster.initialize()
        
        # 如果是測試模式，清除今日的貼文記錄
        if is_test:
            await poster.db.clear_today_posts()
        
        # 運行系統
        success = await poster.run()
        if not success:
            sys.exit(1)
            
    except Exception as e:
        logging.error(f"系統運行時發生錯誤：{str(e)}")
        sys.exit(1)
    finally:
        if poster:
            await poster._shutdown()

if __name__ == "__main__":
    asyncio.run(main()) 