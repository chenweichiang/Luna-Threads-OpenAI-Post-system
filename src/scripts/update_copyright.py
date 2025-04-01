#!/usr/bin/env python3
"""
版權信息更新工具

此腳本用於更新所有源碼檔案中的版權聲明和修改日期。
"""

import os
import re
import sys
from datetime import datetime
import argparse

def update_file(file_path, year, author):
    """更新文件的版權信息
    
    Args:
        file_path: 檔案路徑
        year: 版權年份
        author: 版權作者
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # 檢查是否有版權聲明模式
    version_pattern = r'Version:\s+[\d\.]+\s+\(v[\d\.]+\)'
    version_match = re.search(version_pattern, content)
    
    last_modified_pattern = r'Last Modified:\s+[\d\.\-]+'
    last_modified_match = re.search(last_modified_pattern, content)
    
    copyright_pattern = r'Copyright \(c\) \d{4}.*?(?=\n)'
    copyright_match = re.search(copyright_pattern, content)
    
    current_date = datetime.now().strftime('%Y.%m.%d')
    
    # 如果找到version標記，就更新Last Modified
    if version_match and last_modified_match:
        # 更新Last Modified日期
        new_content = re.sub(
            last_modified_pattern,
            f'Last Modified: {current_date}',
            content
        )
        
        # 如果有版權聲明，更新版權年份
        if copyright_match:
            new_content = re.sub(
                copyright_pattern,
                f'Copyright (c) {year} {author}',
                new_content
            )
        
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
                
    return False

def find_python_files(directory):
    """找出所有Python檔案
    
    Args:
        directory: 目錄路徑
        
    Returns:
        list: Python檔案列表
    """
    python_files = []
    
    for root, dirs, files in os.walk(directory):
        # 忽略venv目錄
        if 'venv' in dirs:
            dirs.remove('venv')
        # 忽略.git目錄
        if '.git' in dirs:
            dirs.remove('.git')
        # 忽略__pycache__目錄
        if '__pycache__' in dirs:
            dirs.remove('__pycache__')
            
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
                
    return python_files

def main():
    parser = argparse.ArgumentParser(description='更新版權信息')
    parser.add_argument('--year', type=str, default=datetime.now().strftime('%Y'),
                        help='版權年份')
    parser.add_argument('--author', type=str, default='Chiang, Chenwei',
                        help='版權作者')
    parser.add_argument('--directory', type=str, default='.',
                        help='要掃描的目錄')
    
    args = parser.parse_args()
    
    # 找出源代碼目錄
    if os.path.exists(os.path.join(args.directory, 'src')):
        source_dir = os.path.join(args.directory, 'src')
    else:
        source_dir = args.directory
        
    # 找出測試目錄
    tests_dir = None
    if os.path.exists(os.path.join(args.directory, 'tests')):
        tests_dir = os.path.join(args.directory, 'tests')
    
    # 找出所有Python檔案
    python_files = find_python_files(source_dir)
    
    # 加入測試檔案
    if tests_dir:
        python_files.extend(find_python_files(tests_dir))
    
    # 更新每個檔案
    updated_count = 0
    for file_path in python_files:
        if update_file(file_path, args.year, args.author):
            print(f"Updated {file_path}")
            updated_count += 1
    
    print(f"更新了 {updated_count} 個檔案的版權信息")
    
if __name__ == "__main__":
    main() 