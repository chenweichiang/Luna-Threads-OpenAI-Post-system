#!/usr/bin/env python
"""
測試腳本 - 測試ThreadsPoster系統各個核心組件的運行情況
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
import pytz

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_system")

async def test_speaking_patterns():
    """測試說話模式模組"""
    from src.speaking_patterns import SpeakingPatterns
    
    logger.info("===== 測試說話模式模組 =====")
    sp = SpeakingPatterns()
    
    # 測試獲取系統提示詞
    prompt = sp.get_system_prompt('gaming', '遊戲體驗')
    logger.info(f"系統提示詞示例:\n{prompt[:200]}...")
    
    # 測試驗證標準
    criteria = sp.get_content_validation_criteria()
    logger.info(f"驗證標準: {criteria}")
    
    # 測試時間相關功能
    time_period = sp._get_current_time_period()
    logger.info(f"當前時間段: {time_period}")
    
    # 測試時間特定模式
    time_pattern = sp.get_time_specific_pattern()
    logger.info(f"時間特定模式示例開場白: {time_pattern['開場白'][0]}")
    
    # 測試用戶提示詞
    user_prompt = sp.get_user_prompt("科技新知")
    logger.info(f"用戶提示詞: {user_prompt[:100]}...")
    
    return True

async def test_content_generator():
    """測試內容生成器"""
    import aiohttp
    from src.content_generator import ContentGenerator
    from src.db_handler import DatabaseHandler
    from src.config import Config
    
    logger.info("===== 測試內容生成器 =====")
    
    # 創建必要的組件
    config = Config()
    
    # 使用模擬的資料庫處理器
    class MockDBHandler:
        async def get_personality_memory(self, context):
            return {
                "基本特徵": {
                    "身份": "AI少女",
                    "性格": "善良、溫柔、容易感到寂寞",
                    "特點": "對現實世界充滿好奇，喜歡交朋友",
                    "說話風格": "活潑可愛，文字中會使用表情符號表達情感"
                }
            }
    
    # 創建HTTP會話
    async with aiohttp.ClientSession() as session:
        # 使用模擬的API密鑰和數據庫處理器創建內容生成器
        content_generator = ContentGenerator("test_api_key", session, MockDBHandler())
        
        # 初始化內容生成器
        await content_generator.initialize()
        
        # 測試驗證功能
        test_content = "嗨嗨，最近發現一款超有趣的遊戲！✨ 我花了好多時間研究它的玩法，真的很有深度。操作簡單但是戰略性很強，每次玩都會發現新東西～🎮 你們有玩過類似的遊戲嗎？"
        validation_result = content_generator._validate_content(test_content, content_generator.speaking_patterns.get_content_validation_criteria())
        logger.info(f"內容驗證結果: {validation_result}")
        
        # 測試內容後處理
        processed_content = content_generator._post_process_content("哈囉！今天天氣真好")
        logger.info(f"處理後的內容: {processed_content}")
        
        return True

async def test_ai_handler():
    """測試AI處理器"""
    import aiohttp
    from src.ai_handler import AIHandler
    
    logger.info("===== 測試AI處理器 =====")
    
    # 使用模擬的資料庫處理器
    class MockDBHandler:
        async def get_personality_memory(self, context):
            return {
                "基本特徵": {
                    "身份": "AI少女",
                    "性格": "善良、溫柔、容易感到寂寞",
                    "特點": "對現實世界充滿好奇，喜歡交朋友",
                    "說話風格": "活潑可愛，文字中會使用表情符號表達情感"
                }
            }
            
        async def save_personality_memory(self, context, data):
            return True
            
        async def create_base_personality(self):
            return True
    
    # 創建HTTP會話
    async with aiohttp.ClientSession() as session:
        # 使用模擬的API密鑰和數據庫處理器創建AI處理器
        ai_handler = AIHandler("test_api_key", session, MockDBHandler())
        
        # 測試初始化
        try:
            await ai_handler.initialize()
            logger.info("AI處理器初始化成功")
        except Exception as e:
            logger.error(f"AI處理器初始化失敗: {str(e)}")
            return False
            
        # 測試獲取Luna人設
        try:
            personality = await ai_handler._get_luna_personality()
            if personality:
                logger.info("獲取人設成功")
            else:
                logger.warning("未獲取到人設數據")
        except Exception as e:
            logger.error(f"獲取人設失敗: {str(e)}")
            
        # 測試獲取當前上下文
        try:
            context = await ai_handler.get_topic_by_time()
            logger.info(f"當前時間的話題: {context}")
        except Exception as e:
            logger.error(f"獲取話題失敗: {str(e)}")
        
        return True

async def main():
    """主測試函數"""
    logger.info("開始測試 ThreadsPoster 系統組件")
    
    # 測試說話模式模組
    if await test_speaking_patterns():
        logger.info("說話模式模組測試通過")
    else:
        logger.error("說話模式模組測試失敗")
    
    # 測試內容生成器
    if await test_content_generator():
        logger.info("內容生成器測試通過")
    else:
        logger.error("內容生成器測試失敗")
    
    # 測試AI處理器
    if await test_ai_handler():
        logger.info("AI處理器測試通過")
    else:
        logger.error("AI處理器測試失敗")
    
    logger.info("所有測試完成")

if __name__ == "__main__":
    # 運行測試
    asyncio.run(main()) 