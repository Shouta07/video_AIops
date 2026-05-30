#!/usr/bin/env python3
"""
CVRファネル分析

各チャネルのファネル（imp → プロフ → Web → 記事読了 → アフィクリック → 成約）を
計算してレポートする。

使い方:
  python growth_engine/funnel.py
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.sheets import get_all_data, append_funnel


def calculate_funnel():
    """チャネル別CVRファネルを計算"""
    print(f"\n{'═' * 55}")
    print(f"  CVR ファネル分析")
    print(f"{'═' * 55}")

    channels = {
        "threads": {
            "data": get_all_data("threads_posts"),
            "imp_key": "impressions",
        },
        "instagram": {
            "data": get_all_data("instagram_posts"),
            "imp_key": "reach",
        },
    }

    web_data = get_all_data("web_analytics")
    total_web_pv = sum(int(p.get("pageviews", 0)) for p in web_data)

    today = datetime.now().strftime("%Y-%m-%d")

    for channel_name, channel in channels.items():
        data = channel["data"]
        if not data:
            continue

        imp = sum(int(p.get(channel["imp_key"], 0)) for p in data)
        profile_visits = sum(int(p.get("profile_visits", 0)) for p in data)

        # 推定値（実データがない場合の仮定）
        if profile_visits == 0:
            profile_rate = 3.0 if channel_name == "threads" else 5.0
            profile_visits = int(imp * profile_rate / 100)

        web_transitions = int(profile_visits * 0.1)  # プロフ→Web: 10%推定
        article_reads = int(web_transitions * 0.5)     # Web→記事読了: 50%推定
        affiliate_clicks = int(article_reads * 0.2)    # 読了→クリック: 20%推定
        conversions = int(affiliate_clicks * 0.33)     # クリック→成約: 33%推定

        funnel_data = {
            "date": today,
            "channel": channel_name,
            "impressions": imp,
            "profile_visits": profile_visits,
            "web_transitions": web_transitions,
            "article_reads": article_reads,
            "affiliate_clicks": affiliate_clicks,
            "conversions": conversions,
            "profile_rate": round(profile_visits / max(imp, 1) * 100, 1),
            "web_rate": round(web_transitions / max(profile_visits, 1) * 100, 1),
            "read_rate": round(article_reads / max(web_transitions, 1) * 100, 1),
            "click_rate": round(affiliate_clicks / max(article_reads, 1) * 100, 1),
            "conv_rate": round(conversions / max(affiliate_clicks, 1) * 100, 1),
        }

        append_funnel(funnel_data)

        print(f"\n  {channel_name.upper()}")
        print(f"  imp: {imp:,}")
        print(f"    → プロフ訪問: {profile_visits:,} ({funnel_data['profile_rate']}%)")
        print(f"      → Web遷移: {web_transitions:,} ({funnel_data['web_rate']}%)")
        print(f"        → 記事読了: {article_reads:,} ({funnel_data['read_rate']}%)")
        print(f"          → アフィクリック: {affiliate_clicks:,} ({funnel_data['click_rate']}%)")
        print(f"            → 成約: {conversions:,} ({funnel_data['conv_rate']}%)")

    print(f"\n{'═' * 55}\n")


if __name__ == "__main__":
    calculate_funnel()
