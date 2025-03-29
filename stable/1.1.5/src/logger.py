"""
Version: 2024.03.30
Author: ThreadsPoster Team
Description: 日誌處理模組，負責系統日誌的配置和管理
Last Modified: 2024.03.30
Changes:
- 優化日誌格式
- 改進日誌輸出
- 加強日誌分類
- 統一日誌路徑
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger
from src.config import Config

class LoggerSetup:
    """日誌設定類"""
    def __init__(self, config: Config):
        """初始化"""
        self.config = config
        self.log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        self.log_file = os.path.join(self.log_dir, 'threads_poster.log')
        self._setup_log_dir()
        self._setup_logger()

    def _setup_log_dir(self):
        """設置日誌目錄"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def _setup_logger(self):
        """設置日誌記錄器"""
        # 建立日誌格式
        log_format = {
            'time': '%(asctime)s',
            'name': '%(name)s',
            'level': '%(levelname)s',
            'message': '%(message)s'
        }

        # 建立 JSON 格式處理器
        formatter = jsonlogger.JsonFormatter(
            json_ensure_ascii=False,
            fmt='%(asctime)s %(name)s %(levelname)s %(message)s'
        )

        # 建立檔案處理器
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=self.config.LOG_MAX_BYTES,
            backupCount=self.config.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)

        # 建立控制台處理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        # 設置根記錄器
        root_logger = logging.getLogger()
        root_logger.setLevel(self.config.LOG_LEVEL)
        
        # 移除所有現有的處理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
        # 添加新的處理器
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

def setup_logger(config: Config) -> None:
    """設置日誌系統"""
    LoggerSetup(config)

# 使用根記錄器
def log_info(message: str):
    """記錄資訊級別的日誌"""
    logging.getLogger().info(message)

def log_error(message: str, error: Exception = None):
    """記錄錯誤級別的日誌"""
    logger = logging.getLogger()
    if error:
        logger.error(f"{message}: {str(error)}")
        # 如果是除錯模式，也記錄堆疊追蹤
        if logger.level <= logging.DEBUG:
            import traceback
            logger.debug(f"錯誤堆疊追蹤:\n{traceback.format_exc()}")
    else:
        logger.error(message)

def log_warning(message: str):
    """記錄警告級別的日誌"""
    logging.getLogger().warning(message)

def log_debug(message: str):
    """記錄除錯級別的日誌"""
    logging.getLogger().debug(message)

def log_api_call(api_name: str, method: str, params: dict = None, response: dict = None, error: Exception = None):
    """記錄 API 呼叫資訊"""
    logger = logging.getLogger()
    if error:
        logger.error(f"API 呼叫失敗 - {api_name} - {method}: {str(error)}")
    else:
        logger.debug(
            f"API 呼叫 - {api_name} - {method}\n"
            f"參數: {params if params else 'None'}\n"
            f"回應: {response if response else 'None'}"
        )

def log_ai_interaction(prompt: str, response: str = None, error: Exception = None):
    """記錄 AI 互動資訊"""
    logger = logging.getLogger()
    if error:
        logger.error(f"AI 互動失敗: {str(error)}")
    else:
        logger.debug(
            f"AI 互動\n"
            f"提示詞: {prompt}\n"
            f"回應: {response if response else 'None'}"
        ) 