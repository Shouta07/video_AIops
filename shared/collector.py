"""
統合データ収集

全チャネル（Threads / Instagram / Web）の成果データを収集し、
Google Sheetsに記録する。

使い方:
  python -m shared.collector --channel threads
  python -m shared.collector --channel instagram
  python -m shared.collector --channel web
  python -m shared.collector --all
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta


# ── Threads データ収集 ──

def collect_threads(days=1):
    """Threads API から投稿の成果データを収集"""
    from shared.sheets import append_threads_post
    from shared.hypothesis import detect_hypothesis

    access_token = os.environ.get("THREADS_ACCESS_TOKEN")
    if not access_token:
        print("  ⚠️  THREADS_ACCESS_TOKEN が未設定")
        return []

    try:
        import requests
    except ImportError:
        print("  pip install requests が必要です")
        return []

    # ユーザーの投稿一覧を取得
    url = "https://graph.threads.net/v1.0/me/threads"
    params = {
        "fields": "id,text,timestamp,likes,replies,reposts",
        "access_token": access_token,
        "limit": 25,
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"  ❌ Threads API エラー: {response.status_code}")
        return []

    posts = response.json().get("data", [])
    collected = []

    for post in posts:
        post_time = post.get("timestamp", "")
        text = post.get("text", "")

        # 投稿ごとのインサイト取得
        insight_url = f"https://graph.threads.net/v1.0/{post['id']}/insights"
        insight_params = {
            "metric": "views,likes,replies,reposts,quotes",
            "access_token": access_token,
        }
        insight_resp = requests.get(insight_url, params=insight_params)
        metrics = {}
        if insight_resp.status_code == 200:
            for m in insight_resp.json().get("data", []):
                metrics[m["name"]] = m.get("values", [{}])[0].get("value", 0)

        hypothesis = detect_hypothesis(text)
        impressions = metrics.get("views", 0)
        likes = metrics.get("likes", 0)
        replies = metrics.get("replies", 0)
        saves = metrics.get("reposts", 0) + metrics.get("quotes", 0)

        data = {
            "date": post_time[:10] if post_time else datetime.now().strftime("%Y-%m-%d"),
            "time": post_time[11:16] if len(post_time) > 11 else "",
            "text": text[:100],
            "hypothesis": hypothesis or "",
            "cta_type": "",
            "impressions": impressions,
            "likes": likes,
            "replies": replies,
            "saves": saves,
            "profile_visits": 0,
            "engagement_rate": round((likes + replies + saves) / max(impressions, 1) * 100, 2),
            "save_rate": round(saves / max(impressions, 1) * 100, 2),
        }

        append_threads_post(data)
        collected.append(data)

    print(f"  ✅ Threads: {len(collected)}件の投稿データを収集")
    return collected


# ── Instagram データ収集 ──

def collect_instagram(days=1):
    """Instagram Graph API から投稿の成果データを収集"""
    from shared.sheets import append_instagram_post
    from shared.hypothesis import detect_hypothesis

    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    ig_user_id = os.environ.get("INSTAGRAM_USER_ID")

    if not access_token or not ig_user_id:
        print("  ⚠️  INSTAGRAM_ACCESS_TOKEN / INSTAGRAM_USER_ID が未設定")
        return []

    try:
        import requests
    except ImportError:
        print("  pip install requests が必要です")
        return []

    # メディア一覧
    url = f"https://graph.instagram.com/v21.0/{ig_user_id}/media"
    params = {
        "fields": "id,caption,media_type,timestamp,like_count,comments_count",
        "access_token": access_token,
        "limit": 25,
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"  ❌ Instagram API エラー: {response.status_code}")
        return []

    posts = response.json().get("data", [])
    collected = []

    for post in posts:
        caption = post.get("caption", "")
        media_type = post.get("media_type", "")

        # インサイト取得
        insight_url = f"https://graph.instagram.com/v21.0/{post['id']}/insights"
        insight_params = {
            "metric": "impressions,reach,saved,shares,plays",
            "access_token": access_token,
        }
        insight_resp = requests.get(insight_url, params=insight_params)
        metrics = {}
        if insight_resp.status_code == 200:
            for m in insight_resp.json().get("data", []):
                metrics[m["name"]] = m.get("values", [{}])[0].get("value", 0)

        hypothesis = detect_hypothesis(caption)
        impressions = metrics.get("impressions", 0)
        reach = metrics.get("reach", 0)
        saves = metrics.get("saved", 0)
        shares = metrics.get("shares", 0)
        plays = metrics.get("plays", 0)

        data = {
            "date": post.get("timestamp", "")[:10],
            "type": media_type,
            "caption": caption[:100],
            "hypothesis": hypothesis or "",
            "reel_type": "",
            "reach": reach,
            "impressions": impressions,
            "likes": post.get("like_count", 0),
            "comments": post.get("comments_count", 0),
            "saves": saves,
            "shares": shares,
            "plays": plays,
            "profile_visits": 0,
            "follows": 0,
            "engagement_rate": round(
                (post.get("like_count", 0) + post.get("comments_count", 0) + saves)
                / max(reach, 1) * 100, 2
            ),
        }

        append_instagram_post(data)
        collected.append(data)

    print(f"  ✅ Instagram: {len(collected)}件の投稿データを収集")
    return collected


# ── Web Analytics データ収集 ──

def collect_web(days=7):
    """Google Analytics 4 + Search Console からデータ収集"""
    from shared.sheets import append_web_analytics

    ga_property = os.environ.get("GA4_PROPERTY_ID")
    sc_site = os.environ.get("SEARCH_CONSOLE_SITE")
    creds_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials.json")

    collected = []

    # GA4
    if ga_property and os.path.exists(creds_path):
        try:
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
            from google.analytics.data_v1beta.types import (
                RunReportRequest, DateRange, Dimension, Metric
            )
            from google.oauth2.service_account import Credentials

            creds = Credentials.from_service_account_file(creds_path)
            client = BetaAnalyticsDataClient(credentials=creds)

            request = RunReportRequest(
                property=f"properties/{ga_property}",
                dimensions=[Dimension(name="pagePath"), Dimension(name="sessionSource")],
                metrics=[
                    Metric(name="screenPageViews"),
                    Metric(name="totalUsers"),
                    Metric(name="averageSessionDuration"),
                    Metric(name="bounceRate"),
                ],
                date_ranges=[DateRange(
                    start_date=f"{days}daysAgo",
                    end_date="today"
                )],
            )

            response = client.run_report(request)
            today = datetime.now().strftime("%Y-%m-%d")

            for row in response.rows:
                data = {
                    "date": today,
                    "page": row.dimension_values[0].value,
                    "source": row.dimension_values[1].value,
                    "pageviews": int(row.metric_values[0].value),
                    "unique_visitors": int(row.metric_values[1].value),
                    "avg_time_on_page": round(float(row.metric_values[2].value), 1),
                    "bounce_rate": round(float(row.metric_values[3].value), 2),
                }
                append_web_analytics(data)
                collected.append(data)

            print(f"  ✅ GA4: {len(collected)}ページのデータを収集")
        except ImportError:
            print("  ⚠️  GA4 API パッケージ未インストール: pip install google-analytics-data")
        except Exception as e:
            print(f"  ⚠️  GA4 エラー: {e}")

    # Search Console
    if sc_site and os.path.exists(creds_path):
        try:
            from googleapiclient.discovery import build
            from google.oauth2.service_account import Credentials

            creds = Credentials.from_service_account_file(
                creds_path,
                scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
            )
            service = build("searchconsole", "v1", credentials=creds)

            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            request = {
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["query", "page"],
                "rowLimit": 100,
            }

            response = service.searchanalytics().query(
                siteUrl=sc_site, body=request
            ).execute()

            sc_collected = 0
            for row in response.get("rows", []):
                data = {
                    "date": end_date,
                    "page": row["keys"][1] if len(row["keys"]) > 1 else "",
                    "search_query": row["keys"][0],
                    "clicks": row.get("clicks", 0),
                    "impressions": row.get("impressions", 0),
                    "position": round(row.get("position", 0), 1),
                }
                append_web_analytics(data)
                sc_collected += 1

            print(f"  ✅ Search Console: {sc_collected}クエリのデータを収集")
            collected.extend([{"source": "search_console"}] * sc_collected)
        except ImportError:
            print("  ⚠️  Search Console パッケージ未インストール: pip install google-api-python-client")
        except Exception as e:
            print(f"  ⚠️  Search Console エラー: {e}")

    if not collected:
        print("  ⚠️  Web: データ収集なし（API未設定）")

    return collected


# ── 全チャネル一括収集 ──

def collect_all():
    """全チャネルのデータを一括収集"""
    print("\n  📊 全チャネルデータ収集中...")
    threads = collect_threads()
    instagram = collect_instagram()
    web = collect_web()
    return {
        "threads": threads,
        "instagram": instagram,
        "web": web,
        "collected_at": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="統合データ収集")
    parser.add_argument("--channel", choices=["threads", "instagram", "web"])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()

    if args.all:
        collect_all()
    elif args.channel == "threads":
        collect_threads(args.days)
    elif args.channel == "instagram":
        collect_instagram(args.days)
    elif args.channel == "web":
        collect_web(args.days)
    else:
        parser.print_help()
