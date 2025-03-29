from flask import Flask, request
import os
import requests
from dotenv import load_dotenv
import ssl

app = Flask(__name__)
load_dotenv()

@app.route('/auth/')
def auth():
    # 獲取授權碼
    code = request.args.get('code')
    if not code:
        return '授權失敗：沒有收到授權碼'
    
    # 交換存取權杖
    token_url = 'https://graph.threads.net/oauth/access_token'
    data = {
        'client_id': os.getenv('THREADS_APP_ID'),
        'client_secret': os.getenv('THREADS_APP_SECRET'),
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': 'https://localhost:8443/auth/'
    }
    
    response = requests.post(token_url, data=data)
    result = response.json()
    
    if 'access_token' in result:
        # 將存取權杖寫入 .env 檔案
        with open('.env', 'r') as f:
            lines = f.readlines()
        
        token_line_found = False
        for i, line in enumerate(lines):
            if line.startswith('THREADS_ACCESS_TOKEN='):
                lines[i] = f'THREADS_ACCESS_TOKEN={result["access_token"]}\n'
                token_line_found = True
                break
        
        if not token_line_found:
            lines.append(f'THREADS_ACCESS_TOKEN={result["access_token"]}\n')
        
        with open('.env', 'w') as f:
            f.writelines(lines)
        
        return '授權成功！存取權杖已更新。'
    else:
        return f'授權失敗：{result.get("error_message", "未知錯誤")}'

if __name__ == '__main__':
    # 生成自簽名的 SSL 憑證
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    print(f'請使用此網址進行授權：\nhttps://threads.net/oauth/authorize?client_id={os.getenv("THREADS_APP_ID")}&redirect_uri=https://localhost:8443/auth/&scope=threads_basic,threads_content_publish&response_type=code')
    
    app.run(host='0.0.0.0', port=8443, ssl_context=context) 