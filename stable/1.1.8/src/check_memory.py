"""
Version: 2024.03.30
Author: ThreadsPoster Team
Description: 記憶檢查工具，用於檢視和診斷系統的記憶狀態
Last Modified: 2024.03.30
Changes:
- 優化記憶檢查邏輯
- 改進錯誤處理機制
- 加強日誌記錄
- 優化資料顯示格式
"""

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
檢查資料庫中的記憶內容
"""

import asyncio
import json
import logging
from main import ThreadsPoster
from config import Config
from database import Database

async def check_memories():
    """檢查所有場景的記憶"""
    try:
        config = Config()
        db = Database(config)
        await db.initialize()
        
        # 獲取所有場景的記憶
        contexts = ['base', 'gaming', 'night', 'social']
        for context in contexts:
            memory = await db.get_personality_memory(context)
            print(f"\n=== {context} 場景的記憶 ===")
            print(json.dumps(memory, ensure_ascii=False, indent=2))
        
        await db.close()
        
    except Exception as e:
        print(f"檢查記憶時發生錯誤：{str(e)}")

if __name__ == "__main__":
    # 設定日誌
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(check_memories()) 