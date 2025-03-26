"""
ThreadsPoster - Threads 自動回覆與內容發布系統
"""

import logging
import time
from datetime import datetime
import json
from typing import Dict, List, Optional, Any
import random
from pathlib import Path
import asyncio

from src.config import Config
from src.threads_api import ThreadsAPI

class ThreadsPoster:
    """Threads 自動回覆系統"""
    
    def __init__(self, config: Config):
        """初始化系統

        Args:
            config (Config): 設定檔
        """
        self.config = config
        self.api = ThreadsAPI(config)
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
        
    def _should_reply_now(self) -> bool:
        """判斷是否應該立即回覆

        Returns:
            bool: 是否應該回覆
        """
        current_hour = datetime.now().hour
        
        # 深夜時間（23:00-06:00）
        if current_hour >= 23 or current_hour < 6:
            return random.random() < 0.2  # 20% 機率回覆
            
        # 白天時間
        return random.random() < 0.8  # 80% 機率回覆
        
    def _generate_reply(self, username: str, text: str) -> str:
        """生成回覆內容

        Args:
            username (str): 用戶名稱
            text (str): 原始訊息

        Returns:
            str: 回覆內容
        """
        # 根據用戶互動歷史生成回覆
        user_history = self.memory["users"].get(username, {}).get("interactions", [])
        
        # 如果是第一次互動
        if not user_history:
            return f"你好 {username}！很高興認識你 💕"
            
        # 根據之前的互動生成回覆
        return f"謝謝你的回覆，{username}！"
        
    async def initialize(self) -> bool:
        """初始化系統

        Returns:
            bool: 是否初始化成功
        """
        # 檢查用戶權限
        self.user_info = await self.api.get_user_info()
        if not self.user_info:
            logging.error("無法獲取用戶資訊")
            return False
            
        logging.info(f"用戶名稱: {self.user_info.get('username')}")
        logging.info(f"用戶 ID: {self.user_info.get('id')}")
        
        # 檢查發布限制
        limit_info = await self.api.get_publishing_limit()
        if not limit_info:
            logging.error("無法獲取發布限制資訊")
            return False
            
        logging.info(f"已使用 {limit_info.get('quota_usage', 0)} / {limit_info.get('quota_total', 0)} 則貼文")
        return True
        
    async def check_and_reply(self):
        """檢查並回覆貼文"""
        try:
            # 獲取最新的貼文
            posts = await self.api.get_user_posts(limit=25)
            if not posts:
                logging.warning("無法獲取貼文")
                return
                
            logging.info(f"成功獲取 {len(posts)} 則貼文")
            
            # 檢查每個貼文的回覆
            for post in posts:
                post_id = post.get("id")
                logging.info(f"檢查貼文 {post_id} 的回覆...")
                
                # 獲取回覆
                post_replies = await self.api.get_post_replies(post_id)
                if not post_replies:
                    continue
                    
                logging.info(f"找到 {len(post_replies)} 則回覆")
                
                # 處理每個回覆
                for reply in post_replies:
                    reply_id = reply.get("id")
                    username = reply.get("username")
                    text = reply.get("text")
                    
                    # 檢查是否已經回覆過
                    if reply_id in self.memory["replies"]:
                        continue
                        
                    # 如果是自己的回覆則跳過
                    if username == self.user_info.get("username"):
                        continue
                        
                    # 判斷是否要立即回覆
                    if not self._should_reply_now():
                        logging.info(f"暫時不回覆 {username} 的訊息")
                        continue
                        
                    # 生成回覆
                    reply_text = self._generate_reply(username, text)
                    
                    # 建立回覆
                    new_reply_id = await self.api.create_reply(reply_id, reply_text)
                    if new_reply_id:
                        logging.info(f"成功回覆 {username}，回覆 ID: {new_reply_id}")
                        
                        # 更新記憶
                        self._update_user_memory(username, {
                            "type": "reply",
                            "original_text": text,
                            "reply_text": reply_text,
                            "post_id": post_id,
                            "reply_id": reply_id
                        })
                        
                        self.memory["replies"][reply_id] = {
                            "timestamp": datetime.now().isoformat(),
                            "username": username,
                            "text": reply_text
                        }
                        self._save_memory()
                    else:
                        logging.error(f"回覆 {username} 失敗")
                        
        except Exception as e:
            logging.error(f"檢查回覆時發生錯誤: {str(e)}")
            
    async def run(self):
        """執行系統"""
        if not await self.initialize():
            return
            
        check_interval = 30  # 檢查間隔（秒）
        
        try:
            while True:
                logging.info(f"\n=== 檢查回覆（{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}）===")
                await self.check_and_reply()
                logging.info(f"\n等待 {check_interval} 秒後再次檢查...")
                await asyncio.sleep(check_interval)
                
        except KeyboardInterrupt:
            logging.info("\n程式已停止")
        except Exception as e:
            logging.error(f"\n發生錯誤: {str(e)}")
        finally:
            self._save_memory()
            logging.info("系統關閉")

if __name__ == "__main__":
    config = Config()
    poster = ThreadsPoster(config)
    asyncio.run(poster.run()) 