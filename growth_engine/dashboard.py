#!/usr/bin/env python3
"""
統合ダッシュボード（CLI版）

全チャネルのKPIを一画面で確認。

使い方:
  python growth_engine/dashboard.py
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.hypothesis import HYPOTHESES, calculate_hypothesis_scores, rank_hypotheses
from shared.sheets import get_all_data


def show_dashboard():
    """統合ダッシュボードを表示"""
    os.system("cls" if os.name == "nt" else "clear")

    print()
    print("  ╔═══════════════════════════════════════════════════════╗")
    print("  ║          His Recoveries Growth Dashboard              ║")
    print("  ╚═══════════════════════════════════════════════════════╝")
    print(f"  更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # データ取得
    threads = get_all_data("threads_posts")
    instagram = get_all_data("instagram_posts")
    web = get_all_data("web_analytics")

    # ── 1. チャネル別サマリー ──
    print(f"\n  {'─' * 55}")
    print(f"  チャネル別サマリー")
    print(f"  {'─' * 55}")

    t_imp = sum(int(p.get("impressions", 0)) for p in threads)
    t_posts = len(threads)
    ig_reach = sum(int(p.get("reach", 0)) for p in instagram)
    ig_posts = len(instagram)
    w_pv = sum(int(p.get("pageviews", 0)) for p in web)

    print(f"\n  {'チャネル':12s} {'投稿数':8s} {'リーチ':10s}")
    print(f"  {'─' * 35}")
    print(f"  {'Threads':12s} {t_posts:>6d}本  {t_imp:>8,}")
    print(f"  {'Instagram':12s} {ig_posts:>6d}本  {ig_reach:>8,}")
    print(f"  {'Web':12s} {'—':>6s}    {w_pv:>8,} PV")

    # ── 2. 仮説スコアボード ──
    print(f"\n  {'─' * 55}")
    print(f"  仮説スコアボード")
    print(f"  {'─' * 55}")

    all_posts = []
    for p in threads:
        all_posts.append({
            "hypothesis": p.get("hypothesis", ""),
            "impressions": int(p.get("impressions", 0)),
            "saves": int(p.get("saves", 0)),
            "comments": int(p.get("replies", p.get("comments", 0))),
            "likes": int(p.get("likes", 0)),
        })
    for p in instagram:
        all_posts.append({
            "hypothesis": p.get("hypothesis", ""),
            "impressions": int(p.get("impressions", 0)),
            "saves": int(p.get("saves", 0)),
            "comments": int(p.get("comments", 0)),
            "likes": int(p.get("likes", 0)),
        })

    scores = calculate_hypothesis_scores(all_posts)
    ranked = rank_hypotheses(scores)

    print(f"\n  {'#':3s} {'仮説':10s} {'スコア':8s} {'保存率':8s} {'確信度':15s}")
    print(f"  {'─' * 50}")
    for hid, data in ranked:
        hyp = HYPOTHESES.get(hid, {})
        name = hyp.get("name", hid)
        if data["posts"] > 0:
            print(f"  {data['rank']:2d}. {name:10s} {data['score']:6.1f}  {data['avg_save_rate']:5.1f}%  {data['stars']} {data['confidence_pct']}%")
        else:
            print(f"   -  {name:10s}  {'—':>6s}  {'—':>5s}   ☆☆☆☆☆ 0%")

    # ── 3. 最近の投稿 ──
    print(f"\n  {'─' * 55}")
    print(f"  最近の投稿（Threads）")
    print(f"  {'─' * 55}")

    recent = sorted(threads, key=lambda p: p.get("date", ""), reverse=True)[:5]
    for p in recent:
        text = p.get("text", "")[:30]
        imp = int(p.get("impressions", 0))
        saves = int(p.get("saves", 0))
        hyp = p.get("hypothesis", "—")
        print(f"  {p.get('date', ''):10s} imp:{imp:>5d} save:{saves:>3d} [{hyp:10s}] {text}")

    # ── 4. アクションサジェスト ──
    print(f"\n  {'─' * 55}")
    print(f"  推奨アクション")
    print(f"  {'─' * 55}")

    if ranked and ranked[0][1]["score"] > 0:
        top_hid = ranked[0][0]
        top_hyp = HYPOTHESES.get(top_hid, {})
        print(f"\n  1. 「{top_hyp.get('name', '')}」テーマに集中投稿")
        if top_hyp.get("seo_keywords"):
            print(f"  2. SEO記事「{top_hyp['seo_keywords'][0]}」を公開")
        print(f"  3. 上位仮説のリールを作成")
    else:
        print(f"\n  データが蓄積されるまで投稿を継続してください。")
        print(f"  2週間分のデータで仮説スコアが算出されます。")

    print(f"\n  {'═' * 55}")
    print(f"  コマンド:")
    print(f"    python growth_engine/weekly_insight.py    週次レポート")
    print(f"    python growth_engine/content_calendar.py  カレンダー生成")
    print(f"    python growth_engine/funnel.py            ファネル分析")
    print(f"    python -m shared.collector --all          データ収集")
    print(f"  {'═' * 55}\n")


if __name__ == "__main__":
    show_dashboard()
