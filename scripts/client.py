#!/usr/bin/env python3
"""
クライアント管理 - プロフィール作成・一覧・更新

clients/
  {client_id}/
    profile.json   ← ブランド設定
    input/         ← 素材フォルダ
    output/        ← 完成動画
    reports/       ← 納品レポート
"""
import json
import os
import sys

CLIENTS_DIR = "clients"

DEFAULT_PROFILE = {
    "name": "",
    "genre": "beauty",
    "brand": {
        "tone": "親しみやすく丁寧",
        "telop_color_main": "white",
        "telop_color_accent": "yellow",
        "telop_color_cta": "#FFB6C1",
        "font_size": 56,
    },
    "hashtags_fixed": [],
    "hashtags_ng": [],
    "caption_rules": "",
    "ng_words": [],
    "target_audience": "",
    "posting_frequency": "週3回",
    "notes": "",
}

GENRES = {
    "beauty": "美容・コスメ",
    "food": "料理・グルメ",
    "travel": "旅行・Vlog",
    "fitness": "筋トレ・フィットネス",
    "business": "ビジネス・ノウハウ",
    "lifestyle": "ライフスタイル・日常",
    "education": "教育・解説",
    "product": "商品紹介・レビュー",
}


def get_client_dir(client_id):
    return os.path.join(CLIENTS_DIR, client_id)


def get_profile_path(client_id):
    return os.path.join(get_client_dir(client_id), "profile.json")


def load_profile(client_id):
    path = get_profile_path(client_id)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_profile(client_id, profile):
    client_dir = get_client_dir(client_id)
    os.makedirs(client_dir, exist_ok=True)
    os.makedirs(os.path.join(client_dir, "input"), exist_ok=True)
    os.makedirs(os.path.join(client_dir, "output"), exist_ok=True)
    os.makedirs(os.path.join(client_dir, "reports"), exist_ok=True)

    with open(get_profile_path(client_id), "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)


def list_clients():
    """登録済みクライアント一覧"""
    if not os.path.exists(CLIENTS_DIR):
        return []
    clients = []
    for name in sorted(os.listdir(CLIENTS_DIR)):
        profile_path = os.path.join(CLIENTS_DIR, name, "profile.json")
        if os.path.exists(profile_path):
            with open(profile_path, encoding="utf-8") as f:
                profile = json.load(f)
            # 素材数をカウント
            input_dir = os.path.join(CLIENTS_DIR, name, "input")
            video_count = 0
            if os.path.exists(input_dir):
                exts = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
                video_count = sum(1 for fn in os.listdir(input_dir) if os.path.splitext(fn)[1].lower() in exts)
            clients.append({
                "id": name,
                "name": profile.get("name", name),
                "genre": profile.get("genre", ""),
                "video_count": video_count,
            })
    return clients


def prompt_input(label, default="", required=False):
    """対話型入力ヘルパー"""
    suffix = f" ({default})" if default else ""
    while True:
        value = input(f"  {label}{suffix}: ").strip()
        if not value and default:
            return default
        if not value and required:
            print(f"    ※ 必須項目です")
            continue
        return value


def prompt_choice(label, options, default=None):
    """選択式入力"""
    print(f"\n  {label}:")
    keys = list(options.keys())
    for i, key in enumerate(keys, 1):
        marker = " ←" if key == default else ""
        print(f"    {i}) {options[key]}{marker}")
    while True:
        raw = input(f"  番号を入力: ").strip()
        if not raw and default:
            return default
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(keys):
                return keys[idx]
        except (ValueError, IndexError):
            pass
        print(f"    ※ 1〜{len(keys)} の番号を入力してください")


def prompt_list(label, current=None):
    """リスト入力（カンマ区切り）"""
    current_str = ", ".join(current) if current else ""
    hint = f" (現在: {current_str})" if current_str else ""
    raw = input(f"  {label}{hint}\n  カンマ区切りで入力: ").strip()
    if not raw:
        return current or []
    return [x.strip() for x in raw.split(",") if x.strip()]


def create_client_interactive():
    """対話型でクライアントを新規登録"""
    print("\n" + "=" * 50)
    print("  新規クライアント登録")
    print("=" * 50)

    # クライアントID
    print()
    client_id = prompt_input("クライアントID（英数字、例: eyebrow_salon）", required=True)
    client_id = client_id.lower().replace(" ", "_").replace("-", "_")

    if load_profile(client_id):
        print(f"\n  ⚠️  {client_id} は既に登録済みです。")
        yn = input("  上書きしますか？ (y/N): ").strip().lower()
        if yn != "y":
            return None

    profile = dict(DEFAULT_PROFILE)
    profile["brand"] = dict(DEFAULT_PROFILE["brand"])

    # 基本情報
    print(f"\n  ── 基本情報 ──")
    profile["name"] = prompt_input("クライアント名（表示名）", required=True)
    profile["genre"] = prompt_choice("ジャンル", GENRES, default="beauty")
    profile["target_audience"] = prompt_input("ターゲット層", "20〜30代女性")
    profile["posting_frequency"] = prompt_input("投稿頻度", "週3回")

    # ブランド設定
    print(f"\n  ── ブランド設定 ──")
    profile["brand"]["tone"] = prompt_input("トーン・文体", "親しみやすく丁寧")
    print(f"\n  テロップ色 (white, yellow, #FF69B4 等)")
    profile["brand"]["telop_color_main"] = prompt_input("メイン色", "white")
    profile["brand"]["telop_color_accent"] = prompt_input("強調色", "yellow")
    profile["brand"]["telop_color_cta"] = prompt_input("CTA色", "#FFB6C1")

    # ハッシュタグ
    print(f"\n  ── ハッシュタグ ──")
    profile["hashtags_fixed"] = prompt_list("毎回つける固定タグ（例: #眉毛サロン, #渋谷）")
    profile["hashtags_ng"] = prompt_list("使用禁止タグ")

    # キャプションルール
    print(f"\n  ── キャプション・NG設定 ──")
    profile["caption_rules"] = prompt_input("キャプションのルール", "絵文字控えめ、敬語")
    profile["ng_words"] = prompt_list("NG表現（例: 激安, 最強, 神）")
    profile["notes"] = prompt_input("その他メモ", "")

    # 保存
    save_profile(client_id, profile)

    print(f"\n  ✅ 登録完了: {profile['name']}（{client_id}）")
    print(f"  📂 フォルダ: clients/{client_id}/")
    print(f"     素材を clients/{client_id}/input/ に入れてください")

    return client_id


def edit_client_interactive(client_id):
    """既存クライアントのプロフィールを編集"""
    profile = load_profile(client_id)
    if not profile:
        print(f"  ❌ クライアントが見つかりません: {client_id}")
        return

    print(f"\n  ── {profile['name']} の設定を編集 ──")
    print(f"  （変更しない項目はEnterでスキップ）\n")

    profile["name"] = prompt_input("クライアント名", profile.get("name", ""))
    profile["genre"] = prompt_choice("ジャンル", GENRES, default=profile.get("genre", "beauty"))
    profile["target_audience"] = prompt_input("ターゲット層", profile.get("target_audience", ""))
    profile["posting_frequency"] = prompt_input("投稿頻度", profile.get("posting_frequency", ""))

    brand = profile.get("brand", {})
    brand["tone"] = prompt_input("トーン・文体", brand.get("tone", ""))
    brand["telop_color_main"] = prompt_input("テロップメイン色", brand.get("telop_color_main", "white"))
    brand["telop_color_accent"] = prompt_input("テロップ強調色", brand.get("telop_color_accent", "yellow"))
    brand["telop_color_cta"] = prompt_input("テロップCTA色", brand.get("telop_color_cta", "#FFB6C1"))
    profile["brand"] = brand

    profile["hashtags_fixed"] = prompt_list("固定タグ", profile.get("hashtags_fixed", []))
    profile["hashtags_ng"] = prompt_list("禁止タグ", profile.get("hashtags_ng", []))
    profile["caption_rules"] = prompt_input("キャプションルール", profile.get("caption_rules", ""))
    profile["ng_words"] = prompt_list("NG表現", profile.get("ng_words", []))
    profile["notes"] = prompt_input("メモ", profile.get("notes", ""))

    save_profile(client_id, profile)
    print(f"\n  ✅ 更新完了: {profile['name']}")


def show_client_detail(client_id):
    """クライアント詳細表示"""
    profile = load_profile(client_id)
    if not profile:
        print(f"  ❌ 見つかりません: {client_id}")
        return

    brand = profile.get("brand", {})
    print(f"\n  ╔══════════════════════════════════════╗")
    print(f"  ║  {profile['name']}")
    print(f"  ╚══════════════════════════════════════╝")
    print(f"  ID:           {client_id}")
    print(f"  ジャンル:      {GENRES.get(profile.get('genre', ''), profile.get('genre', ''))}")
    print(f"  ターゲット:    {profile.get('target_audience', '-')}")
    print(f"  投稿頻度:      {profile.get('posting_frequency', '-')}")
    print(f"  トーン:        {brand.get('tone', '-')}")
    print(f"  テロップ色:    メイン={brand.get('telop_color_main','-')} / 強調={brand.get('telop_color_accent','-')} / CTA={brand.get('telop_color_cta','-')}")
    print(f"  固定タグ:      {' '.join(profile.get('hashtags_fixed', [])) or '-'}")
    print(f"  禁止タグ:      {' '.join(profile.get('hashtags_ng', [])) or '-'}")
    print(f"  NG表現:        {', '.join(profile.get('ng_words', [])) or '-'}")
    print(f"  ルール:        {profile.get('caption_rules', '-')}")
    print(f"  メモ:          {profile.get('notes', '-')}")

    # 素材状況
    input_dir = os.path.join(CLIENTS_DIR, client_id, "input")
    output_dir = os.path.join(CLIENTS_DIR, client_id, "output")
    exts = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}

    input_count = sum(1 for fn in os.listdir(input_dir) if os.path.splitext(fn)[1].lower() in exts) if os.path.exists(input_dir) else 0
    output_count = sum(1 for fn in os.listdir(output_dir) if os.path.splitext(fn)[1].lower() in exts) if os.path.exists(output_dir) else 0

    print(f"\n  素材:  {input_count}本（input/）")
    print(f"  完成:  {output_count}本（output/）")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="クライアント管理")
    parser.add_argument("action", choices=["create", "list", "show", "edit"], help="操作")
    parser.add_argument("--id", help="クライアントID")
    parser.add_argument("--json", action="store_true", help="JSONで出力（Web API用）")
    args = parser.parse_args()

    if args.action == "create":
        create_client_interactive()
    elif args.action == "list":
        clients = list_clients()
        if args.json:
            print(json.dumps({"clients": clients}, ensure_ascii=False))
        elif not clients:
            print("  登録済みクライアントはありません。")
        else:
            print(f"\n  ── クライアント一覧 ──\n")
            for c in clients:
                genre_label = GENRES.get(c["genre"], c["genre"])
                print(f"  {c['id']:20s}  {c['name']:15s}  {genre_label}  素材{c['video_count']}本")
    elif args.action == "show":
        if not args.id:
            print("  --id を指定してください")
        else:
            show_client_detail(args.id)
    elif args.action == "edit":
        if not args.id:
            print("  --id を指定してください")
        else:
            edit_client_interactive(args.id)
