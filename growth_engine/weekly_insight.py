#!/usr/bin/env python3
"""
Weekly Insight Report 自動生成

毎週日曜に実行。全チャネルのデータを集計し、
仮説スコア・チャネル別KPI・推奨アクションを自動生成。

使い方:
  python growth_engine/weekly_insight.py
  python growth_engine/weekly_insight.py --week 2026-W23
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.hypothesis import HYPOTHESES, calculate_hypothesis_scores, rank_hypotheses
from shared.sheets import get_all_data, append_weekly_insight


def generate_weekly_insight(week_label=None):
    """週次インサイトレポートを生成"""
    if not week_label:
        week_label = datetime.now().strftime("%Y-W%W")

    print(f"\n{'═' * 55}")
    print(f"  His Recoveries Weekly Insight")
    print(f"  Week: {week_label}")
    print(f"{'═' * 55}")

    # データ取得
    threads_data = get_all_data("threads_posts")
    instagram_data = get_all_data("instagram_posts")
    web_data = get_all_data("web_analytics")

    # ── 1. 仮説スコアリング ──

    all_posts = []
    for post in threads_data:
        all_posts.append({
            "hypothesis": post.get("hypothesis", ""),
            "impressions": int(post.get("impressions", 0)),
            "saves": int(post.get("saves", 0)),
            "comments": int(post.get("replies", 0)),
            "likes": int(post.get("likes", 0)),
            "channel": "threads",
        })
    for post in instagram_data:
        all_posts.append({
            "hypothesis": post.get("hypothesis", ""),
            "impressions": int(post.get("impressions", 0)),
            "saves": int(post.get("saves", 0)),
            "comments": int(post.get("comments", 0)),
            "likes": int(post.get("likes", 0)),
            "channel": "instagram",
        })

    scores = calculate_hypothesis_scores(all_posts)
    ranked = rank_hypotheses(scores)

    print(f"\n  【最も反応の良い仮説】")
    for hid, data in ranked[:3]:
        hyp = HYPOTHESES.get(hid, {})
        print(f"    #{data['rank']} {hyp.get('name', hid)} — 保存率 {data['avg_save_rate']}%, スコア {data['score']}")
        print(f"       {data['stars']} ({data['confidence_pct']}%)")

    # ── 2. チャネル別KPI ──

    threads_imp = sum(int(p.get("impressions", 0)) for p in threads_data)
    threads_count = len(threads_data)
    ig_reach = sum(int(p.get("reach", 0)) for p in instagram_data)
    ig_count = len(instagram_data)
    web_pv = sum(int(p.get("pageviews", 0)) for p in web_data)

    print(f"\n  【チャネル別パフォーマンス】")
    print(f"    Threads:   imp {threads_imp:,}, 投稿 {threads_count}本")
    print(f"    Instagram: reach {ig_reach:,}, 投稿 {ig_count}本")
    print(f"    Web:       PV {web_pv:,}")

    # ── 3. CTA分析 ──

    cta_data = get_all_data("cta_results")
    best_cta = ""
    if cta_data:
        cta_scores = {}
        for c in cta_data:
            cta_type = c.get("cta_type", "")
            if cta_type:
                cta_scores.setdefault(cta_type, []).append(
                    float(c.get("profile_rate", 0))
                )
        if cta_scores:
            best_cta = max(cta_scores, key=lambda k: sum(cta_scores[k]) / len(cta_scores[k]))
            print(f"\n  【最もCVRの高いCTA】")
            print(f"    {best_cta}: プロフ遷移 {sum(cta_scores[best_cta]) / len(cta_scores[best_cta]):.1f}%")

    # ── 4. 推奨アクション生成 ──

    recommendations = generate_recommendations(ranked, threads_imp, ig_reach, web_pv)
    print(f"\n  【来週の推奨アクション】")
    for i, rec in enumerate(recommendations, 1):
        print(f"    {i}. {rec}")

    # ── 5. 事業仮説の確信度 ──

    print(f"\n  【事業仮説の確信度】")
    for hid, data in ranked:
        hyp = HYPOTHESES.get(hid, {})
        status = "有力" if data["confidence_pct"] >= 70 else "要追加検証" if data["confidence_pct"] >= 40 else "データ不足"
        print(f"    {hyp.get('name', hid)}: {data['stars']} ({data['confidence_pct']}%) — {status}")

    print(f"\n{'═' * 55}\n")

    # Sheetsに記録
    top = ranked[0] if ranked else ("", {})
    insight = {
        "week": week_label,
        "top_hypothesis": top[0],
        "threads_imp": threads_imp,
        "threads_growth": "",
        "instagram_reach": ig_reach,
        "instagram_growth": "",
        "web_pv": web_pv,
        "web_growth": "",
        "best_cta": best_cta,
        "recommendations": " / ".join(recommendations[:3]),
    }
    append_weekly_insight(insight)

    # レポートファイル保存
    report_dir = "reports"
    os.makedirs(report_dir, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = os.path.join(report_dir, f"weekly_insight_{today}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "week": week_label,
            "hypothesis_ranking": [{"id": hid, **data} for hid, data in ranked],
            "channels": {
                "threads": {"impressions": threads_imp, "posts": threads_count},
                "instagram": {"reach": ig_reach, "posts": ig_count},
                "web": {"pageviews": web_pv},
            },
            "best_cta": best_cta,
            "recommendations": recommendations,
        }, f, ensure_ascii=False, indent=2)

    print(f"  📊 レポート保存: {report_path}")
    return insight


def generate_recommendations(ranked, threads_imp, ig_reach, web_pv):
    """データに基づいた推奨アクションを生成"""
    recs = []

    if ranked:
        top_hid = ranked[0][0]
        top_hyp = HYPOTHESES.get(top_hid, {})

        recs.append(f"「{top_hyp.get('name', '')}」テーマの記事をWebに公開")
        recs.append(f"Threadsで「{top_hyp.get('name', '')}」を深掘りする投稿")

        if ig_reach == 0:
            recs.append("Instagram開設準備（リール3本ストック）")
        else:
            recs.append(f"「{top_hyp.get('name', '')}」テーマのリールを投稿")

    if threads_imp < 1000:
        recs.append("Threads投稿頻度を上げる（1日2→3投稿を試す）")

    if web_pv < 100:
        seo_kw = ranked[0][0] if ranked else "hygiene"
        hyp = HYPOTHESES.get(seo_kw, {})
        if hyp.get("seo_keywords"):
            recs.append(f"SEO記事「{hyp['seo_keywords'][0]}」を優先公開")

    return recs[:5]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Weekly Insight Report 自動生成")
    parser.add_argument("--week", help="週ラベル（例: 2026-W23）")
    args = parser.parse_args()

    generate_weekly_insight(args.week)
