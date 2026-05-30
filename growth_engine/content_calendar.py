#!/usr/bin/env python3
"""
コンテンツカレンダー自動生成

仮説スコアに基づいて、週間コンテンツカレンダーを自動生成。
Threads / Instagram / Web の投稿を曜日ごとに割り当て。

使い方:
  python growth_engine/content_calendar.py
  python growth_engine/content_calendar.py --week 2026-W24
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.hypothesis import HYPOTHESES, calculate_hypothesis_scores, rank_hypotheses
from shared.sheets import get_all_data, update_content_calendar

# 曜日スケジュールテンプレート
SCHEDULE_TEMPLATE = {
    "月": {"threads_am": True, "threads_pm": True, "instagram": "リール",    "web": None},
    "火": {"threads_am": True, "threads_pm": True, "instagram": "ストーリーズ", "web": "記事公開"},
    "水": {"threads_am": True, "threads_pm": True, "instagram": "リール",    "web": None},
    "木": {"threads_am": True, "threads_pm": True, "instagram": "カルーセル", "web": "記事公開"},
    "金": {"threads_am": True, "threads_pm": True, "instagram": "リール",    "web": None},
    "土": {"threads_am": None, "threads_pm": True, "instagram": "ストーリーズ", "web": None},
    "日": {"threads_am": None, "threads_pm": None, "instagram": None,       "web": "週次レポート"},
}

DAYS_JP = ["月", "火", "水", "木", "金", "土", "日"]


def generate_calendar(week_label=None):
    """仮説スコアに基づいたコンテンツカレンダーを生成"""
    if not week_label:
        today = datetime.now()
        next_monday = today + timedelta(days=(7 - today.weekday()))
        week_label = next_monday.strftime("%Y-W%W")

    print(f"\n{'═' * 60}")
    print(f"  コンテンツカレンダー — {week_label}")
    print(f"{'═' * 60}")

    # 仮説スコア取得
    all_posts = get_all_data("threads_posts") + get_all_data("instagram_posts")
    posts_for_scoring = []
    for p in all_posts:
        posts_for_scoring.append({
            "hypothesis": p.get("hypothesis", ""),
            "impressions": int(p.get("impressions", 0)),
            "saves": int(p.get("saves", 0)),
            "comments": int(p.get("comments", p.get("replies", 0))),
            "likes": int(p.get("likes", 0)),
        })

    scores = calculate_hypothesis_scores(posts_for_scoring)
    ranked = rank_hypotheses(scores)

    # スコア上位の仮説を優先的にカレンダーに配置
    top_hypotheses = [hid for hid, _ in ranked if scores[hid]["score"] > 0]
    # データ不足の仮説も混ぜる（Discovery用）
    discovery = [hid for hid in HYPOTHESES if hid not in top_hypotheses]
    hypothesis_pool = top_hypotheses + discovery

    # カレンダー生成
    calendar = []
    hyp_idx = 0

    for day in DAYS_JP:
        sched = SCHEDULE_TEMPLATE[day]

        # Threads AM
        if sched["threads_am"]:
            h = hypothesis_pool[hyp_idx % len(hypothesis_pool)]
            hyp_idx += 1
            calendar.append({
                "week": week_label,
                "day": day,
                "channel": "Threads",
                "hypothesis": h,
                "content_type": "AM投稿 (07:30)",
                "title": f"{HYPOTHESES[h]['name']}系: {HYPOTHESES[h]['insight'][:20]}...",
                "status": "予定",
                "scheduled_time": "07:30",
            })

        # Threads PM
        if sched["threads_pm"]:
            h = hypothesis_pool[hyp_idx % len(hypothesis_pool)]
            hyp_idx += 1
            calendar.append({
                "week": week_label,
                "day": day,
                "channel": "Threads",
                "hypothesis": h,
                "content_type": "PM投稿 (22:30)",
                "title": f"{HYPOTHESES[h]['name']}系: 共感・深掘り",
                "status": "予定",
                "scheduled_time": "22:30",
            })

        # Instagram
        if sched["instagram"]:
            h = hypothesis_pool[hyp_idx % len(hypothesis_pool)]
            hyp_idx += 1
            ig_type = sched["instagram"]
            calendar.append({
                "week": week_label,
                "day": day,
                "channel": "Instagram",
                "hypothesis": h,
                "content_type": ig_type,
                "title": f"{HYPOTHESES[h]['name']}系 {ig_type}",
                "status": "予定",
                "scheduled_time": "19:00",
            })

        # Web
        if sched["web"] and sched["web"] != "週次レポート":
            h = top_hypotheses[0] if top_hypotheses else hypothesis_pool[0]
            seo_kw = HYPOTHESES[h].get("seo_keywords", [""])[0]
            calendar.append({
                "week": week_label,
                "day": day,
                "channel": "Web",
                "hypothesis": h,
                "content_type": sched["web"],
                "title": f"SEO記事: 「{seo_kw}」",
                "status": "予定",
                "scheduled_time": "10:00",
            })

    # 表示
    print(f"\n  {'曜日':4s} {'Threads AM':20s} {'Threads PM':20s} {'Instagram':15s} {'Web':15s}")
    print(f"  {'─' * 74}")

    for day in DAYS_JP:
        day_entries = [c for c in calendar if c["day"] == day]
        threads_am = next((c for c in day_entries if "AM" in c.get("content_type", "")), None)
        threads_pm = next((c for c in day_entries if "PM" in c.get("content_type", "")), None)
        ig = next((c for c in day_entries if c["channel"] == "Instagram"), None)
        web = next((c for c in day_entries if c["channel"] == "Web"), None)

        ta = HYPOTHESES.get(threads_am["hypothesis"], {}).get("name", "—") if threads_am else "—"
        tp = HYPOTHESES.get(threads_pm["hypothesis"], {}).get("name", "—") if threads_pm else "—"
        ig_text = f"{ig['content_type']}/{HYPOTHESES.get(ig['hypothesis'], {}).get('name', '')}" if ig else "—"
        web_text = web["content_type"] if web else "—"

        print(f"  {day:4s} {ta:20s} {tp:20s} {ig_text:15s} {web_text:15s}")

    print(f"\n  合計: {len(calendar)}コンテンツ")

    # Sheets に保存
    update_content_calendar(calendar)

    # JSON保存
    os.makedirs("reports", exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    cal_path = f"reports/calendar_{today}.json"
    with open(cal_path, "w", encoding="utf-8") as f:
        json.dump(calendar, f, ensure_ascii=False, indent=2)
    print(f"  📅 保存: {cal_path}")

    return calendar


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="コンテンツカレンダー自動生成")
    parser.add_argument("--week", help="週ラベル")
    args = parser.parse_args()
    generate_calendar(args.week)
