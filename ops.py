#!/usr/bin/env python3
"""
Video AIops - 統合メニュー

これだけ覚えればOK:
  python ops.py
"""
import os
import subprocess
import sys

# スクリプトのディレクトリに移動
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ─── UI ヘルパー ───

def clear():
    os.system("cls" if os.name == "nt" else "clear")


def header():
    print()
    print("  ╔═══════════════════════════════════════════╗")
    print("  ║        Video AIops                        ║")
    print("  ║        TikTok 運営オペレーション            ║")
    print("  ╚═══════════════════════════════════════════╝")
    print()


def divider():
    print("  " + "─" * 45)


def pause():
    print()
    input("  Enter で戻る...")


def menu_select(title, options):
    """番号選択メニュー。options = [(label, key), ...]"""
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


# ─── クライアント選択 ───

def select_client():
    """登録済みクライアントを選択"""
    from scripts.client import list_clients
    clients = list_clients()
    if not clients:
        print("  クライアントが未登録です。先に登録してください。")
        pause()
        return None

    options = []
    for c in clients:
        label = f"{c['name']:15s}  素材{c['video_count']}本"
        options.append((label, c["id"]))

    return menu_select("クライアントを選択:", options)


# ─── メニュー 1: クライアント管理 ───

def menu_client():
    while True:
        clear()
        header()
        action = menu_select("クライアント管理", [
            ("新規登録", "create"),
            ("一覧", "list"),
            ("詳細を見る", "show"),
            ("設定を編集", "edit"),
        ])
        if action is None:
            return

        if action == "create":
            subprocess.run([sys.executable, "scripts/client.py", "create"])
            pause()
        elif action == "list":
            subprocess.run([sys.executable, "scripts/client.py", "list"])
            pause()
        elif action == "show":
            client_id = select_client()
            if client_id:
                subprocess.run([sys.executable, "scripts/client.py", "show", "--id", client_id])
                pause()
        elif action == "edit":
            client_id = select_client()
            if client_id:
                subprocess.run([sys.executable, "scripts/client.py", "edit", "--id", client_id])
                pause()


# ─── メニュー 2: 撮影指示書 ───

def menu_brief():
    clear()
    header()
    client_id = select_client()
    if not client_id:
        return

    from scripts.client import load_profile
    profile = load_profile(client_id)

    print(f"\n  クライアント: {profile['name']}")
    print(f"  ジャンル: {profile['genre']}")
    theme = input("\n  テーマを入力（例: 眉毛デザイン体験）: ").strip()

    args = [sys.executable, "scripts/brief.py",
            "--genre", profile["genre"], "--save"]
    if theme:
        args += ["--theme", theme]

    # --client オプションで保存先を変更
    subprocess.run(args + ["--client", client_id])
    pause()


# ─── メニュー 3: 投稿プラン生成 ───

def menu_plan():
    while True:
        clear()
        header()
        action = menu_select("投稿プラン", [
            ("素材から投稿プランを生成", "new"),
            ("プラン確認のみ（動画生成なし）", "dry"),
            ("既存プランを修正して再生成", "redo"),
        ])
        if action is None:
            return

        client_id = select_client()
        if not client_id:
            continue

        from scripts.client import load_profile
        profile = load_profile(client_id)
        input_dir = f"clients/{client_id}/input"
        genre = profile["genre"]

        # リサイクル提案
        recycle = input("\n  素材リサイクル提案も出す？ (y/N): ").strip().lower() == "y"

        if action == "new":
            args = [sys.executable, "scripts/planner.py",
                    "--client", client_id, "--genre", genre]
            if recycle:
                args.append("--recycle")
            subprocess.run(args)
        elif action == "dry":
            args = [sys.executable, "scripts/planner.py",
                    "--client", client_id, "--genre", genre, "--dry-run"]
            if recycle:
                args.append("--recycle")
            subprocess.run(args)
        elif action == "redo":
            reports_dir = f"clients/{client_id}/reports"
            # 最新のplan JSONを探す
            plan_files = sorted(
                [f for f in os.listdir(reports_dir) if f.startswith("plan_") and f.endswith(".json")]
            ) if os.path.exists(reports_dir) else []
            if not plan_files:
                print(f"\n  ❌ {reports_dir}/ にプランJSONがありません。先にプランを生成してください。")
            else:
                plan_path = os.path.join(reports_dir, plan_files[-1])
                print(f"\n  最新プラン: {plan_path}")
                print(f"  ※ このJSONを編集してから実行すると、修正が反映されます")
                yn = input("  このプランで再生成しますか？ (Y/n): ").strip().lower()
                if yn != "n":
                    subprocess.run([sys.executable, "scripts/planner.py",
                                    "--client", client_id, "--plan-json", plan_path])
        pause()


# ─── メニュー 4: ステータス確認 ───

def menu_status():
    clear()
    header()
    from scripts.client import list_clients, GENRES

    clients = list_clients()
    if not clients:
        print("  クライアントが未登録です。")
        pause()
        return

    print("  ── 全クライアント状況 ──")
    print()
    print(f"  {'クライアント':15s}  {'ジャンル':12s}  {'素材':5s}  {'完成':5s}  {'レポート':5s}")
    divider()

    for c in clients:
        cid = c["id"]
        genre_label = GENRES.get(c["genre"], c["genre"])

        output_dir = f"clients/{cid}/output"
        reports_dir = f"clients/{cid}/reports"
        exts = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}

        output_count = 0
        if os.path.exists(output_dir):
            output_count = sum(1 for fn in os.listdir(output_dir)
                               if os.path.splitext(fn)[1].lower() in exts)

        report_count = 0
        if os.path.exists(reports_dir):
            report_count = sum(1 for fn in os.listdir(reports_dir)
                               if fn.endswith(".md"))

        print(f"  {c['name']:15s}  {genre_label:12s}  {c['video_count']:3d}本  {output_count:3d}本  {report_count:3d}件")

    print()
    divider()
    pause()


# ─── メニュー 5: クイック実行 ───

def menu_quick():
    """素材を入れたらすぐ実行"""
    clear()
    header()
    client_id = select_client()
    if not client_id:
        return

    from scripts.client import load_profile
    profile = load_profile(client_id)
    input_dir = f"clients/{client_id}/input"

    # 素材数を確認
    exts = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
    video_count = sum(1 for fn in os.listdir(input_dir)
                      if os.path.splitext(fn)[1].lower() in exts) if os.path.exists(input_dir) else 0

    print(f"\n  クライアント: {profile['name']}")
    print(f"  素材: {video_count}本")

    if video_count == 0:
        print(f"\n  ❌ 素材がありません。")
        print(f"  clients/{client_id}/input/ に動画を入れてください。")
        pause()
        return

    # テンプレート選択（任意）
    from scripts.analyze_buzz import list_templates
    templates = list_templates(client_id)
    tmpl_path = None
    if templates:
        print(f"\n  バズの型を使いますか？")
        tmpl_options = [(f"{t['name']} ({t['template_name']})", t["path"]) for t in templates]
        tmpl_options.append(("型なし（AIにおまかせ）", None))
        tmpl_path = menu_select("型を選択:", tmpl_options)

    print(f"\n  → 素材解析 → 投稿プラン → 動画生成 → レポート を一括実行します")
    yn = input("  実行しますか？ (Y/n): ").strip().lower()
    if yn == "n":
        return

    cmd = [
        sys.executable, "scripts/planner.py",
        "--client", client_id,
        "--genre", profile["genre"],
        "--recycle",
    ]
    if tmpl_path:
        cmd += ["--template", tmpl_path]
    subprocess.run(cmd)
    pause()


# ─── メニュー 6: バズ動画から型を作る ───

def menu_buzz():
    while True:
        clear()
        header()
        action = menu_select("バズ動画の型", [
            ("バズ動画URLから型を作る", "analyze"),
            ("保存済みの型一覧", "list"),
            ("型を使って投稿プランを生成", "use"),
        ])
        if action is None:
            return

        if action == "analyze":
            print("\n  バズ動画のURLを入力してください。")
            print("  複数の場合はカンマ区切り → 共通パターンを抽出します。")
            raw_urls = input("\n  URL: ").strip()
            if not raw_urls:
                continue
            urls = [u.strip() for u in raw_urls.split(",") if u.strip()]

            name = input("  型の名前（例: ビフォアフ王道）: ").strip()
            if not name:
                name = "バズ型"

            # クライアント選択（任意）
            print("\n  クライアントに紐付けますか？")
            client_id = select_client()

            cmd = [sys.executable, "scripts/analyze_buzz.py"] + urls + ["--name", name]
            if client_id:
                cmd += ["--client", client_id]
            subprocess.run(cmd)
            pause()

        elif action == "list":
            # クライアント選択
            client_id = select_client()
            from scripts.analyze_buzz import list_templates
            templates = list_templates(client_id)
            if not templates:
                print("\n  保存済みの型がありません。")
                print("  先に「バズ動画URLから型を作る」を実行してください。")
            else:
                print(f"\n  ── 保存済みの型 ──\n")
                for t in templates:
                    print(f"  {t['name']:20s}  {t['template_name']:20s}  {t['duration']}秒  {t['parts']}パート")
                    print(f"    → {t['path']}")
            pause()

        elif action == "use":
            # クライアント選択
            client_id = select_client()
            if not client_id:
                continue

            from scripts.client import load_profile
            from scripts.analyze_buzz import list_templates
            profile = load_profile(client_id)

            templates = list_templates(client_id)
            if not templates:
                print("\n  ❌ テンプレートがありません。先にバズ動画から型を作ってください。")
                pause()
                continue

            # テンプレート選択
            tmpl_options = [(f"{t['name']} ({t['template_name']}, {t['duration']}秒)", t["path"]) for t in templates]
            tmpl_path = menu_select("使う型を選択:", tmpl_options)
            if not tmpl_path:
                continue

            recycle = input("\n  素材リサイクル提案も出す？ (y/N): ").strip().lower() == "y"

            cmd = [
                sys.executable, "scripts/planner.py",
                "--client", client_id,
                "--genre", profile["genre"],
                "--template", tmpl_path,
            ]
            if recycle:
                cmd.append("--recycle")
            subprocess.run(cmd)
            pause()


# ─── メニュー 7: 台本作成 ───

def menu_script():
    clear()
    header()
    client_id = select_client()
    if not client_id:
        return

    from scripts.script import STYLES

    # スタイル選択
    style_options = [(f"{s['name']}（{s['duration']}秒）— {s['description']}", sid) for sid, s in STYLES.items()]
    style_id = menu_select("台本スタイルを選択:", style_options)
    if not style_id:
        return

    theme = input("\n  テーマを入力（例: 眉毛の描き方）: ").strip()
    if not theme:
        return

    cmd = [sys.executable, "scripts/script.py",
           "--theme", theme, "--style", style_id, "--client", client_id]
    subprocess.run(cmd)
    pause()


# ─── メインメニュー ───

def main():
    while True:
        clear()
        header()
        action = menu_select("メインメニュー", [
            ("クイック実行（素材 → 投稿プラン → 動画生成）", "quick"),
            ("台本を作成（テーマ入力 → 台本生成）", "script"),
            ("バズ動画の型（URL分析 / 型で投稿生成）", "buzz"),
            ("投稿プラン（確認・修正・再生成）", "plan"),
            ("撮影指示書を作成", "brief"),
            ("クライアント管理", "client"),
            ("ステータス確認", "status"),
        ])

        if action is None:
            print("\n  お疲れさまでした！\n")
            break
        elif action == "quick":
            menu_quick()
        elif action == "script":
            menu_script()
        elif action == "buzz":
            menu_buzz()
        elif action == "plan":
            menu_plan()
        elif action == "brief":
            menu_brief()
        elif action == "client":
            menu_client()
        elif action == "status":
            menu_status()


if __name__ == "__main__":
    main()
