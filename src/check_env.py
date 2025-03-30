"""檢查環境變數是否存在並有效"""
import os
import sys
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

required_vars = [
    "OPENAI_API_KEY",
    "THREADS_ACCESS_TOKEN",
    "THREADS_USER_ID",
    "MONGODB_URI"
]

missing_vars = []
for var in required_vars:
    if not os.getenv(var):
        missing_vars.append(var)

if missing_vars:
    print(f"錯誤：缺少以下必要的環境變數: {', '.join(missing_vars)}")
    sys.exit(1)
else:
    print("環境變數檢查通過")
    sys.exit(0) 