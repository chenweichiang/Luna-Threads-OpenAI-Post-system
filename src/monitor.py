"""
Version: 2024.03.30
Author: ThreadsPoster Team
Description: 監控模組，負責系統運行狀態監控和日誌記錄
Last Modified: 2024.03.30
Changes:
- 優化監控邏輯
- 改進日誌記錄
- 加強異常監控
"""

import logging
import time
from collections import defaultdict
from datetime import datetime
import pytz
from typing import Dict, List, Any, Optional
import json
from pathlib import Path

class PerformanceMonitor:
    """性能監控器"""
    
    def __init__(self, timezone: str = "Asia/Taipei"):
        self.metrics = defaultdict(list)
        self.start_times = {}
        self.logger = logging.getLogger(__name__)
        self.timezone = pytz.timezone(timezone)
        self.metrics_file = Path("logs/metrics.json")
        self.metrics_file.parent.mkdir(exist_ok=True)
        
        # 載入歷史指標
        self._load_metrics()
        
    def _load_metrics(self):
        """載入歷史性能指標"""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for key, values in data.items():
                        self.metrics[key].extend(values)
        except Exception as e:
            self.logger.error(f"載入性能指標失敗：{str(e)}")
            
    def save_metrics(self):
        """儲存性能指標"""
        try:
            with open(self.metrics_file, "w", encoding="utf-8") as f:
                json.dump(dict(self.metrics), f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"儲存性能指標失敗：{str(e)}")
            
    def start_operation(self, operation_name: str):
        """開始追蹤操作時間
        
        Args:
            operation_name: 操作名稱
        """
        self.start_times[operation_name] = time.time()
        
    def end_operation(self, operation_name: str):
        """結束追蹤操作時間並記錄
        
        Args:
            operation_name: 操作名稱
        """
        if operation_name in self.start_times:
            duration = time.time() - self.start_times[operation_name]
            self.record_metric(f"{operation_name}_duration", duration)
            del self.start_times[operation_name]
            
    def record_metric(self, name: str, value: float):
        """記錄性能指標
        
        Args:
            name: 指標名稱
            value: 指標值
        """
        timestamp = datetime.now(self.timezone).isoformat()
        self.metrics[name].append({
            "timestamp": timestamp,
            "value": value
        })
        
    def get_metrics_summary(self) -> Dict[str, Dict[str, float]]:
        """獲取性能指標摘要
        
        Returns:
            Dict: 包含各指標的統計資訊
        """
        summary = {}
        for name, values in self.metrics.items():
            if values:
                numeric_values = [v["value"] for v in values]
                summary[name] = {
                    "min": min(numeric_values),
                    "max": max(numeric_values),
                    "avg": sum(numeric_values) / len(numeric_values),
                    "count": len(numeric_values)
                }
        return summary
        
    def cleanup_old_metrics(self, days: int = 30):
        """清理舊的性能指標
        
        Args:
            days: 保留天數
        """
        current_time = datetime.now(self.timezone)
        for name in list(self.metrics.keys()):
            self.metrics[name] = [
                metric for metric in self.metrics[name]
                if (current_time - datetime.fromisoformat(metric["timestamp"])).days < days
            ]
        self.save_metrics()

class SystemMonitor:
    """系統監控器"""
    
    def __init__(self, config_path: str = ".env"):
        self.logger = logging.getLogger(__name__)
        self.alerts = []
        self.config_path = config_path
        self.performance = PerformanceMonitor()
        
    def check_api_keys(self) -> bool:
        """檢查 API 金鑰設定
        
        Returns:
            bool: 是否所有必要的 API 金鑰都已設定
        """
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                content = f.read()
                required_keys = [
                    "OPENAI_API_KEY",
                    "THREADS_ACCESS_TOKEN",
                    "THREADS_APP_ID",
                    "THREADS_APP_SECRET"
                ]
                
                for key in required_keys:
                    if key not in content or f"{key}=" in content:
                        self.add_alert("error", f"缺少必要的 API 金鑰：{key}")
                        return False
                        
            return True
        except Exception as e:
            self.add_alert("error", f"檢查 API 金鑰時發生錯誤：{str(e)}")
            return False
            
    def check_memory_usage(self) -> Dict[str, Any]:
        """檢查記憶體使用情況
        
        Returns:
            Dict: 記憶體使用資訊
        """
        try:
            memory_info = {}
            
            # 檢查記憶檔案大小
            memory_file = Path("memory/interactions.json")
            if memory_file.exists():
                memory_info["file_size"] = memory_file.stat().st_size / 1024  # KB
                
                if memory_info["file_size"] > 1024:  # 如果大於 1MB
                    self.add_alert("warning", "記憶檔案大小超過 1MB，建議進行清理")
                    
            # 檢查記錄數量
            if memory_file.exists():
                with open(memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    memory_info["record_count"] = sum(len(records) for records in data.values())
                    
            return memory_info
        except Exception as e:
            self.add_alert("error", f"檢查記憶體使用時發生錯誤：{str(e)}")
            return {}
            
    def add_alert(self, level: str, message: str):
        """添加警告訊息
        
        Args:
            level: 警告等級 (info/warning/error)
            message: 警告訊息
        """
        timestamp = datetime.now(pytz.UTC).isoformat()
        self.alerts.append({
            "timestamp": timestamp,
            "level": level,
            "message": message
        })
        
        # 根據等級記錄日誌
        if level == "error":
            self.logger.error(message)
        elif level == "warning":
            self.logger.warning(message)
        else:
            self.logger.info(message)
            
    def get_system_status(self) -> Dict[str, Any]:
        """獲取系統狀態摘要
        
        Returns:
            Dict: 系統狀態資訊
        """
        return {
            "api_keys_valid": self.check_api_keys(),
            "memory_usage": self.check_memory_usage(),
            "performance_metrics": self.performance.get_metrics_summary(),
            "recent_alerts": self.alerts[-10:] if self.alerts else []
        }
        
    def cleanup(self):
        """清理系統資源"""
        self.performance.cleanup_old_metrics()
        self.alerts = [] 