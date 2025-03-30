#!/usr/bin/env python3
"""
Version: 2025.03.31 (v1.1.9)
Author: ThreadsPoster Team
Description: 版權與版本更新工具
Copyright (c) 2025 Chiang, Chenwei. All rights reserved.
License: MIT License
Last Modified: 2025.03.31
"""

import os
import re
import sys
from datetime import datetime

VERSION = "2025.03.31 (v1.1.9)"
COPYRIGHT = "Copyright (c) 2025 Chiang, Chenwei. All rights reserved."
LICENSE = "MIT License"
LAST_MODIFIED = f"Last Modified: {datetime.now().strftime('%Y.%m.%d')}"

def update_file_header(file_path):
    """更新檔案標頭的版權和版本信息
    
    Args:
        file_path: 檔案路徑
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 判斷是否含有註解塊
        docstring_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
        if not docstring_match:
            print(f"跳過文件 {file_path} (沒有文檔字符串)")
            return
            
        docstring = docstring_match.group(1)
        
        # 更新版本號
        new_docstring = re.sub(r'Version:.*?(\n|$)', f'Version: {VERSION}\\1', docstring)
        
        # 更新版權信息(如果存在)
        if re.search(r'Copyright.*?(\n|$)', new_docstring):
            new_docstring = re.sub(r'Copyright.*?(\n|$)', f'{COPYRIGHT}\\1', new_docstring)
        else:
            new_docstring = re.sub(r'(Author:.*?(\n|$))', f'\\1{COPYRIGHT}\\2', new_docstring)
            
        # 更新授權信息(如果存在)
        if re.search(r'License:.*?(\n|$)', new_docstring):
            new_docstring = re.sub(r'License:.*?(\n|$)', f'{LICENSE}\\1', new_docstring)
        else:
            new_docstring = re.sub(r'(Copyright.*?(\n|$))', f'\\1{LICENSE}\\2', new_docstring)
            
        # 更新最後修改日期
        if re.search(r'Last Modified:.*?(\n|$)', new_docstring):
            new_docstring = re.sub(r'Last Modified:.*?(\n|$)', f'{LAST_MODIFIED}\\1', new_docstring)
        else:
            # 沒有最後修改日期的話添加
            if "Changes:" in new_docstring:
                new_docstring = re.sub(r'(Changes:)', f'{LAST_MODIFIED}\n\\1', new_docstring)
            else:
                new_docstring += f"\n{LAST_MODIFIED}"
                
        # 更新整個文件內容
        new_content = content.replace(docstring_match.group(1), new_docstring)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        print(f"已更新檔案: {file_path}")
    except Exception as e:
        print(f"更新檔案 {file_path} 時出錯: {str(e)}")

def process_directory(directory):
    """處理目錄下的所有 Python 文件
    
    Args:
        directory: 目錄路徑
    """
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                update_file_header(file_path)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
        if os.path.isfile(target) and target.endswith('.py'):
            update_file_header(target)
        elif os.path.isdir(target):
            process_directory(target)
        else:
            print(f"無效的目標: {target}")
    else:
        # 默認處理 src 目錄
        src_directory = "src"
        if os.path.isdir(src_directory):
            process_directory(src_directory)
            print(f"已完成處理 {src_directory} 目錄下的所有 Python 文件")
        else:
            print(f"找不到 {src_directory} 目錄") 