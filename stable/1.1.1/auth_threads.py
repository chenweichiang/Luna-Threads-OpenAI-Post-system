import os
import logging
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import requests
from dotenv import load_dotenv
import json
import time

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 載入環境變數
load_dotenv()

class AuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """處理授權回調"""
        try:
            # 解析 URL 參數
            query_components = parse_qs(urlparse(self.path).query)
            
            # 檢查是否收到授權碼
            if 'code' in query_components:
                code = query_components['code'][0]
                logger.info("收到授權碼")
                
                # 交換授權碼獲取 access token
                token_url = "https://graph.threads.net/oauth/access_token"
                data = {
                    'client_id': os.getenv('THREADS_APP_ID'),
                    'client_secret': os.getenv('THREADS_APP_SECRET'),
                    'code': code,
                    'grant_type': 'authorization_code',
                    'redirect_uri': os.getenv('THREADS_REDIRECT_URI')
                }
                
                response = requests.post(token_url, data=data)
                response.raise_for_status()
                token_data = response.json()
                
                # 將 access token 寫入 .env 文件
                with open('.env', 'r') as file:
                    env_lines = file.readlines()
                
                token_line_found = False
                for i, line in enumerate(env_lines):
                    if line.startswith('THREADS_TOKEN='):
                        env_lines[i] = f"THREADS_TOKEN={token_data['access_token']}\n"
                        token_line_found = True
                        break
                
                if not token_line_found:
                    env_lines.append(f"\nTHREADS_TOKEN={token_data['access_token']}\n")
                
                with open('.env', 'w') as file:
                    file.writelines(env_lines)
                
                logger.info("成功獲取並保存 access token")
                
                # 返回成功頁面
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write("授權成功！您可以關閉此視窗。".encode('utf-8'))
                
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write("未收到授權碼".encode('utf-8'))
                
        except Exception as e:
            logger.error(f"處理授權回調時發生錯誤: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write("處理授權時發生錯誤。請檢查日誌。".encode('utf-8'))

def start_auth_server():
    """啟動授權伺服器並開啟授權視窗"""
    try:
        # 解析重定向 URI 獲取主機和端口
        redirect_uri = urlparse(os.getenv('THREADS_REDIRECT_URI'))
        host = redirect_uri.hostname
        port = redirect_uri.port
        
        # 啟動授權伺服器
        server = HTTPServer((host, port), AuthHandler)
        logger.info(f"授權伺服器啟動於 {host}:{port}")
        
        # 構建授權 URL
        auth_url = (
            "https://threads.net/oauth/authorize?"
            f"client_id={os.getenv('THREADS_APP_ID')}&"
            f"redirect_uri={os.getenv('THREADS_REDIRECT_URI')}&"
            f"scope={os.getenv('THREADS_SCOPES')}&"
            "response_type=code"
        )
        
        # 開啟瀏覽器進行授權
        logger.info("開啟瀏覽器進行授權...")
        webbrowser.open(auth_url)
        
        # 啟動伺服器
        server.serve_forever()
        
    except KeyboardInterrupt:
        logger.info("伺服器已停止")
        server.server_close()
    except Exception as e:
        logger.error(f"啟動授權伺服器時發生錯誤: {str(e)}")

if __name__ == "__main__":
    start_auth_server() 