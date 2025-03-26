"""
ThreadsPoster 主程式
只負責發布新文章
"""

import asyncio
import logging
import sys

from src.config import Config
from src.threads_api import ThreadsAPI
from src.ai_handler import AIHandler

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def post_single_article():
    """發布單篇文章"""
    api = None
    try:
        # 初始化設定
        config = Config()
        
        # 初始化 API 客戶端
        api = ThreadsAPI(config)
        
        # 初始化 AI 處理器
        ai_handler = AIHandler(config)
        
        # 生成文章內容
        content = await ai_handler.generate_post()
        if not content:
            logger.error("生成文章內容失敗")
            return
            
        logger.info(f"準備發布文章：{content}")
        
        # 發布文章
        post_id = await api.create_post(content)
        
        if post_id:
            logger.info(f"發文成功！文章 ID: {post_id}")
        else:
            logger.error("發文失敗！")
            
    except Exception as e:
        logger.error(f"發生錯誤：{str(e)}")
    finally:
        # 確保程式結束前關閉所有連接
        if api and hasattr(api, '_session') and api._session:
            await api._session.close()
        # 強制結束程式
        sys.exit(0)

if __name__ == "__main__":
    config = Config()
    logger.info(f"ThreadsPoster v{config.VERSION} ({config.LAST_UPDATED}) 開始運行")
    
    # 執行發文
    asyncio.run(post_single_article()) 