import os
import re

def fix_imports(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修正 from src. 開頭的導入
    content = re.sub(r'from src\.', 'from ', content)
    
    # 修正 import src. 開頭的導入
    content = re.sub(r'import src\.', 'import ', content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def process_directory(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                print(f"處理檔案: {file_path}")
                fix_imports(file_path)

if __name__ == "__main__":
    # 處理 src 目錄下的所有 Python 檔案
    process_directory('.') 