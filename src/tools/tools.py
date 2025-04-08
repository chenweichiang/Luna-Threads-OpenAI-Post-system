#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Version: 2024.03.31 (v1.1.7)
Author: ThreadsPoster Team
Description: 統一命令行工具入口
Last Modified: 2024.03.31
Changes:
- 創建統一工具入口
- 整合各工具腳本功能
- 使用src中的功能替代獨立工具腳本
"""

import os
import sys
import argparse
import asyncio

# 添加專案根目錄到路徑，以便能夠導入相關模組
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from config import Config
from db_handler import DatabaseHandler
from utils import check_latest_posts
from tools.test_time_settings import test_settings

async def run_check_posts():
    """執行檢查最近文章功能"""
    config = Config()
    db = DatabaseHandler(config)
    await db.initialize()
    
    try:
        await check_latest_posts(db, 3, True)
    finally:
        await db.close()

def main():
    """主函數：解析命令行參數並執行相應工具"""
    parser = argparse.ArgumentParser(description='ThreadsPoster 系統工具')
    
    # 添加各個工具的命令行選項
    parser.add_argument('--check-posts', action='store_true', help='檢查最近的文章')
    parser.add_argument('--test-time', action='store_true', help='測試時間設定')
    parser.add_argument('--all', action='store_true', help='執行所有工具')
    
    args = parser.parse_args()
    
    # 如果沒有指定參數，顯示幫助信息
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    # 執行選定的工具
    if args.check_posts or args.all:
        print("=== 檢查最近的文章 ===")
        asyncio.run(run_check_posts())
        print("\n")
    
    if args.test_time or args.all:
        print("=== 測試時間設定 ===")
        test_settings()
        print("\n")
    
    print("工具執行完成")

if __name__ == "__main__":
    main() 