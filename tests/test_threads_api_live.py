"""
Threads API 實際測試腳本
"""

import logging
import time
from datetime import datetime
from src.config import Config
from src.threads_api import ThreadsAPI

def format_reply(reply: dict, indent: str = "") -> None:
    """格式化並顯示回覆資訊"""
    print(f"{indent}- {reply.get('text')} (by {reply.get('username')})")
    print(f"{indent}  讚數: {reply.get('like_count', 0)}")
    print(f"{indent}  時間: {datetime.strptime(reply.get('timestamp'), '%Y-%m-%dT%H:%M:%S%z').strftime('%Y-%m-%d %H:%M:%S')}")
    
    if reply.get("has_replies"):
        print(f"{indent}  子回覆:")
        for sub_reply in reply.get("replies", []):
            format_reply(sub_reply, indent + "    ")

def check_and_reply_to_posts(api: ThreadsAPI, user_info: dict) -> None:
    """檢查並回覆貼文

    Args:
        api (ThreadsAPI): API 客戶端
        user_info (dict): 用戶資訊
    """
    # 獲取最新的貼文
    posts = api.get_user_posts(limit=25)
    if not posts:
        print("無法獲取貼文")
        return
        
    print(f"成功獲取 {len(posts)} 則貼文")
    
    # 檢查每個貼文的回覆
    for post in posts:
        print(f"\n檢查貼文 {post.get('id')} 的回覆...")
        post_replies = api.get_post_replies(post.get('id'))
        
        if post_replies:
            print(f"找到 {len(post_replies)} 則回覆:")
            for reply in post_replies:
                print(f"- ID: {reply.get('id')}")
                print(f"  內容: {reply.get('text')}")
                print(f"  作者: {reply.get('username')}")
                print(f"  回覆給: {reply.get('replied_to')}")
                print()
                
            # 如果找到其他用戶的回覆，就回覆它
            for reply in post_replies:
                if reply.get('username') != user_info.get('username'):
                    print("\n=== 回覆其他用戶 ===")
                    reply_text = f"謝謝你的回覆，{reply.get('username')}！"
                    new_reply_id = api.create_reply(reply.get('id'), reply_text)
                    
                    if new_reply_id:
                        print(f"成功建立回覆，ID: {new_reply_id}")
                    else:
                        print("建立回覆失敗")
                    return
        else:
            print("尚未有回覆")

def main():
    # 設定日誌
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # 初始化設定和 API
    config = Config()
    api = ThreadsAPI(config)

    print("\n=== 檢查權限 ===")
    user_info = api.get_user_info()
    if user_info:
        print(f"用戶名稱: {user_info.get('username')}")
        print(f"用戶 ID: {user_info.get('id')}")
    else:
        print("無法獲取用戶資訊")
        return

    print("\n=== 檢查發布限制 ===")
    limit_info = api.get_publishing_limit()
    if limit_info:
        print(f"已使用 {limit_info.get('quota_usage', 0)} / {limit_info.get('quota_total', 0)} 則貼文")
    else:
        print("無法獲取發布限制資訊")
        return

    # 每 30 秒檢查一次回覆
    check_interval = 30  # 檢查間隔（秒）
    try:
        while True:
            print(f"\n=== 檢查回覆（{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}）===")
            check_and_reply_to_posts(api, user_info)
            print(f"\n等待 {check_interval} 秒後再次檢查...")
            time.sleep(check_interval)
    except KeyboardInterrupt:
        print("\n程式已停止")
    except Exception as e:
        print(f"\n發生錯誤: {str(e)}")
    finally:
        print("所有測試完成")

if __name__ == "__main__":
    main() 