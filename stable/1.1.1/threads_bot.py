import logging
import random
import time
from datetime import datetime
import pytz
from typing import Dict, List, Optional

from config import Config
from database import Database
from ai_handler import AIHandler
from threads_api import ThreadsAPI
from utils import get_current_time, sanitize_text

logger = logging.getLogger(__name__)

class ThreadsBot:
    def __init__(self):
        """初始化 ThreadsBot"""
        try:
            # 初始化設定
            self.config = Config()
            
            # 初始化組件
            self.db = Database(self.config)
            self.ai = AIHandler(self.config)
            self.api = ThreadsAPI(self.config)
            
            # 設定時區
            self.timezone = pytz.timezone(self.config.TIMEZONE)
            self.last_check_time = get_current_time()
            
            logger.info("ThreadsBot 初始化成功")
        except Exception as e:
            logger.error(f"ThreadsBot 初始化失敗: {str(e)}")
            raise

    def check_new_replies(self) -> List[Dict]:
        """檢查新回覆"""
        try:
            logger.info("檢查新回覆...")
            new_replies = self.api.get_new_replies(self.last_check_time)
            self.last_check_time = get_current_time()
            return new_replies
        except Exception as e:
            logger.error(f"檢查新回覆時發生錯誤: {str(e)}")
            return []

    def create_post(self, content: str) -> bool:
        """發布新貼文"""
        try:
            logger.info(f"發布新貼文: {content}")
            sanitized_content = sanitize_text(content)
            post_data = self.api.create_post(sanitized_content)
            
            if post_data:
                self.db.save_post(post_data['id'], sanitized_content, 'post')
                logger.info("貼文發布成功")
                return True
            return False
        except Exception as e:
            logger.error(f"發布貼文時發生錯誤: {str(e)}")
            return False

    def reply_to_post(self, post_id: str, content: str) -> bool:
        """回覆貼文"""
        try:
            logger.info(f"回覆貼文 {post_id}: {content}")
            sanitized_content = sanitize_text(content)
            reply_data = self.api.reply_to_post(post_id, sanitized_content)
            
            if reply_data:
                self.db.save_post(reply_data['id'], sanitized_content, 'reply', post_id)
                logger.info("回覆發布成功")
                return True
            return False
        except Exception as e:
            logger.error(f"回覆貼文時發生錯誤: {str(e)}")
            return False

    def generate_post_content(self) -> Optional[str]:
        """生成貼文內容"""
        try:
            recent_posts = self.db.get_post_history(5)
            current_hour = datetime.now(self.timezone).hour
            return self.ai.generate_new_post(recent_posts, current_hour)
        except Exception as e:
            logger.error(f"生成貼文內容時發生錯誤: {str(e)}")
            return None

    def generate_response(self, message: str, user_id: str) -> Optional[str]:
        """生成回覆內容"""
        try:
            # 獲取用戶互動摘要
            user_summary = self.db.get_user_interaction_summary(user_id)
            
            # 獲取對話歷史
            history = self.db.get_user_conversation_history(user_id)
            
            # 生成回覆
            response = self.ai.generate_response(message, history, user_summary)
            
            if response:
                # 保存對話記錄
                self.db.save_conversation(user_id, message, response)
            
            return response
        except Exception as e:
            logger.error(f"生成回覆內容時發生錯誤: {str(e)}")
            return None

    def _get_current_mood(self) -> str:
        """獲取當前心情"""
        try:
            moods = list(self.config.MOOD_STATES.keys())
            weights = [0.5, 0.3, 0.2]  # happy, normal, tired 的機率
            return random.choices(moods, weights=weights)[0]
        except Exception as e:
            logger.error(f"獲取當前心情時發生錯誤: {str(e)}")
            return 'normal'

    def run(self):
        """主要運行邏輯"""
        logger.info("ThreadsBot 開始運行...")
        
        while True:
            try:
                # 更新心情
                self.current_mood = self._get_current_mood()
                
                # 檢查是否需要發布新貼文
                if self._should_post_now():
                    content = self.generate_post_content()
                    if content:
                        if self.create_post(content):
                            logger.info(f"已發布新貼文：{content}")

                # 檢查新回覆
                new_replies = self.check_new_replies()
                
                for reply in new_replies:
                    reply_id = reply["id"]
                    user_id = reply["from"]["id"]
                    reply_text = reply["text"]

                    # 生成回覆
                    response_text = self.generate_response(reply_text, user_id)

                    # 發送回覆
                    if self.reply_to_post(reply_id, response_text):
                        logger.info(f"已回覆：{response_text}")

                # 休息一段時間
                time.sleep(self.config.CHECK_INTERVAL)
                
            except Exception as e:
                logger.error("運行時發生錯誤", e)
                time.sleep(self.config.RETRY_INTERVAL)

if __name__ == "__main__":
    bot = ThreadsBot()
    bot.run() 