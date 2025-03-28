"""
ThreadsPoster API 處理模組
處理與 Threads API 的所有互動
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
        self.base_url = "https://graph.threads.net/v1.0"
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

    async def get_new_replies(self) -> List[Dict]:
        """獲取新回覆"""
        try:
            logging.info("正在獲取新回覆")
            url = f"{self.base_url}/me/threads"
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
        """建立新貼文 (兩步驟流程)"""
        try:
            await self._init_session()
            
            # 步驟 1: 建立媒體容器
            container_url = f"{self.base_url}/me/threads"
            container_params = {
                "access_token": self.config.THREADS_ACCESS_TOKEN,
                "media_type": "TEXT",
                "text": text
            }
            
            logging.info(f"正在建立媒體容器，請求 URL: {container_url}")
            logging.info(f"貼文內容: {text}")
            
            container_response = await self.session.post(container_url, params=container_params)
            container_text = await container_response.text()
            
            logging.info(f"媒體容器回應: 狀態碼 {container_response.status}")
            logging.info(f"媒體容器回應內容: {container_text}")
            
            if container_response.status != 200:
                logging.error(f"建立媒體容器失敗：狀態碼 {container_response.status}，回應內容：{container_text}")
                return ""
                
            try:
                container_data = await container_response.json()
                container_id = container_data.get("id")
                
                if not container_id:
                    logging.error("無法獲取媒體容器 ID")
                    return ""
                    
                logging.info(f"媒體容器建立成功，ID: {container_id}")
                
                # 等待 10 秒讓伺服器處理媒體容器
                logging.info("等待 10 秒讓伺服器處理媒體容器...")
                await asyncio.sleep(10)
                
                # 步驟 2: 發布媒體容器
                publish_url = f"{self.base_url}/me/threads_publish"
                publish_params = {
                    "access_token": self.config.THREADS_ACCESS_TOKEN,
                    "creation_id": container_id
                }
                
                logging.info(f"正在發布媒體容器，請求 URL: {publish_url}")
                
                publish_response = await self.session.post(publish_url, params=publish_params)
                publish_text = await publish_response.text()
                
                logging.info(f"發布回應: 狀態碼 {publish_response.status}")
                logging.info(f"發布回應內容: {publish_text}")
                
                if publish_response.status != 200:
                    logging.error(f"發布媒體容器失敗：狀態碼 {publish_response.status}，回應內容：{publish_text}")
                    return ""
                    
                publish_data = await publish_response.json()
                post_id = publish_data.get("id", "")
                logging.info(f"貼文成功發布，ID: {post_id}")
                return post_id
                
            except json.JSONDecodeError as e:
                logging.error(f"解析回應 JSON 失敗：{str(e)}")
                return ""
            
        except Exception as e:
            logging.error(f"發布貼文時發生錯誤：{str(e)}")
            return ""
        finally:
            await self._close_session()
            
    async def reply_to_post(self, post_id: str, text: str) -> bool:
        """回覆貼文"""
        try:
            # 步驟 1: 建立回覆容器
            container_url = f"{self.base_url}/me/threads"
            container_params = {
                "access_token": self.config.THREADS_ACCESS_TOKEN,
                "media_type": "TEXT",
                "text": text,
                "in_reply_to": post_id
            }
            
            await self._init_session()
            container_response = await self.session.post(container_url, params=container_params)
            
            if container_response.status != 200:
                logging.error(f"建立回覆容器失敗：{container_response.status}")
                return False
                
            container_data = await container_response.json()
            container_id = container_data.get("id")
            
            if not container_id:
                logging.error("無法獲取回覆容器 ID")
                return False
                
            # 等待 30 秒讓伺服器處理媒體容器
            await asyncio.sleep(30)
            
            # 步驟 2: 發布回覆容器
            publish_url = f"{self.base_url}/me/threads_publish"
            publish_params = {
                "access_token": self.config.THREADS_ACCESS_TOKEN,
                "creation_id": container_id
            }
            
            publish_response = await self.session.post(publish_url, params=publish_params)
            
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