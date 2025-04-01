#!/usr/bin/env python
"""
測試腳本 - 測試說話模式模組的資料庫存取功能
"""

import asyncio
import logging
import json
from datetime import datetime
import os
import pytz

from src.speaking_patterns import SpeakingPatterns
from src.db_handler import DatabaseHandler
from src.config import Config

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_db_patterns")

async def test_speaking_patterns_db():
    """測試說話模式模組的資料庫存取功能"""
    logger.info("===== 測試說話模式模組的資料庫存取功能 =====")
    
    # 建立設定和資料庫連接
    config = Config()
    db_handler = DatabaseHandler(config)
    await db_handler.initialize()
    logger.info("資料庫連接成功")
    
    try:
        # 創建說話模式模組
        speaking_patterns = SpeakingPatterns()
        speaking_patterns.set_db_handler(db_handler)
        
        # 初始化默認模式
        speaking_patterns._initialize_default_speaking_styles()
        
        # 保存到資料庫
        logger.info("保存默認說話模式到資料庫...")
        await speaking_patterns.save_patterns_to_db()
        logger.info("保存完成")
        
        # 新增一個測試模式
        logger.info("添加測試說話模式...")
        test_pattern = f"測試模式 {datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')}"
        success = await speaking_patterns.add_speaking_pattern("base", "開場白", test_pattern)
        logger.info(f"添加結果: {'成功' if success else '失敗'}")
        
        # 重新載入說話模式
        logger.info("創建新的說話模式模組並載入之前保存的模式...")
        new_patterns = SpeakingPatterns()
        new_patterns.set_db_handler(db_handler)
        await new_patterns.load_patterns_from_db()
        
        # 檢查新增的模式是否存在
        if "base" in new_patterns.speaking_styles and "開場白" in new_patterns.speaking_styles["base"]:
            if test_pattern in new_patterns.speaking_styles["base"]["開場白"]:
                logger.info("測試成功！可以從資料庫載入新增的模式")
            else:
                logger.warning("測試失敗：未找到新增的模式")
        else:
            logger.warning("測試失敗：未找到base場景或開場白類別")
        
        # 檢查系統提示詞生成
        prompt = new_patterns.get_system_prompt("base", "日常生活")
        logger.info(f"系統提示詞示例:\n{prompt[:200]}...")
        
        # 添加不同場景的測試模式
        scenes = ["gaming", "social", "night"]
        categories = ["開場白", "結尾句", "口頭禪", "情感表達"]
        
        for scene in scenes:
            for category in categories:
                test_pattern = f"{scene}測試{category} {datetime.now(pytz.timezone('Asia/Taipei')).strftime('%H:%M:%S')}"
                await new_patterns.add_speaking_pattern(scene, category, test_pattern)
                logger.info(f"已添加: {scene} - {category} - {test_pattern}")
                
        # 導出所有模式到JSON文件
        logger.info("導出說話模式到JSON文件...")
        with open("speaking_patterns_export.json", "w", encoding="utf-8") as f:
            json.dump({
                "speaking_styles": new_patterns.speaking_styles,
                "time_specific_patterns": new_patterns.time_specific_patterns,
                "export_time": datetime.now(pytz.timezone("Asia/Taipei")).strftime("%Y-%m-%d %H:%M:%S")
            }, f, ensure_ascii=False, indent=2)
        logger.info("導出完成")
        
        return True
    except Exception as e:
        logger.error(f"測試過程中發生錯誤: {str(e)}")
        return False
    finally:
        # 關閉資料庫連接
        await db_handler.close()
        logger.info("資料庫連接已關閉")

async def main():
    """主測試函數"""
    logger.info("開始測試說話模式模組的資料庫功能")
    
    success = await test_speaking_patterns_db()
    
    if success:
        logger.info("測試成功！說話模式模組已成功整合到資料庫系統")
    else:
        logger.error("測試失敗！請檢查錯誤日誌")
    
if __name__ == "__main__":
    # 運行測試
    asyncio.run(main()) 