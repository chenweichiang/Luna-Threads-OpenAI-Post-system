"""
Version: 2024.03.30
Author: ThreadsPoster Team
Description: Threads API 介面，處理與 Threads 平台的所有互動
Last Modified: 2024.03.30
Changes:
- 優化 API 請求處理
- 加強錯誤重試機制
- 改進回應處理邏輯
- 優化連接管理
- 加強安全性驗證
"""

import logging
import aiohttp
import json
from datetime import datetime
import pytz
from typing import Dict, List, Optional, Union
import uuid
import asyncio

from src.config import Config
from src.exceptions import APIError, ValidationError

logger = logging.getLogger(__name__)

class ThreadsAPI:
    """Threads API 客戶端"""
    
    def __init__(self, config):
        self.config = config
        self.base_url = "https://graph.threads.net/v1.0"  # 更新為正確的 API 端點
        self.session = None
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        self.timezone = pytz.timezone(config.SYSTEM_CONFIG['timezone'])
        
    async def initialize(self):
        """初始化 API 客戶端"""
        try:
            await self._init_session()
            # 驗證 API 憑證
            if not self.config.THREADS_ACCESS_TOKEN:
                raise ValidationError("缺少 Threads API 存取令牌")
            logger.info("Threads API 客戶端初始化成功")
            return True
        except Exception as e:
            logger.error(f"Threads API 客戶端初始化失敗: {str(e)}")
            return False
        
    async def _init_session(self):
        """初始化 session"""
        if self.session is None:
            self.session = aiohttp.ClientSession(headers=self.headers)
            
    async def _close_session(self):
        """關閉 session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def close(self):
        """關閉 API 客戶端"""
        await self._close_session()
            
    async def get_new_replies(self) -> List[Dict]:
        """獲取新回覆"""
        try:
            logging.info("正在獲取新回覆")
            url = f"{self.base_url}/{self.config.THREADS_USER_ID}/threads"
            params = {
                "access_token": self.config.THREADS_ACCESS_TOKEN,
                "fields": "id,text,from{username},created_time"
            }
            
            await self._init_session()
            response = await self.session.get(url, params=params)
            if response.status == 200:
                data = await response.json()
                replies = []
                for item in data.get("data", []):
                    replies.append({
                        "id": item["id"],
                        "username": item.get("from", {}).get("username"),
                        "text": item.get("text"),
                        "created_at": item.get("created_time")
                    })
                return replies
            else:
                logging.error(f"獲取回覆失敗: {response.status}")
                return []
        except Exception as e:
            logging.error(f"獲取回覆時發生錯誤: {str(e)}")
            return []
            
    async def create_post(self, text: str) -> str:
        """建立新貼文"""
        try:
            await self._init_session()
            
            # 步驟 1: 建立媒體容器
            container_url = f"{self.base_url}/{self.config.THREADS_USER_ID}/threads"
            params = {'access_token': self.config.THREADS_ACCESS_TOKEN}
            data = {
                'text': text,
                'media_type': 'TEXT'
            }
            
            logger.info(f"正在建立媒體容器，內容: {text}")
            async with self.session.post(container_url, params=params, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"建立媒體容器失敗: {error_text}")
                    return None
                    
                container_data = await response.json()
                container_id = container_data.get('id')
                
                if not container_id:
                    logger.error("無法獲取媒體容器 ID")
                    return None
                
                logger.info(f"媒體容器建立成功，ID: {container_id}")
                
                # 步驟 2: 等待 30 秒讓伺服器處理媒體容器
                await asyncio.sleep(30)
                
                # 步驟 3: 發布媒體容器
                publish_url = f"{self.base_url}/{self.config.THREADS_USER_ID}/threads_publish"
                publish_params = {
                    'access_token': self.config.THREADS_ACCESS_TOKEN,
                    'creation_id': container_id
                }
                
                async with self.session.post(publish_url, params=publish_params) as publish_response:
                    if publish_response.status != 200:
                        error_text = await publish_response.text()
                        logger.error(f"發布媒體容器失敗: {error_text}")
                        return None
                    
                    publish_data = await publish_response.json()
                    post_id = publish_data.get('id')
                    
                    if not post_id:
                        logger.error("無法獲取發文 ID")
                        return None
                        
                    logger.info(f"貼文發布成功，ID: {post_id}")
                    return post_id
                
        except Exception as e:
            logger.error(f"建立貼文時發生錯誤: {str(e)}")
            return None
        finally:
            await self._close_session()
            
    async def reply_to_post(self, post_id: str, text: str) -> bool:
        """回覆貼文"""
        try:
            # 步驟 1: 建立回覆容器
            container_url = f"{self.base_url}/{self.config.THREADS_USER_ID}/threads"
            container_params = {
                "access_token": self.config.THREADS_ACCESS_TOKEN,
                "media_type": "TEXT",
                "text": text,
                "in_reply_to": post_id
            }
            
            await self._init_session()
            async with self.session.post(container_url, params=container_params) as response:
                if response.status != 200:
                    logging.error(f"建立回覆容器失敗：{response.status}")
                    return False
                
                container_data = await response.json()
                container_id = container_data.get("id")
                
                if not container_id:
                    logging.error("無法獲取回覆容器 ID")
                    return False
                
                # 等待 30 秒讓伺服器處理媒體容器
                await asyncio.sleep(30)
                
                # 步驟 2: 發布回覆容器
                publish_url = f"{self.base_url}/{self.config.THREADS_USER_ID}/threads_publish"
                publish_params = {
                    "access_token": self.config.THREADS_ACCESS_TOKEN,
                    "creation_id": container_id
                }
                
                async with self.session.post(publish_url, params=publish_params) as publish_response:
                    if publish_response.status != 200:
                        logging.error(f"發布回覆容器失敗：{publish_response.status}")
                        return False
                    
                    return True
                
        except Exception as e:
            logging.error(f"回覆貼文時發生錯誤：{str(e)}")
            return False
        finally:
            await self._close_session()
            
    async def get_user_info(self) -> Dict:
        """獲取用戶資訊"""
        try:
            url = f"{self.base_url}/me"
            params = {
                "access_token": self.config.THREADS_ACCESS_TOKEN,
                "fields": "id,username,name,profile_picture_url"
            }
            
            await self._init_session()
            response = await self.session.get(url, params=params)
            if response.status == 200:
                return await response.json()
            else:
                logging.error(f"獲取用戶資訊失敗：{response.status}")
                return {}
        except Exception as e:
            logging.error(f"獲取用戶資訊時發生錯誤：{str(e)}")
            return {}