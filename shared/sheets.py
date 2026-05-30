"""
Google Sheets 統合DB

全チャネルのデータをSheetsに記録・取得する共通モジュール。
10シート構成でHis Recoveries Growth Engineのデータ基盤となる。

環境変数:
  GOOGLE_SHEETS_ID: スプレッドシートID
  GOOGLE_SERVICE_ACCOUNT_JSON: サービスアカウントのJSONパス
"""
import json
import os
from datetime import datetime

# シート名定義
SHEETS = {
    "threads_posts": "threads_posts",
    "instagram_posts": "instagram_posts",
    "web_analytics": "web_analytics",
    "hypothesis_scores": "hypothesis_scores",
    "cta_results": "cta_results",
    "content_calendar": "content_calendar",
    "funnel": "funnel",
    "weekly_insights": "weekly_insights",
    "trends": "trends",
    "revenue": "revenue",
}


def _get_client():
    """Google Sheets APIクライアントを取得"""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        print("  必要パッケージ: pip install gspread google-auth")
        return None, None

    creds_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials.json")
    sheet_id = os.environ.get("GOOGLE_SHEETS_ID")

    if not os.path.exists(creds_path):
        print(f"  ⚠️  認証ファイルが見つかりません: {creds_path}")
        return None, None
    if not sheet_id:
        print("  ⚠️  GOOGLE_SHEETS_ID が未設定です")
        return None, None

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(sheet_id)
    return client, spreadsheet


def _get_or_create_sheet(spreadsheet, sheet_name, headers=None):
    """シートを取得。なければ作成"""
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except Exception:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
        if headers:
            worksheet.append_row(headers)
    return worksheet


# ── 書き込み ──

def append_threads_post(data):
    """Threads投稿データを記録"""
    _, spreadsheet = _get_client()
    if not spreadsheet:
        return _fallback_write("threads_posts", data)

    headers = ["date", "time", "text", "hypothesis", "cta_type",
               "impressions", "likes", "replies", "saves", "profile_visits",
               "engagement_rate", "save_rate"]
    ws = _get_or_create_sheet(spreadsheet, SHEETS["threads_posts"], headers)
    row = [data.get(h, "") for h in headers]
    ws.append_row(row)


def append_instagram_post(data):
    """Instagram投稿データを記録"""
    _, spreadsheet = _get_client()
    if not spreadsheet:
        return _fallback_write("instagram_posts", data)

    headers = ["date", "type", "caption", "hypothesis", "reel_type",
               "reach", "impressions", "likes", "comments", "saves", "shares",
               "plays", "profile_visits", "follows", "engagement_rate"]
    ws = _get_or_create_sheet(spreadsheet, SHEETS["instagram_posts"], headers)
    row = [data.get(h, "") for h in headers]
    ws.append_row(row)


def append_web_analytics(data):
    """Webアナリティクスデータを記録"""
    _, spreadsheet = _get_client()
    if not spreadsheet:
        return _fallback_write("web_analytics", data)

    headers = ["date", "page", "pageviews", "unique_visitors", "avg_time_on_page",
               "bounce_rate", "source", "search_query", "position", "clicks", "impressions"]
    ws = _get_or_create_sheet(spreadsheet, SHEETS["web_analytics"], headers)
    row = [data.get(h, "") for h in headers]
    ws.append_row(row)


def update_hypothesis_scores(scores):
    """仮説スコアを更新"""
    _, spreadsheet = _get_client()
    if not spreadsheet:
        return _fallback_write("hypothesis_scores", scores)

    headers = ["date", "hypothesis", "score", "posts", "avg_save_rate",
               "avg_engagement", "total_impressions", "rank", "confidence"]
    ws = _get_or_create_sheet(spreadsheet, SHEETS["hypothesis_scores"], headers)

    today = datetime.now().strftime("%Y-%m-%d")
    for hid, data in scores.items():
        row = [today, hid, data.get("score", 0), data.get("posts", 0),
               data.get("avg_save_rate", 0), data.get("avg_engagement", 0),
               data.get("total_impressions", 0), data.get("rank", 0),
               data.get("confidence_pct", 0)]
        ws.append_row(row)


def update_content_calendar(calendar_data):
    """コンテンツカレンダーを更新"""
    _, spreadsheet = _get_client()
    if not spreadsheet:
        return _fallback_write("content_calendar", calendar_data)

    headers = ["week", "day", "channel", "hypothesis", "content_type",
               "title", "status", "scheduled_time"]
    ws = _get_or_create_sheet(spreadsheet, SHEETS["content_calendar"], headers)

    for entry in calendar_data:
        row = [entry.get(h, "") for h in headers]
        ws.append_row(row)


def append_weekly_insight(insight):
    """週次インサイトを記録"""
    _, spreadsheet = _get_client()
    if not spreadsheet:
        return _fallback_write("weekly_insights", insight)

    headers = ["week", "top_hypothesis", "threads_imp", "threads_growth",
               "instagram_reach", "instagram_growth", "web_pv", "web_growth",
               "best_cta", "recommendations"]
    ws = _get_or_create_sheet(spreadsheet, SHEETS["weekly_insights"], headers)
    row = [insight.get(h, "") for h in headers]
    ws.append_row(row)


def append_funnel(funnel_data):
    """CVRファネルデータを記録"""
    _, spreadsheet = _get_client()
    if not spreadsheet:
        return _fallback_write("funnel", funnel_data)

    headers = ["date", "channel", "impressions", "profile_visits", "web_transitions",
               "article_reads", "affiliate_clicks", "conversions",
               "profile_rate", "web_rate", "read_rate", "click_rate", "conv_rate"]
    ws = _get_or_create_sheet(spreadsheet, SHEETS["funnel"], headers)
    row = [funnel_data.get(h, "") for h in headers]
    ws.append_row(row)


def append_revenue(data):
    """収益データを記録"""
    _, spreadsheet = _get_client()
    if not spreadsheet:
        return _fallback_write("revenue", data)

    headers = ["month", "affiliate_revenue", "session_revenue", "total",
               "affiliate_clicks", "affiliate_cvr", "top_product"]
    ws = _get_or_create_sheet(spreadsheet, SHEETS["revenue"], headers)
    row = [data.get(h, "") for h in headers]
    ws.append_row(row)


# ── 読み取り ──

def get_all_data(sheet_name):
    """シートの全データを取得"""
    _, spreadsheet = _get_client()
    if not spreadsheet:
        return _fallback_read(sheet_name)

    ws = spreadsheet.worksheet(sheet_name)
    return ws.get_all_records()


# ── フォールバック（Sheets未接続時はローカルJSON） ──

FALLBACK_DIR = "data"


def _fallback_write(sheet_name, data):
    """Sheets未接続時のフォールバック: ローカルJSONに追記"""
    os.makedirs(FALLBACK_DIR, exist_ok=True)
    filepath = os.path.join(FALLBACK_DIR, f"{sheet_name}.json")

    existing = []
    if os.path.exists(filepath):
        with open(filepath, encoding="utf-8") as f:
            existing = json.load(f)

    if isinstance(data, dict):
        existing.append(data)
    elif isinstance(data, list):
        existing.extend(data)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def _fallback_read(sheet_name):
    """フォールバック読み取り"""
    filepath = os.path.join(FALLBACK_DIR, f"{sheet_name}.json")
    if os.path.exists(filepath):
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    return []
