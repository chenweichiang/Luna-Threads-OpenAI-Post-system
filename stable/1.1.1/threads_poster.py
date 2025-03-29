"""
ThreadsPoster - Threads 自動回覆與內容發布系統
"""

import logging
import time
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Any
import random
from pathlib import Path
import asyncio
import pytz

from src.config import Config
from src.threads_api import ThreadsAPI
from src.ai_handler import AIHandler
from src.database import Database

class ThreadsPoster:
    """Threads 自動發文系統"""
    
    def __init__(self, config_path: str = "config/character_config.json"):
        """初始化 ThreadsPoster"""
        self.config = self._load_config(config_path)
        self.ai_handler = AIHandler()
        self.threads_api = ThreadsAPI()
        self.db = Database()
        self.last_post_time = datetime.now(pytz.UTC) - timedelta(hours=24)
        self._test_mode = False
        self.logger = logging.getLogger(__name__)
        self.user_info = None
        self.memory_file = Path("data/memory.json")
        self.memory = self._load_memory()
        
        # 設定日誌
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("logs/threads_poster.log"),
                logging.StreamHandler()
            ]
        )
        
    def _load_config(self, config_path: str) -> dict:
        """載入配置檔案"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"載入配置檔案失敗：{str(e)}")
            return {}
        
    def _load_memory(self) -> Dict:
        """載入記憶檔案"""
        if self.memory_file.exists():
            with open(self.memory_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"users": {}, "posts": {}, "replies": {}}
        
    def _save_memory(self):
        """儲存記憶檔案"""
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, ensure_ascii=False, indent=2)
            
    def _update_user_memory(self, username: str, interaction: Dict):
        """更新用戶互動記憶

        Args:
            username (str): 用戶名稱
            interaction (Dict): 互動資訊
        """
        if username not in self.memory["users"]:
            self.memory["users"][username] = {
                "first_interaction": datetime.now().isoformat(),
                "interactions": []
            }
        
        self.memory["users"][username]["interactions"].append({
            "timestamp": datetime.now().isoformat(),
            **interaction
        })
        self._save_memory()
        
    async def initialize(self):
        """初始化系統"""
        await self.db.connect()
        self.logger.info("系統初始化完成")
        
        # 檢查用戶權限
        self.user_info = await self.threads_api.get_user_info()
        if not self.user_info:
            self.logger.error("無法獲取用戶資訊")
            return False
            
        self.logger.info(f"用戶名稱: {self.user_info.get('username')}")
        self.logger.info(f"用戶 ID: {self.user_info.get('id')}")
        
        # 檢查發布限制
        limit_info = await self.threads_api.get_publishing_limit()
        if not limit_info:
            self.logger.error("無法獲取發布限制資訊")
            return False
            
        self.logger.info(f"已使用 {limit_info.get('quota_usage', 0)} / {limit_info.get('quota_total', 0)} 則貼文")
        return True
        
    async def _should_reply_now(self) -> bool:
        """判斷是否應該回覆"""
        current_hour = datetime.now().hour
        
        # 深夜時間（0-6點）降低回覆機率
        if 0 <= current_hour < 6:
            return random.random() < 0.2  # 20% 機率回覆
        
        return random.random() < 0.8  # 80% 機率回覆
        
    async def _generate_reply(self, username: str, message: str) -> str:
        """生成回覆內容"""
        # 獲取用戶歷史對話
        history = await self.db.get_user_conversation_history(username)
        
        # 生成回覆
        reply = await self.ai_handler.generate_response(message, history)
        
        # 更新對話歷史
        await self.db.update_user_history(username, message, reply)
        
        return reply
        
    async def process_new_replies(self):
        """處理新的回覆"""
        try:
            self.logger.info("正在獲取新回覆")
            replies = await self.threads_api.get_new_replies()
            
            if not replies:
                self.logger.info("沒有新的回覆")
                return
            
            for reply in replies:
                if not await self._should_reply_now():
                    self.logger.info(f"決定不回覆 {reply['username']} 的訊息")
                    continue
                
                response = await self._generate_reply(reply['username'], reply['text'])
                if response:
                    success = await self.threads_api.reply_to_post(reply['id'], response)
                    if success:
                        self.logger.info(f"成功回覆 {reply['username']}")
                    else:
                        self.logger.error(f"回覆 {reply['username']} 失敗")
        
        except Exception as e:
            self.logger.error(f"處理回覆時發生錯誤：{str(e)}")
            if not self._test_mode:
                raise
        
    async def generate_new_post(self):
        """生成並發布新貼文"""
        try:
            # 檢查是否應該發布新貼文
            time_since_last_post = (datetime.now(pytz.UTC) - self.last_post_time).total_seconds() / 3600
            
            if time_since_last_post < self.config.POST_INTERVAL_HOURS:
                return
            
            content = await self.ai_handler.generate_new_post()
            if not content:
                return
            
            max_retries = 3
            retry_delay = 5
            
            for attempt in range(max_retries):
                if await self.threads_api.create_post(content):
                    self.last_post_time = datetime.now(pytz.UTC)
                    self.logger.info("成功發布新貼文")
                    return
                
                if attempt < max_retries - 1:
                    retry_delay *= 2
                    self.logger.warning(f"發布失敗，{retry_delay} 秒後重試")
                    await asyncio.sleep(retry_delay)
            
            self.logger.error("發布新貼文失敗，已達最大重試次數")
        
        except Exception as e:
            self.logger.error(f"生成新貼文時發生錯誤：{str(e)}")
            if not self._test_mode:
                raise
        
    async def run(self):
        """執行主程序"""
        try:
            await self.initialize()
            
            while True:
                await self.process_new_replies()
                await self.generate_new_post()
                await asyncio.sleep(self.config.CHECK_INTERVAL)
        
        except Exception as e:
            self.logger.error(f"執行過程中發生錯誤：{str(e)}")
            if not self._test_mode:
                raise

if __name__ == "__main__":
    poster = ThreadsPoster()
    asyncio.run(poster.run()) 