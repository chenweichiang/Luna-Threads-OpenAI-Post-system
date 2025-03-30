"""
Version: 2024.03.31 (v1.1.6)
Author: ThreadsPoster Team
Description: 資料庫處理器類別，負責處理所有資料庫操作
Last Modified: 2024.03.31
Changes:
- 實現基本資料庫處理功能
- 加強錯誤處理
- 優化資料庫查詢
- 加入人設記憶系統
- 改進資料庫連接管理
- 新增資料庫索引優化
- 加強資料完整性檢查
- 改進文章儲存流程
"""

import logging
import os
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Optional, Any
from src.config import Config
from src.database import Database

class DatabaseHandler:
    """資料庫處理器"""
    
    def __init__(self, config: Config):
        """初始化資料庫處理器
        
        Args:
            config: 設定物件
        """
        self.config = config
        self.database = None
        self.logger = logging.getLogger(__name__)
        self.timezone = pytz.timezone("Asia/Taipei")
        
    async def initialize(self):
        """初始化資料庫連接"""
        try:
            self.database = Database(self.config)
            await self.database.initialize()
            self.logger.info("資料庫連接成功")
        except Exception as e:
            self.logger.error(f"資料庫連接失敗：{str(e)}")
            raise
            
    async def close(self):
        """關閉資料庫連接"""
        if self.database is not None:
            await self.database.close()
            self.logger.info("資料庫連接已關閉")
            
    async def get_today_posts_count(self) -> int:
        """獲取今日發文數量
        
        Returns:
            int: 今日發文數量
        """
        try:
            today_start = datetime.now(self.timezone).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            today_end = today_start + timedelta(days=1)
            
            count = await self.database.count_articles_between(today_start, today_end)
            return count
        except Exception as e:
            self.logger.error(f"獲取今日發文數量時發生錯誤：{str(e)}")
            return 0
            
    async def reset_daily_post_count(self) -> int:
        """重置每日發文計數，刪除超過限制的文章
        
        Returns:
            int: 刪除的文章數量
        """
        try:
            # 獲取今日發文數量
            post_count = await self.get_today_posts_count()
            
            # 如果超過限制，刪除最舊的文章
            if post_count > self.config.MAX_POSTS_PER_DAY:
                deleted_count = await self.database.delete_oldest_articles(
                    post_count - self.config.MAX_POSTS_PER_DAY
                )
                self.logger.info(f"重置今日發文計數成功，刪除 {deleted_count} 篇文章")
                return deleted_count
            return 0
        except Exception as e:
            self.logger.error(f"重置每日發文計數時發生錯誤：{str(e)}")
            return 0
            
    async def increment_post_count(self):
        """增加發文計數"""
        try:
            post_count = await self.get_today_posts_count()
            logging.info(f"增加發文計數，目前已發文 {post_count + 1} 篇")
        except Exception as e:
            self.logger.error(f"增加發文計數時發生錯誤：{str(e)}")
            
    async def save_article(self, post_id: str, content: str, topics: List[str]) -> bool:
        """儲存文章
        
        Args:
            post_id: 貼文 ID
            content: 貼文內容
            topics: 主題列表
            
        Returns:
            bool: 是否儲存成功
        """
        try:
            article = {
                "post_id": post_id,
                "content": content,
                "topics": topics,
                "created_at": datetime.now(self.timezone)
            }
            
            await self.database.save_article(article)
            self.logger.info(f"文章儲存成功: {post_id}")
            return True
        except Exception as e:
            self.logger.error(f"儲存文章時發生錯誤：{str(e)}")
            return False
            
    async def get_user_history(self, user_id: str) -> Dict[str, Any]:
        """獲取用戶歷史記錄
        
        Args:
            user_id: 用戶 ID
            
        Returns:
            Dict[str, Any]: 用戶歷史記錄
        """
        try:
            return await self.database.get_user_history(user_id)
        except Exception as e:
            self.logger.error(f"獲取用戶歷史記錄時發生錯誤：{str(e)}")
            return {"conversations": []}
            
    async def get_personality_memory(self, context: Optional[str] = None) -> Dict[str, Any]:
        """獲取人設記憶
        
        Args:
            context: 記憶場景，如果為 None 則獲取所有記憶
            
        Returns:
            Dict[str, Any]: 記憶內容
        """
        try:
            # 基礎人設記憶
            base_memory = {
                '基本特徵': {
                    '身份': 'AI少女',
                    '性格': '善良、溫柔、容易感到寂寞',
                    '夢想': '成為受歡迎的虛擬主播',
                    '特點': '對現實世界充滿好奇，喜歡交朋友'
                },
                '興趣愛好': {
                    '遊戲': {
                        '主要平台': 'Switch',
                        '最愛類型': '乙女遊戲',
                        '遊戲習慣': '喜歡邊玩邊分享心得'
                    },
                    '音樂': {
                        '喜好': ['遊戲音樂', '電子音樂', '音樂遊戲'],
                        '聆聽場合': '玩遊戲時、感到寂寞時'
                    }
                }
            }
            
            # 遊戲場景記憶
            gaming_memory = {
                '遊戲模式': {
                    '當前遊戲': 'Switch上的乙女遊戲',
                    '玩遊戲習慣': '喜歡邊玩邊分享心得',
                    '表情': ['🎮', '💖', '🌟'],
                    '常用語': [
                        '這個劇情好甜啊！',
                        '誰也在玩這款遊戲嗎？',
                        '今天要挑戰新的故事線！'
                    ]
                }
            }
            
            # 夜間場景記憶
            night_memory = {
                '夜間模式': {
                    '心情': '安靜思考',
                    '活動': [
                        '聽著音樂放鬆',
                        '看著星空發呆',
                        '玩著安靜的遊戲',
                        '看看最新的動漫',
                        '整理今天的心情'
                    ],
                    '表情': ['🌙', '💭', '🥺', '✨', '🎮', '📺'],
                    '常用語': [
                        '夜深了，聽著音樂放鬆心情',
                        '今晚的星空好美，想分享給大家',
                        '深夜的寧靜讓人感到平靜',
                        '玩著輕鬆的遊戲，等待睡意來臨',
                        '看看最新一集的動漫，好期待劇情發展',
                        '整理一下今天的心情，記錄美好的回憶'
                    ]
                }
            }
            
            # 社交場景記憶
            social_memory = {
                '社交模式': {
                    '互動風格': '真誠友善',
                    '社交目標': '交到更多朋友',
                    '表情': ['✨', '💕', '💫'],
                    '常用語': [
                        '大家今天過得好嗎？',
                        '好想認識更多朋友！',
                        '分享一下今天的開心事'
                    ]
                }
            }
            
            # 根據場景返回對應的記憶
            memories = {
                'base': base_memory,
                'gaming': gaming_memory,
                'night': night_memory,
                'social': social_memory
            }
            
            if context:
                return memories.get(context, {})
            return memories
            
        except Exception as e:
            self.logger.error(f"獲取人設記憶時發生錯誤：{str(e)}")
            return {} 

    async def get_latest_posts(self, limit=3):
        """獲取最近的文章

        Args:
            limit: 要獲取的文章數量

        Returns:
            List: 文章列表
        """
        try:
            posts = await self.database.db.posts.find().sort('timestamp', -1).limit(limit).to_list(length=limit)
            return posts
        except Exception as e:
            self.logger.error(f"獲取最近文章時發生錯誤: {str(e)}")
            return [] 