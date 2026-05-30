#!/usr/bin/env python3
"""
His Recoveries Growth Engine - 統合メニュー

全チャネル（Threads / Instagram / Web）の運営を1つの入口で管理。

使い方:
  python growth.py
"""
import os
import subprocess
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def header():
    print()
    print("  ╔═══════════════════════════════════════════════════════╗")
    print("  ║        His Recoveries Growth Engine                   ║")
    print("  ╚═══════════════════════════════════════════════════════╝")
    print()


def menu_select(title, options):
    print(f"  {title}")
    print()
    for i, (label, _) in enumerate(options, 1):
        print(f"    {i}) {label}")
    print(f"    0) 戻る")
    print()
    while True:
        raw = input("  > ").strip()
        if raw == "0" or raw == "":
            return None
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx][1]
        except (ValueError, IndexError):
            pass


def pause():
    print()
    input("  Enter で戻る...")


def main():
    while True:
        clear()
        header()
        action = menu_select("メインメニュー", [
            ("ダッシュボード（全チャネルKPI）", "dashboard"),
            ("リール作成（スクリプト→動画生成）", "reel"),
            ("データ収集（全チャネル一括）", "collect"),
            ("週次インサイトレポート", "weekly"),
            ("コンテンツカレンダー生成", "calendar"),
            ("CVRファネル分析", "funnel"),
            ("仮説一覧", "hypotheses"),
        ])

        if action is None:
            print("\n  お疲れさまでした！\n")
            break

        elif action == "dashboard":
            subprocess.run([sys.executable, "growth_engine/dashboard.py"])
            pause()

        elif action == "reel":
            clear()
            header()
            reel_action = menu_select("リール作成", [
                ("スクリプト生成（仮説→テキスト）", "script"),
                ("動画生成（スクリプト→リール動画）", "render"),
                ("一括生成（仮説→スクリプト→動画）", "batch"),
            ])

            if reel_action == "script":
                hyp = input("\n  仮説ID（hygiene/confidence/loneliness等）: ").strip()
                rtype = input("  リール型（card/slide/question）: ").strip() or "card"
                subprocess.run([sys.executable, "instagram/script_writer.py",
                                "--hypothesis", hyp, "--type", rtype])
                pause()

            elif reel_action == "render":
                script_path = input("\n  スクリプトJSONパス: ").strip()
                if os.path.exists(script_path):
                    subprocess.run([sys.executable, "instagram/reel_editor.py",
                                    "--script", script_path])
                else:
                    print(f"  ❌ ファイルが見つかりません: {script_path}")
                pause()

            elif reel_action == "batch":
                hyp = input("\n  仮説ID: ").strip()
                if hyp:
                    # スクリプト生成
                    subprocess.run([sys.executable, "instagram/script_writer.py",
                                    "--hypothesis", hyp, "--batch"])
                    # 生成されたスクリプトから動画生成
                    output_dir = "instagram/output"
                    if os.path.exists(output_dir):
                        scripts = [f for f in os.listdir(output_dir)
                                   if f.startswith(f"script_{hyp}") and f.endswith(".json")]
                        for s in scripts:
                            print(f"\n  動画生成: {s}")
                            subprocess.run([sys.executable, "instagram/reel_editor.py",
                                            "--script", os.path.join(output_dir, s)])
                pause()

        elif action == "collect":
            subprocess.run([sys.executable, "-m", "shared.collector", "--all"])
            pause()

        elif action == "weekly":
            subprocess.run([sys.executable, "growth_engine/weekly_insight.py"])
            pause()

        elif action == "calendar":
            subprocess.run([sys.executable, "growth_engine/content_calendar.py"])
            pause()

        elif action == "funnel":
            subprocess.run([sys.executable, "growth_engine/funnel.py"])
            pause()

        elif action == "hypotheses":
            from shared.hypothesis import HYPOTHESES
            print(f"\n  ── 事業仮説一覧 ──\n")
            for hid, hyp in HYPOTHESES.items():
                print(f"  {hid:20s} {hyp['name']:8s}")
                print(f"    インサイト: {hyp['insight']}")
                print(f"    キーワード: {', '.join(hyp['keywords'][:4])}")
                print(f"    SEO: {', '.join(hyp.get('seo_keywords', [])[:2])}")
                print()
            pause()


if __name__ == "__main__":
    main()
