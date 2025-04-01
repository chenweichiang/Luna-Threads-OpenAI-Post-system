"""
Version: 2025.03.31 (v1.1.9)
Author: ThreadsPoster Team
Description: 性能監控模組，負責記錄系統效能指標
Last Modified: 2025.03.31
Changes:
- 實現基本性能監控功能
- 添加記憶體使用監控
- 添加操作計時功能
- 添加數據庫操作統計
- 添加API請求監控
"""

import os
import time
import json
import logging
import tracemalloc
import asyncio
import functools
import traceback
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
import pytz
from collections import defaultdict

class PerformanceMonitor:
    """性能監控器類別"""
    
    def __init__(self, config=None, enabled=True):
        """初始化性能監控器
        
        Args:
            config: 設定物件
            enabled: 是否啟用監控
        """
        self.logger = logging.getLogger(__name__)
        self.enabled = enabled
        self.config = config
        self.timezone = pytz.timezone(os.getenv("TIMEZONE", "Asia/Taipei"))
        
        # 儲存操作時間
        self.operation_times = defaultdict(list)
        self.start_times = {}
        
        # API統計
        self.api_stats = {
            "openai": {"requests": 0, "tokens": 0, "errors": 0},
            "threads": {"requests": 0, "posts": 0, "errors": 0}
        }
        
        # 資料庫統計
        self.db_stats = {
            "queries": 0,
            "inserts": 0,
            "updates": 0,
            "errors": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "operations_log": []  # 儲存最近的操作記錄
        }
        self.max_operation_logs = int(os.getenv("MAX_DB_OPERATION_LOGS", "1000"))  # 最多保存1000筆操作記錄
        self.detailed_db_logging = os.getenv("DETAILED_DB_LOGGING", "true").lower() == "true"  # 是否開啟詳細日誌
        self.db_log_sample_rate = float(os.getenv("DB_LOG_SAMPLE_RATE", "0.1"))  # 日誌採樣率，默認10%
        
        # 性能指標檔案路徑
        self.metrics_dir = Path("logs/metrics")
        self.metrics_dir.mkdir(exist_ok=True, parents=True)
        self.metrics_file = self.metrics_dir / f"metrics_{datetime.now().strftime('%Y%m%d')}.json"
        
        # 資料庫操作日誌路徑
        self.db_log_dir = Path("logs/db_operations")
        self.db_log_dir.mkdir(exist_ok=True, parents=True)
        self.db_log_file = self.db_log_dir / f"db_operations_{datetime.now().strftime('%Y%m%d')}.log"
        
        # 設置資料庫操作日誌
        self.db_logger = self._setup_db_logger()
        
        # 載入之前的指標數據
        self._load_metrics()
        
        # 啟動追蹤記憶體
        if self.enabled:
            tracemalloc.start()
            
    def _setup_db_logger(self):
        """設置資料庫操作日誌"""
        logger = logging.getLogger("db_operations")
        logger.setLevel(logging.INFO)
        
        # 文件處理器
        file_handler = logging.FileHandler(self.db_log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        
        # 格式化
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # 添加處理器
        logger.addHandler(file_handler)
        
        # 確保不向上傳遞
        logger.propagate = False
        
        return logger
        
    def _should_log_operation(self):
        """是否應記錄此操作，依照採樣率決定"""
        if not self.detailed_db_logging:
            return False
            
        return random.random() < self.db_log_sample_rate
        
    def _load_metrics(self):
        """載入先前的性能指標"""
        try:
            if self.metrics_file.exists():
                try:
                    with open(self.metrics_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for key, values in data.get("operation_times", {}).items():
                            self.operation_times[key].extend(values)
                        
                        # 合併 API 統計數據
                        for api, stats in data.get("api_stats", {}).items():
                            if api in self.api_stats:
                                for stat_key, value in stats.items():
                                    if stat_key in self.api_stats[api]:
                                        self.api_stats[api][stat_key] += value
                        
                        # 合併資料庫統計數據
                        for key, value in data.get("db_stats", {}).items():
                            if key in self.db_stats:
                                self.db_stats[key] += value
                except Exception as e:
                    self.logger.error(f"載入性能指標失敗: {str(e)}")
        except Exception as e:
            self.logger.warning(f"檢查性能指標檔案時出錯: {str(e)}, 將創建新檔案")
                
    def save_metrics(self):
        """儲存性能指標"""
        if not self.enabled:
            return
            
        try:
            # 收集記憶體使用情報
            current, peak = tracemalloc.get_traced_memory()
            
            # 整理資料庫操作記錄 (最多保留100條)
            if len(self.db_stats["operations_log"]) > 100:
                db_logs = self.db_stats["operations_log"][-100:]
            else:
                db_logs = self.db_stats["operations_log"]
                
            data = {
                "timestamp": datetime.now(self.timezone).isoformat(),
                "operation_times": dict(self.operation_times),
                "api_stats": self.api_stats,
                "db_stats": {
                    "queries": self.db_stats["queries"],
                    "inserts": self.db_stats["inserts"],
                    "updates": self.db_stats["updates"],
                    "errors": self.db_stats["errors"],
                    "cache_hits": self.db_stats["cache_hits"],
                    "cache_misses": self.db_stats["cache_misses"],
                    "recent_operations": db_logs
                },
                "memory": {
                    "current": current,
                    "peak": peak
                }
            }
            
            # 確保目錄存在
            self.metrics_dir.mkdir(exist_ok=True, parents=True)
            
            # 使用內建的 open 函數而不是 name 'open'
            with open(str(self.metrics_file), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            self.logger.info("性能指標已儲存至 %s", self.metrics_file)
            
        except Exception as e:
            self.logger.error(f"儲存性能指標失敗: {str(e)}")
            
    def start_operation(self, operation_name: str):
        """開始計時操作
        
        Args:
            operation_name: 操作名稱
        """
        if not self.enabled:
            return
            
        self.start_times[operation_name] = time.time()
        
    def end_operation(self, operation_name: str):
        """結束計時操作
        
        Args:
            operation_name: 操作名稱
            
        Returns:
            float: 操作耗時（秒）
        """
        if not self.enabled or operation_name not in self.start_times:
            return 0
            
        elapsed_time = time.time() - self.start_times[operation_name]
        self.operation_times[operation_name].append(elapsed_time)
        
        # 只保留最近100筆資料
        if len(self.operation_times[operation_name]) > 100:
            self.operation_times[operation_name] = self.operation_times[operation_name][-100:]
            
        self.logger.debug("操作 %s 完成，耗時 %.3f 秒", operation_name, elapsed_time)
        return elapsed_time
        
    def record_api_request(self, api_name: str, success: bool, **kwargs):
        """記錄API請求
        
        Args:
            api_name: API名稱
            success: 請求是否成功
            **kwargs: 其他資訊
        """
        if not self.enabled or api_name not in self.api_stats:
            return
            
        self.api_stats[api_name]["requests"] += 1
        
        if not success:
            self.api_stats[api_name]["errors"] += 1
            
        if api_name == "openai" and "tokens" in kwargs:
            self.api_stats[api_name]["tokens"] += kwargs["tokens"]
            
        if api_name == "threads" and success:
            self.api_stats[api_name]["posts"] += 1
            
    def record_db_operation(self, operation_type: str, success: bool, 
                           from_cache: bool = False, count: int = 1,
                           collection: str = None, query: str = None):
        """記錄資料庫操作
        
        Args:
            operation_type: 操作類型，如 "query", "insert", "update"
            success: 操作是否成功
            from_cache: 是否從快取獲取
            count: 操作數量，用於批量操作
            collection: 集合名稱
            query: 查詢語句或操作描述
        """
        if not self.enabled:
            return
            
        # 更新統計資料
        if operation_type == "query":
            self.db_stats["queries"] += count
            if from_cache:
                self.db_stats["cache_hits"] += count
            else:
                self.db_stats["cache_misses"] += count
        elif operation_type == "insert":
            self.db_stats["inserts"] += count
        elif operation_type == "update":
            self.db_stats["updates"] += count
            
        if not success:
            self.db_stats["errors"] += count
            
        # 紀錄操作詳情
        if self._should_log_operation() or not success:
            # 獲取呼叫堆疊
            stack = traceback.extract_stack()
            # 找出實際呼叫的檔案和行數
            caller = None
            for frame in reversed(stack[:-1]):
                if "database.py" in frame.filename:
                    continue
                caller = frame
                break
                
            caller_info = f"{os.path.basename(caller.filename)}:{caller.lineno}" if caller else "unknown"
            timestamp = datetime.now(self.timezone).strftime("%Y-%m-%d %H:%M:%S")
            
            # 格式化操作記錄
            operation_log = {
                "timestamp": timestamp,
                "type": operation_type,
                "collection": collection or "unknown",
                "success": success,
                "from_cache": from_cache,
                "count": count,
                "caller": caller_info,
                "query": query
            }
            
            # 保存到操作記錄
            self.db_stats["operations_log"].append(operation_log)
            
            # 限制記錄數量
            if len(self.db_stats["operations_log"]) > self.max_operation_logs:
                self.db_stats["operations_log"] = self.db_stats["operations_log"][-self.max_operation_logs:]
                
            # 記錄到資料庫操作日誌
            log_msg = f"{timestamp} - {operation_type} - {collection or 'unknown'} - "
            log_msg += f"{'成功' if success else '失敗'} - "
            log_msg += f"{'快取' if from_cache else '資料庫'} - "
            log_msg += f"數量:{count} - 來源:{caller_info}"
            
            if query:
                log_msg += f" - 描述:{query}"
                
            # 將操作記錄寫入日誌
            if success:
                self.db_logger.info(log_msg)
            else:
                self.db_logger.error(log_msg)
                
    def get_operation_stats(self, operation_name: str = None) -> Dict[str, Any]:
        """取得操作統計資料
        
        Args:
            operation_name: 操作名稱，如果不指定則返回所有操作
            
        Returns:
            Dict[str, Any]: 操作統計資料
        """
        if not self.enabled:
            return {}
            
        if operation_name and operation_name in self.operation_times:
            times = self.operation_times[operation_name]
            return {
                "count": len(times),
                "avg_time": sum(times) / len(times) if times else 0,
                "min_time": min(times) if times else 0,
                "max_time": max(times) if times else 0
            }
        else:
            stats = {}
            for op_name, times in self.operation_times.items():
                stats[op_name] = {
                    "count": len(times),
                    "avg_time": sum(times) / len(times) if times else 0,
                    "min_time": min(times) if times else 0,
                    "max_time": max(times) if times else 0
                }
            return stats
            
    def get_memory_usage(self) -> Dict[str, int]:
        """取得記憶體使用狀況
        
        Returns:
            Dict[str, int]: 記憶體使用狀況
        """
        if not self.enabled:
            return {"current": 0, "peak": 0}
            
        current, peak = tracemalloc.get_traced_memory()
        return {"current": current, "peak": peak}
        
    def get_db_operations_report(self, limit: int = 20) -> Dict[str, Any]:
        """獲取資料庫操作報告
        
        Args:
            limit: 最多返回的操作記錄數量
            
        Returns:
            Dict[str, Any]: 資料庫操作報告
        """
        if not self.enabled:
            return {}
            
        # 計算快取命中率
        if self.db_stats["cache_hits"] + self.db_stats["cache_misses"] > 0:
            cache_hit_rate = (self.db_stats["cache_hits"] / 
                            (self.db_stats["cache_hits"] + self.db_stats["cache_misses"])) * 100
        else:
            cache_hit_rate = 0
            
        # 獲取最近的操作記錄
        recent_ops = self.db_stats["operations_log"][-limit:] if self.db_stats["operations_log"] else []
        
        # 分類操作統計
        operation_types = defaultdict(int)
        collection_stats = defaultdict(int)
        error_stats = defaultdict(int)
        
        for op in self.db_stats["operations_log"]:
            operation_types[op["type"]] += op["count"]
            collection_stats[op["collection"]] += op["count"]
            if not op["success"]:
                error_stats[op["collection"]] += op["count"]
                
        return {
            "total_operations": sum([
                self.db_stats["queries"],
                self.db_stats["inserts"],
                self.db_stats["updates"]
            ]),
            "cache_hit_rate": cache_hit_rate,
            "error_rate": (self.db_stats["errors"] / max(1, sum([
                self.db_stats["queries"],
                self.db_stats["inserts"],
                self.db_stats["updates"]
            ]))) * 100,
            "operation_types": dict(operation_types),
            "collection_stats": dict(collection_stats),
            "error_stats": dict(error_stats),
            "recent_operations": recent_ops
        }
        
    def summary(self) -> Dict[str, Any]:
        """取得性能摘要資訊
        
        Returns:
            Dict[str, Any]: 性能摘要資訊
        """
        if not self.enabled:
            return {}
            
        return {
            "memory": self.get_memory_usage(),
            "operations": self.get_operation_stats(),
            "api_stats": self.api_stats,
            "db_stats": {
                "queries": self.db_stats["queries"],
                "inserts": self.db_stats["inserts"],
                "updates": self.db_stats["updates"],
                "errors": self.db_stats["errors"],
                "cache_hits": self.db_stats["cache_hits"],
                "cache_misses": self.db_stats["cache_misses"],
                "cache_hit_rate": (self.db_stats["cache_hits"] / max(1, self.db_stats["cache_hits"] + self.db_stats["cache_misses"])) * 100
            },
            "db_operations": self.get_db_operations_report(10)  # 包含前10筆操作
        }
        
    def reset_stats(self):
        """重置統計資料"""
        if not self.enabled:
            return
            
        self.operation_times = defaultdict(list)
        self.start_times = {}
        self.api_stats = {
            "openai": {"requests": 0, "tokens": 0, "errors": 0},
            "threads": {"requests": 0, "posts": 0, "errors": 0}
        }
        self.db_stats = {
            "queries": 0,
            "inserts": 0,
            "updates": 0,
            "errors": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "operations_log": []
        }
        tracemalloc.clear_traces()
        
    def shutdown(self):
        """關閉性能監控器並保存指標"""
        if self.enabled:
            try:
                self.save_metrics()
                tracemalloc.stop()
                self.logger.info("性能監控器已關閉")
            except Exception as e:
                self.logger.error(f"關閉性能監控器時發生錯誤: {str(e)}")
        self.enabled = False  # 標記為已關閉，避免後續操作

    def __del__(self):
        """清理資源"""
        if self.enabled:
            try:
                self.save_metrics()
                tracemalloc.stop()
            except Exception as e:
                try:
                    logger = logging.getLogger(__name__)
                    logger.error(f"清理性能監控器資源時發生錯誤: {str(e)}")
                except:
                    pass  # 在最終的異常處理中避免更多錯誤

# 定義裝飾器用於追蹤函數執行時間
def track_performance(operation_name=None):
    """函數性能追蹤裝飾器
    
    Args:
        operation_name: 操作名稱，如果不指定則使用函數名稱
        
    Returns:
        Callable: 裝飾後的函數
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 獲取 monitor 實例
            monitor = None
            for arg in args:
                if hasattr(arg, "performance_monitor"):
                    monitor = arg.performance_monitor
                    break
            
            if not monitor:
                return await func(*args, **kwargs)
                
            # 使用函數名作為操作名
            op_name = operation_name or func.__name__
            
            monitor.start_operation(op_name)
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                monitor.end_operation(op_name)
                
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 獲取 monitor 實例
            monitor = None
            for arg in args:
                if hasattr(arg, "performance_monitor"):
                    monitor = arg.performance_monitor
                    break
            
            if not monitor:
                return func(*args, **kwargs)
                
            # 使用函數名作為操作名
            op_name = operation_name or func.__name__
            
            monitor.start_operation(op_name)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                monitor.end_operation(op_name)
                
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# 創建全局性能監控實例
performance_monitor = PerformanceMonitor(enabled=True) 