"""
排程系統
處理所有定時任務的排程
"""

import logging
import asyncio
from datetime import datetime, timedelta
import random
from typing import Callable, Coroutine, Any

logger = logging.getLogger(__name__)

class Scheduler:
    def __init__(self):
        self.tasks = []
        self.running = False
        
    async def start(self):
        """啟動排程器"""
        self.running = True
        logger.info("排程器已啟動")
        await self._run_tasks()
        
    async def stop(self):
        """停止排程器"""
        self.running = False
        logger.info("排程器已停止")
        
    def add_task(self, task: Callable[[], Coroutine[Any, Any, None]], interval: int, random_delay: bool = False):
        """
        添加定時任務
        
        Args:
            task: 要執行的異步函數
            interval: 執行間隔（秒）
            random_delay: 是否添加隨機延遲
        """
        self.tasks.append({
            "task": task,
            "interval": interval,
            "random_delay": random_delay,
            "last_run": None
        })
        logger.info(f"已添加新任務，間隔: {interval}秒")
        
    async def _run_tasks(self):
        """執行所有任務"""
        while self.running:
            current_time = datetime.now()
            
            for task in self.tasks:
                # 檢查是否需要執行任務
                if (task["last_run"] is None or 
                    (current_time - task["last_run"]).total_seconds() >= task["interval"]):
                    
                    # 如果需要隨機延遲，添加 1-5 分鐘的隨機延遲
                    if task["random_delay"]:
                        delay = random.randint(60, 300)
                        logger.info(f"添加 {delay} 秒隨機延遲")
                        await asyncio.sleep(delay)
                    
                    try:
                        await task["task"]()
                        task["last_run"] = current_time
                        logger.info("任務執行完成")
                    except Exception as e:
                        logger.error(f"任務執行失敗: {str(e)}")
            
            # 每 60 秒檢查一次
            await asyncio.sleep(60) 