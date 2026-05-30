"""
Instagram Graph API 投稿モジュール

リール / フィード / ストーリーズの投稿を自動化。
動画はURLでホストされている必要がある（ローカルファイル不可）。

使い方:
  python instagram/poster.py --type reel --video-url "https://..." --caption "テキスト"
  python instagram/poster.py --type image --image-url "https://..." --caption "テキスト"

環境変数:
  INSTAGRAM_ACCESS_TOKEN: Meta Graph APIのアクセストークン
  INSTAGRAM_USER_ID: InstagramビジネスアカウントのID
"""
import argparse
import json
import os
import sys
import time

try:
    import requests
except ImportError:
    print("pip install requests が必要です")
    sys.exit(1)

API_BASE = "https://graph.instagram.com/v21.0"


def get_credentials():
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    user_id = os.environ.get("INSTAGRAM_USER_ID")
    if not token or not user_id:
        print("  ❌ INSTAGRAM_ACCESS_TOKEN と INSTAGRAM_USER_ID が必要です")
        return None, None
    return token, user_id


# ── リール投稿 ──

def post_reel(video_url, caption, share_to_feed=True):
    """リール動画を投稿"""
    token, user_id = get_credentials()
    if not token:
        return None

    print(f"  📤 リール投稿中...")

    # Step 1: メディアコンテナ作成
    create_url = f"{API_BASE}/{user_id}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": share_to_feed,
        "access_token": token,
    }

    response = requests.post(create_url, data=payload)
    if response.status_code != 200:
        print(f"  ❌ コンテナ作成失敗: {response.json()}")
        return None

    container_id = response.json().get("id")
    print(f"    コンテナID: {container_id}")

    # Step 2: 動画処理を待機
    print(f"    動画処理中...")
    for _ in range(30):  # 最大5分待機
        status_url = f"{API_BASE}/{container_id}"
        status_params = {"fields": "status_code", "access_token": token}
        status_resp = requests.get(status_url, params=status_params)
        status = status_resp.json().get("status_code")

        if status == "FINISHED":
            break
        elif status == "ERROR":
            print(f"  ❌ 動画処理エラー: {status_resp.json()}")
            return None

        time.sleep(10)

    # Step 3: 公開
    publish_url = f"{API_BASE}/{user_id}/media_publish"
    publish_payload = {
        "creation_id": container_id,
        "access_token": token,
    }
    publish_resp = requests.post(publish_url, data=publish_payload)

    if publish_resp.status_code == 200:
        media_id = publish_resp.json().get("id")
        print(f"  ✅ リール投稿完了: {media_id}")
        return media_id
    else:
        print(f"  ❌ 公開失敗: {publish_resp.json()}")
        return None


# ── 画像投稿 ──

def post_image(image_url, caption):
    """画像を投稿"""
    token, user_id = get_credentials()
    if not token:
        return None

    print(f"  📤 画像投稿中...")

    create_url = f"{API_BASE}/{user_id}/media"
    payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": token,
    }

    response = requests.post(create_url, data=payload)
    if response.status_code != 200:
        print(f"  ❌ コンテナ作成失敗: {response.json()}")
        return None

    container_id = response.json().get("id")

    publish_url = f"{API_BASE}/{user_id}/media_publish"
    publish_resp = requests.post(publish_url, data={
        "creation_id": container_id,
        "access_token": token,
    })

    if publish_resp.status_code == 200:
        media_id = publish_resp.json().get("id")
        print(f"  ✅ 画像投稿完了: {media_id}")
        return media_id
    else:
        print(f"  ❌ 公開失敗: {publish_resp.json()}")
        return None


# ── カルーセル投稿 ──

def post_carousel(image_urls, caption):
    """カルーセル（複数画像）を投稿"""
    token, user_id = get_credentials()
    if not token:
        return None

    print(f"  📤 カルーセル投稿中（{len(image_urls)}枚）...")

    # 各画像のコンテナ作成
    children_ids = []
    for url in image_urls:
        create_url = f"{API_BASE}/{user_id}/media"
        payload = {
            "image_url": url,
            "is_carousel_item": True,
            "access_token": token,
        }
        response = requests.post(create_url, data=payload)
        if response.status_code == 200:
            children_ids.append(response.json().get("id"))

    if not children_ids:
        print("  ❌ カルーセルアイテムの作成に失敗")
        return None

    # カルーセルコンテナ作成
    carousel_url = f"{API_BASE}/{user_id}/media"
    carousel_payload = {
        "media_type": "CAROUSEL",
        "children": ",".join(children_ids),
        "caption": caption,
        "access_token": token,
    }
    carousel_resp = requests.post(carousel_url, data=carousel_payload)

    if carousel_resp.status_code != 200:
        print(f"  ❌ カルーセル作成失敗: {carousel_resp.json()}")
        return None

    container_id = carousel_resp.json().get("id")

    # 公開
    publish_url = f"{API_BASE}/{user_id}/media_publish"
    publish_resp = requests.post(publish_url, data={
        "creation_id": container_id,
        "access_token": token,
    })

    if publish_resp.status_code == 200:
        media_id = publish_resp.json().get("id")
        print(f"  ✅ カルーセル投稿完了: {media_id}")
        return media_id
    else:
        print(f"  ❌ 公開失敗: {publish_resp.json()}")
        return None


# ── インサイト取得 ──

def get_insights(media_id):
    """投稿のインサイトを取得"""
    token, _ = get_credentials()
    if not token:
        return {}

    url = f"{API_BASE}/{media_id}/insights"
    params = {
        "metric": "impressions,reach,saved,shares,plays,likes,comments,total_interactions",
        "access_token": token,
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        return {}

    metrics = {}
    for m in response.json().get("data", []):
        metrics[m["name"]] = m.get("values", [{}])[0].get("value", 0)

    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Instagram投稿")
    parser.add_argument("--type", choices=["reel", "image", "carousel"], required=True)
    parser.add_argument("--video-url", help="動画URL（リール用）")
    parser.add_argument("--image-url", help="画像URL")
    parser.add_argument("--image-urls", nargs="+", help="複数画像URL（カルーセル用）")
    parser.add_argument("--caption", required=True, help="キャプション")
    args = parser.parse_args()

    if args.type == "reel":
        post_reel(args.video_url, args.caption)
    elif args.type == "image":
        post_image(args.image_url, args.caption)
    elif args.type == "carousel":
        post_carousel(args.image_urls, args.caption)
