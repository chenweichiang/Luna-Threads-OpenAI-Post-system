"""
Version: 2024.03.30
Author: ThreadsPoster Team
Description: 日誌處理模組，負責系統日誌的配置和管理
Last Modified: 2024.03.30
Changes:
- 優化日誌格式
- 加入顏色支援
- 改進訊息排版
"""

import logging
import os
import json
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger
from src.config import Config
from typing import Any, Dict

class ColorFormatter(logging.Formatter):
    """自定義格式化器，支援顏色輸出"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 綠色
        'WARNING': '\033[33m',   # 黃色
        'ERROR': '\033[31m',    # 紅色
        'CRITICAL': '\033[35m',  # 紫色
        'RESET': '\033[0m'      # 重置
    }
    
    ICONS = {
        'DEBUG': '🔍',
        'INFO': '📝',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🔥'
    }
    
    def __init__(self, use_color: bool = True):
        super().__init__()
        self.use_color = use_color
    
    def format_time(self, record: logging.LogRecord) -> str:
        """格式化時間"""
        creation_time = datetime.fromtimestamp(record.created)
        return creation_time.strftime("%Y-%m-%d %H:%M:%S")
    
    def format_dict(self, data: dict, indent: int = 0) -> str:
        """格式化字典內容，使其更易讀"""
        lines = []
        prefix = "  " * indent
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(self.format_dict(value, indent + 1))
            else:
                lines.append(f"{prefix}{key}: {value}")
        return "\n".join(lines)
    
    def format_message(self, record: logging.LogRecord) -> str:
        """格式化訊息內容"""
        if isinstance(record.msg, dict):
            return self.format_dict(record.msg)
        return str(record.msg)
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日誌記錄"""
        # 基本資訊
        log_time = self.format_time(record)
        log_level = record.levelname
        
        # 添加顏色
        if self.use_color:
            color = self.COLORS.get(log_level, self.COLORS['RESET'])
            reset = self.COLORS['RESET']
        else:
            color = reset = ''
            
        # 獲取圖標
        icon = self.ICONS.get(log_level, '')
        
        # 格式化訊息
        message = self.format_message(record)
        
        # 根據訊息類型使用不同格式
        if isinstance(record.msg, dict) and "記憶體使用狀況" in record.msg:
            # 系統狀態報告格式
            return (
                f"\n{color}{'='*50}{reset}\n"
                f"{color}系統狀態報告 {icon}{reset} {log_time}\n"
                f"{color}{'-'*50}{reset}\n"
                f"{message}\n"
                f"{color}{'='*50}{reset}\n"
            )
        elif "初始化" in str(record.msg):
            # 初始化訊息格式
            return f"{color}【初始化】{reset} {icon} {log_time} | {message}"
        elif any(key in str(record.msg).lower() for key in ["成功", "失敗", "錯誤"]):
            # 操作結果格式
            if isinstance(record.msg, dict):
                return (
                    f"\n{color}{'-'*30}{reset}\n"
                    f"{color}操作結果 {icon}{reset} {log_time}\n"
                    f"{message}\n"
                    f"{color}{'-'*30}{reset}\n"
                )
            return f"{color}【結果】{reset} {icon} {log_time} | {message}"
        elif "監控" in str(record.msg):
            # 監控訊息格式
            if isinstance(record.msg, dict):
                return (
                    f"\n{color}{'-'*40}{reset}\n"
                    f"{color}監控資訊 {icon}{reset} {log_time}\n"
                    f"{message}\n"
                    f"{color}{'-'*40}{reset}\n"
                )
            return f"{color}【監控】{reset} {icon} {log_time} | {message}"
        else:
            # 一般訊息格式
            return f"{color}【資訊】{reset} {icon} {log_time} | {message}"

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
        # 設定日誌格式
        log_format = logging.Formatter(
            '【%(levelname)s】 %(asctime)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 設定檔案處理器
        file_handler = logging.FileHandler(
            filename=self.log_file,
            encoding='utf-8'
        )
        file_handler.setFormatter(log_format)
        
        # 設定控制台處理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_format)
        
        # 設定根日誌記錄器
        root_logger = logging.getLogger()
        root_logger.setLevel(self.config.LOG_LEVEL)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        # 關閉 aiohttp 的訪問日誌
        logging.getLogger('aiohttp.access').setLevel(logging.WARNING)
        
        # 自定義 aiohttp 的客戶端日誌格式
        aiohttp_logger = logging.getLogger('aiohttp.client')
        aiohttp_logger.setLevel(logging.INFO)

def setup_logger(name=None):
    """設定日誌系統並返回一個已配置的logger
    
    Args:
        name: 日誌器名稱，如果為None則使用根日誌器
        
    Returns:
        logging.Logger: 已配置的日誌器
    """
    # 確保日誌目錄存在
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # 設定日誌格式
    log_format = logging.Formatter(
        '【%(levelname)s】 %(asctime)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 設定檔案處理器
    file_handler = logging.FileHandler(
        filename=os.path.join(log_dir, 'app.log'),
        encoding='utf-8'
    )
    file_handler.setFormatter(log_format)
    
    # 設定控制台處理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    
    # 獲取或建立日誌記錄器
    if name:
        logger = logging.getLogger(name)
    else:
        logger = logging.getLogger()
        
    # 避免重複添加處理器
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    # 關閉 aiohttp 的訪問日誌
    logging.getLogger('aiohttp.access').setLevel(logging.WARNING)
    
    # 自定義 aiohttp 的客戶端日誌格式
    aiohttp_logger = logging.getLogger('aiohttp.client')
    aiohttp_logger.setLevel(logging.INFO)
    
    return logger

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

# 設定其他模組的日誌級別
logging.getLogger('asyncio').setLevel(logging.WARNING)
logging.getLogger('aiohttp').setLevel(logging.WARNING) 