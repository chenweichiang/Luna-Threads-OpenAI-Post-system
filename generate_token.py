import requests
import json

def generate_access_token():
    """生成新的 access token"""
    
    # 應用程式資訊
    app_id = "524787033609652"
    app_secret = "f0d89aa460150ecfcae767189d09350c"
    
    try:
        # 1. 使用應用程式憑證獲取 access token
        print("\n1. 獲取應用程式 access token...")
        token_url = "https://graph.facebook.com/v19.0/oauth/access_token"
        params = {
            "client_id": app_id,
            "client_secret": app_secret,
            "grant_type": "client_credentials"
        }
        
        response = requests.get(token_url, params=params)
        response.raise_for_status()
        token_data = response.json()
        
        if "access_token" in token_data:
            print("成功獲取 access token！")
            print(f"\n您的新 access token：\n{token_data['access_token']}")
            
            # 2. 測試新的 token
            print("\n2. 測試新的 token...")
            test_url = "https://graph.facebook.com/v19.0/me"
            headers = {
                "Authorization": f"Bearer {token_data['access_token']}"
            }
            test_response = requests.get(test_url, headers=headers)
            test_response.raise_for_status()
            print("Token 測試成功！")
            
            return token_data["access_token"]
        else:
            print("獲取 token 失敗！")
            print(json.dumps(token_data, indent=2))
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"\n發生錯誤：{str(e)}")
        if hasattr(e.response, "json"):
            error_data = e.response.json()
            print(f"錯誤詳情：{json.dumps(error_data, indent=2)}")
        return None

if __name__ == "__main__":
    generate_access_token() 