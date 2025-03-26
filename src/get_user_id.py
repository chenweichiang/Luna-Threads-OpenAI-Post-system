import os
import requests
from dotenv import load_dotenv
import logging

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 載入環境變數
load_dotenv()

def get_user_id():
    access_token = os.getenv('THREADS_TOKEN')
    base_url = "https://graph.facebook.com/v19.0"
    
    try:
        url = f"{base_url}/me"
        params = {
            'access_token': access_token,
            'fields': 'id,name,accounts{instagram_business_account{id,username}}'
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"API 回應: {data}")
        
        # 獲取 Instagram Business Account ID
        if 'accounts' in data and 'data' in data['accounts']:
            ig_account = data['accounts']['data'][0]['instagram_business_account']
            logger.info(f"你的 Threads 用戶 ID 是: {ig_account['id']}")
            logger.info(f"你的 Threads 用戶名稱是: {ig_account['username']}")
        else:
            logger.error("無法獲取 Instagram Business Account ID")
            
    except Exception as e:
        logger.error(f"獲取用戶 ID 失敗: {str(e)}")
        if hasattr(e, 'response'):
            logger.error(f"錯誤詳情: {e.response.text}")

if __name__ == "__main__":
    get_user_id() 