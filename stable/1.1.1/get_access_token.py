import os
import logging
import json
import http.server
import socketserver
import webbrowser
import urllib.parse
import requests
from dotenv import load_dotenv

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        """處理 OAuth 回調"""
        try:
            # 解析 URL 參數
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            
            # 檢查是否有錯誤
            if 'error' in params:
                error = params['error'][0]
                error_description = params.get('error_description', ['未知錯誤'])[0]
                logger.error(f"授權失敗: {error} - {error_description}")
                self.send_response(400)
                self.end_headers()
                self.wfile.write(f"授權失敗: {error_description}".encode())
                return
            
            # 獲取授權碼
            code = params.get('code', [None])[0]
            if not code:
                logger.error("未收到授權碼")
                self.send_response(400)
                self.end_headers()
                self.wfile.write("未收到授權碼".encode())
                return
            
            logger.info(f"收到授權碼: {code}")
            
            # 使用授權碼獲取 access token
            load_dotenv()
            token_url = "https://graph.facebook.com/v19.0/oauth/access_token"
            token_params = {
                'client_id': os.getenv('THREADS_APP_ID'),
                'client_secret': os.getenv('THREADS_APP_SECRET'),
                'redirect_uri': os.getenv('THREADS_REDIRECT_URI'),
                'code': code
            }
            
            response = requests.get(token_url, params=token_params)
            response.raise_for_status()
            token_data = response.json()
            
            # 保存 token
            with open('access_token.json', 'w') as f:
                json.dump(token_data, f, indent=2)
            
            logger.info("Access token 已保存")
            
            # 回應成功訊息
            self.send_response(200)
            self.end_headers()
            self.wfile.write("授權成功！您可以關閉此視窗。".encode())
            
        except Exception as e:
            logger.error(f"處理回調時發生錯誤: {str(e)}", exc_info=True)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"發生錯誤: {str(e)}".encode())
        finally:
            # 關閉伺服器
            self.server.shutdown()

def main():
    """主程序"""
    try:
        # 載入環境變數
        load_dotenv()
        
        # 檢查必要的環境變數
        required_vars = ['THREADS_APP_ID', 'THREADS_APP_SECRET', 'THREADS_REDIRECT_URI', 'THREADS_SCOPES']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"缺少必要的環境變數: {', '.join(missing_vars)}")
        
        # 啟動 OAuth 伺服器
        port = 8000
        with socketserver.TCPServer(("localhost", port), OAuthCallbackHandler) as httpd:
            logger.info(f"OAuth 伺服器已啟動於 http://localhost:{port}")
            
            # 構建授權 URL
            redirect_uri = os.getenv('THREADS_REDIRECT_URI')
            auth_url = (
                "https://www.facebook.com/v19.0/dialog/oauth"
                f"?client_id={os.getenv('THREADS_APP_ID')}"
                f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
                f"&scope={os.getenv('THREADS_SCOPES')}"
                "&response_type=code"
            )
            
            logger.info(f"請在瀏覽器中完成授權: {auth_url}")
            webbrowser.open(auth_url)
            
            # 等待回調
            httpd.serve_forever()
            
    except Exception as e:
        logger.error(f"程序執行失敗: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main() 