FROM python:3.11-slim

LABEL maintainer="ThreadsPoster Team"
LABEL version="1.1.6"
LABEL description="自動 Threads 發文系統"

# 設置工作目錄
WORKDIR /app

# 設置時區為台北
ENV TZ=Asia/Taipei
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安裝必要的系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴檔案
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -U pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# 複製應用程式代碼
COPY . .

# 創建日誌目錄
RUN mkdir -p logs

# 設置執行權限
RUN chmod +x run.sh

# 設置環境變數
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO

# 入口點
ENTRYPOINT ["./run.sh"]
