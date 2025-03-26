"""
ThreadsPoster 主程式
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
import pytz
from src.config import Config
from src.database import Database
from src.threads_api import ThreadsAPI
from src.ai_handler import AIHandler
from src.exceptions import ConfigError, DatabaseError, ThreadsAPIError

class ThreadsPoster:
    """ThreadsPoster 類別，處理貼文和回覆的主要邏輯"""
    
    def __init__(self, config: Config):
        """初始化 ThreadsPoster
        
        Args:
            config: 設定物件
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.db = Database(config)
        self.api = ThreadsAPI(config)
        self.ai = AIHandler(config)
        
    async def check_reply_time(self, post_time: datetime) -> bool:
        """檢查是否應該回覆
        
        Args:
            post_time: 貼文時間
            
        Returns:
            bool: 是否應該回覆
        """
        current_time = datetime.now(self.config.TIMEZONE)
        
        # 確保 post_time 有時區資訊
        if post_time.tzinfo is None:
            post_time = self.config.TIMEZONE.localize(post_time)
        
        hour = current_time.hour
        
        # 深夜時間 (23:00-06:00) 延遲回覆
        if 23 <= hour or hour < 6:
            delay = self.get_reply_delay("night")
        else:
            delay = self.get_reply_delay("day")
            
        time_diff = (current_time - post_time).total_seconds()
        return time_diff >= delay
        
    def get_reply_delay(self, time_period: str) -> int:
        """獲取回覆延遲時間
        
        Args:
            time_period: 時間段 (day/night)
            
        Returns:
            int: 延遲秒數
        """
        if time_period == "night":
            return 300  # 深夜 5 分鐘
        return 60  # 白天 1 分鐘
        
    async def process_new_replies(self, replies):
        """處理新回覆
        
        Args:
            replies: 回覆列表
        """
        if not replies:
            return
            
        for reply in replies:
            try:
                # 檢查必要資料是否完整
                if not all(key in reply for key in ["user_id", "reply_text", "post_id"]):
                    self.logger.warning(f"回覆資料不完整: {reply}")
                    continue
                    
                # 檢查是否已回覆過
                if await self.db.has_replied_to_post(reply["post_id"]):
                    continue
                    
                # 檢查回覆時間
                post_time = datetime.fromisoformat(reply["created_at"])
                if not await self.check_reply_time(post_time):
                    continue
                    
                # 獲取用戶對話歷史
                conversation_history = await self.db.get_user_conversation_history(reply["user_id"])
                
                # 生成回覆
                response = await self.ai.generate_reply(
                    reply["reply_text"],
                    conversation_history
                )
                
                # 嘗試發送回覆，最多重試 3 次
                max_retries = 3
                retry_delay = 5  # 秒
                success = False
                
                for attempt in range(max_retries):
                    try:
                        success = await self.api.reply_to_post(
                            reply["post_id"],
                            response
                        )
                        if success:
                            break
                        await asyncio.sleep(retry_delay)
                    except Exception as e:
                        self.logger.error(f"第 {attempt + 1} 次嘗試回覆失敗: {str(e)}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay)
                            
                if success:
                    # 儲存對話記錄
                    await self.db.save_conversation(
                        reply["user_id"],
                        reply["reply_text"],
                        response
                    )
                    
                    # 儲存回覆記錄
                    await self.db.save_reply({
                        "post_id": reply["post_id"],
                        "user_id": reply["user_id"],
                        "content": response,
                        "reference_id": reply["post_id"]
                    })
                    
            except Exception as e:
                import traceback
                self.logger.error(f"處理回覆時發生錯誤: {str(e)}\n{traceback.format_exc()}")
                
    async def generate_new_post(self):
        """生成新貼文"""
        try:
            # 檢查是否需要發新貼文
            last_post_time = await self.db.get_last_post_time()
            current_time = datetime.now(self.config.TIMEZONE)
            
            # 如果沒有上次發文時間，或距離上次發文超過 6 小時，則發文
            if last_post_time is None or (current_time - last_post_time).total_seconds() >= 21600:  # 6 小時 = 21600 秒
                # 生成新貼文內容
                post_content = await self.ai.generate_post()
                
                # 發布貼文
                post_id = await self.api.create_post(post_content)
                
                if post_id:
                    # 更新最後發文時間
                    await self.db.update_last_post_time(current_time)
                    
                    # 儲存貼文記錄
                    await self.db.save_post(
                        post_id=post_id,
                        content=post_content,
                        post_type="post"
                    )
                    
        except Exception as e:
            self.logger.error(f"生成新貼文時發生錯誤: {str(e)}")
            
    async def run(self):
        """執行主要邏輯"""
        try:
            while True:  # 持續運行
                try:
                    # 檢查新回覆
                    last_check_time = await self.db.get_last_check_time()
                    current_time = datetime.now(self.config.TIMEZONE)
                    
                    # 獲取新回覆
                    replies = await self.api.get_new_replies(last_check_time)
                    
                    # 處理回覆
                    await self.process_new_replies(replies)
                    
                    # 更新最後檢查時間
                    await self.db.update_last_check_time(current_time)
                    
                    # 生成新貼文
                    await self.generate_new_post()
                    
                    # 等待一段時間再進行下一次檢查
                    await asyncio.sleep(30)  # 每 30 秒檢查一次
                    
                except Exception as e:
                    self.logger.error(f"執行主要邏輯時發生錯誤: {str(e)}")
                    await asyncio.sleep(60)  # 發生錯誤時等待 1 分鐘再重試
                    
        except KeyboardInterrupt:
            self.logger.info("程式收到中斷信號，正在結束...")
            
def setup_logging(config: Config):
    """設置日誌
    
    Args:
        config: 設定物件
    """
    logging.basicConfig(
        level=config.LOG_LEVEL,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
async def main():
    """主程式"""
    try:
        # 載入設定
        config = Config()
        config.load_env()
        config.validate()
        
        # 設置日誌
        setup_logging(config)
        logger = logging.getLogger(__name__)
        logger.info("ThreadsPoster 開始運行")
        
        # 初始化 ThreadsPoster
        poster = ThreadsPoster(config)
        
        # 執行主要邏輯
        await poster.run()
        
    except ConfigError as e:
        logger.error(f"設定錯誤: {str(e)}")
        sys.exit(1)
    except DatabaseError as e:
        logger.error(f"資料庫錯誤: {str(e)}")
        sys.exit(1)
    except ThreadsAPIError as e:
        logger.error(f"Threads API 錯誤: {str(e)}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("程式被使用者中斷")
        sys.exit(0)
    except Exception as e:
        logger.error(f"未預期的錯誤: {str(e)}")
        sys.exit(1)
        
if __name__ == "__main__":
    asyncio.run(main()) 