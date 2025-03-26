ThreadsPoster 文件
=================

ThreadsPoster 是一個基於 AI 的 Threads 自動回覆與內容發布系統。系統透過角色設定，使用 OpenAI 來自動回覆 Threads 上的訊息，並能根據設定的時間規律自動發布新的內容。

功能特點
-------

* 自動回覆：根據角色設定自動回覆其他用戶的訊息
* 智能發文：根據時間和角色設定自動發布新的內容
* 記憶系統：記住與每個用戶的互動歷史
* 時間規律：根據不同時段調整回覆時間
* 角色扮演：維持一致的角色人設

目錄
----

.. toctree::
   :maxdepth: 2
   :caption: 內容:

   installation
   configuration
   usage
   api
   modules

安裝
----

1. 克隆專案::

    git clone https://github.com/chenweichiang/AI-Tools-ThreadsPoster.git
    cd AI-Tools-ThreadsPoster

2. 安裝相依套件::

    pip install -r requirements.txt

3. 設定環境變數::

    cp .env.example .env
    # 編輯 .env 文件，填入必要的設定值

使用方法
-------

1. 啟動系統::

    python src/main.py

2. 系統會自動：

   * 檢查新的回覆
   * 根據角色設定生成回應
   * 在適當的時間發布回應
   * 定期發布新的內容

貢獻
----

歡迎提交 Issue 或 Pull Request 來改進這個專案。

授權
----

本專案採用 MIT 授權條款。 