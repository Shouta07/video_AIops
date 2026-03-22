#!/usr/bin/env python3
"""
台本ジェネレーター

テーマを入力するだけで、TikTok用の台本を自動生成。
Shimonはこれを見て読み上げながら撮影するだけ。

使い方:
  python scripts/script.py --theme "眉毛の描き方"
  python scripts/script.py --theme "BBクリームの塗り方" --style howto
  python scripts/script.py --theme "眉サロン体験" --style beforeafter
  python scripts/script.py --client eyebrow_salon --theme "眉毛の描き方"
  python scripts/script.py --list   # テンプレートから選ぶ
"""
import argparse
import json
import os
import sys
from datetime import datetime

# ── 台本スタイル ──

STYLES = {
    "beforeafter": {
        "name": "ビフォーアフター",
        "description": "変身系。変化量が伸びる。",
        "duration": 30,
        "structure": [
            {"part": "フック", "sec": "0-3秒", "role": "変化後 or 煽り。一番インパクトのある一言", "camera": "カメラ目線・正面"},
            {"part": "ビフォー", "sec": "3-6秒", "role": "変身前の状態を見せる", "camera": "正面アップ"},
            {"part": "過程", "sec": "6-22秒", "role": "施術・メイクの過程を見せる", "camera": "手元アップ + 引き"},
            {"part": "アフター", "sec": "22-27秒", "role": "完成。ビフォーとの差を見せる", "camera": "ビフォーと同じアングル"},
            {"part": "CTA", "sec": "27-30秒", "role": "フォロー誘導 or 次回予告", "camera": "カメラ目線"},
        ],
    },
    "howto": {
        "name": "ハウツー",
        "description": "やり方を教える系。保存されやすい。",
        "duration": 30,
        "structure": [
            {"part": "フック", "sec": "0-3秒", "role": "「〇〇するだけで変わる」系の煽り", "camera": "カメラ目線"},
            {"part": "ステップ1", "sec": "3-10秒", "role": "最初の手順を説明しながらやる", "camera": "手元アップ"},
            {"part": "ステップ2", "sec": "10-17秒", "role": "次の手順", "camera": "手元アップ"},
            {"part": "ステップ3", "sec": "17-24秒", "role": "仕上げ", "camera": "手元→顔"},
            {"part": "結果+CTA", "sec": "24-30秒", "role": "完成を見せてフォロー誘導", "camera": "正面"},
        ],
    },
    "grwm": {
        "name": "GRWM（Get Ready With Me）",
        "description": "支度風景。日常感が出て親近感。",
        "duration": 45,
        "structure": [
            {"part": "すっぴん", "sec": "0-3秒", "role": "寝起き or すっぴんを見せる", "camera": "正面（自然光）"},
            {"part": "スキンケア", "sec": "3-12秒", "role": "洗顔・化粧水など", "camera": "鏡越し or 正面"},
            {"part": "ベースメイク", "sec": "12-22秒", "role": "BBクリーム等を塗る", "camera": "手元+顔"},
            {"part": "ポイントメイク", "sec": "22-35秒", "role": "眉毛・リップ等", "camera": "手元アップ"},
            {"part": "完成+CTA", "sec": "35-45秒", "role": "完成顔を見せて一言", "camera": "正面"},
        ],
    },
    "compare": {
        "name": "比較・検証",
        "description": "「やった vs やってない」「左右で比較」系。",
        "duration": 30,
        "structure": [
            {"part": "フック", "sec": "0-3秒", "role": "「眉毛描くだけでこんな変わる」", "camera": "正面"},
            {"part": "片側だけ", "sec": "3-12秒", "role": "片方だけメイクする過程", "camera": "手元+顔"},
            {"part": "比較", "sec": "12-22秒", "role": "左右の差を見せる。寄り→引き", "camera": "正面→寄り→引き"},
            {"part": "両方完成", "sec": "22-27秒", "role": "もう片方もやって完成", "camera": "正面"},
            {"part": "CTA", "sec": "27-30秒", "role": "一言+フォロー誘導", "camera": "カメラ目線"},
        ],
    },
    "review": {
        "name": "アイテムレビュー",
        "description": "使ってみた系。アフィリエイトにもつながる。",
        "duration": 30,
        "structure": [
            {"part": "フック", "sec": "0-3秒", "role": "「これ○○すぎる」で引く", "camera": "商品アップ"},
            {"part": "紹介", "sec": "3-10秒", "role": "何の商品か、なぜ買ったか", "camera": "商品+手持ち"},
            {"part": "使用", "sec": "10-20秒", "role": "実際に使ってみる", "camera": "手元+顔"},
            {"part": "感想", "sec": "20-27秒", "role": "正直な感想。良い点・悪い点", "camera": "カメラ目線"},
            {"part": "CTA", "sec": "27-30秒", "role": "「他のおすすめはフォローして」", "camera": "カメラ目線"},
        ],
    },
}


def generate_script_ai(theme, style, profile=None):
    """GPTで台本を生成"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return generate_script_fallback(theme, style)

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    structure_desc = "\n".join(
        f"  [{p['sec']}] {p['part']} — {p['role']}（カメラ: {p['camera']}）"
        for p in style["structure"]
    )

    brand_context = ""
    if profile:
        brand = profile.get("brand", {})
        brand_context = f"""
クライアント情報:
- 名前: {profile.get('name', '')}
- ターゲット: {profile.get('target_audience', '')}
- トーン: {brand.get('tone', '')}
- NG表現: {', '.join(profile.get('ng_words', []))}
- キャプションルール: {profile.get('caption_rules', '')}
"""

    prompt = f"""TikTok動画の台本を作ってください。

テーマ: {theme}
スタイル: {style['name']}（{style['duration']}秒）
{brand_context}

構成:
{structure_desc}

## ルール
- 各パートにセリフを書く（読み上げ用。話し言葉で自然に）
- セリフは短く。1パート2文以内
- 冒頭3秒で離脱を防ぐ強いフックを入れる
- テロップ案も各パートに入れる（セリフとは別。短く刺さる表現で15文字以内）
- カメラワーク指示を具体的に
- 初心者男性向け。上から教えない。一緒にやる感じ
- タメ口ベース

## 出力（JSON厳守）:
{{
  "title": "この台本のタイトル（管理用）",
  "theme": "{theme}",
  "total_duration": {style['duration']},
  "parts": [
    {{
      "part_name": "パート名",
      "time": "0-3秒",
      "serif": "読み上げるセリフ",
      "telop": "テロップ（15文字以内）",
      "camera": "カメラワーク指示",
      "note": "撮影時の注意点"
    }}
  ],
  "post_caption": "投稿キャプション（150文字以内）",
  "hashtags": ["#タグ1", "#タグ2"]
}}

JSONのみ出力。"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"  ⚠️  GPTエラー: {e}")
        return generate_script_fallback(theme, style)


def generate_script_fallback(theme, style):
    """GPTが使えない場合のフォールバック"""
    parts = []
    for p in style["structure"]:
        parts.append({
            "part_name": p["part"],
            "time": p["sec"],
            "serif": f"（{p['role']}）",
            "telop": "",
            "camera": p["camera"],
            "note": "",
        })
    return {
        "title": theme,
        "theme": theme,
        "total_duration": style["duration"],
        "parts": parts,
        "post_caption": "",
        "hashtags": [],
    }


def format_script(script):
    """台本を読みやすい形式にフォーマット"""
    lines = []
    lines.append("=" * 50)
    lines.append(f"  台本: {script.get('title', '')}")
    lines.append("=" * 50)
    lines.append(f"  テーマ: {script.get('theme', '')}")
    lines.append(f"  尺: {script.get('total_duration', '?')}秒")
    lines.append("")

    for part in script.get("parts", []):
        lines.append(f"  ┌─ {part['part_name']}（{part['time']}）")
        lines.append(f"  │")
        lines.append(f"  │  セリフ: 「{part['serif']}」")
        if part.get("telop"):
            lines.append(f"  │  テロップ: 【{part['telop']}】")
        lines.append(f"  │  カメラ: {part['camera']}")
        if part.get("note"):
            lines.append(f"  │  注意: {part['note']}")
        lines.append(f"  └─")
        lines.append("")

    if script.get("post_caption"):
        lines.append("─" * 50)
        lines.append("  投稿キャプション（コピペ用）:")
        lines.append(f"  {script['post_caption']}")

    if script.get("hashtags"):
        lines.append("")
        lines.append("  ハッシュタグ（コピペ用）:")
        lines.append(f"  {' '.join(script['hashtags'])}")

    lines.append("")
    lines.append("=" * 50)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="台本ジェネレーター - テーマを入れるだけでTikTok台本を自動生成",
    )
    parser.add_argument("--theme", help="テーマ（例: 眉毛の描き方）")
    parser.add_argument("--style", default="beforeafter",
                        choices=list(STYLES.keys()),
                        help="台本スタイル（デフォルト: beforeafter）")
    parser.add_argument("--client", help="クライアントID")
    parser.add_argument("--list", action="store_true", help="スタイル一覧を表示")
    args = parser.parse_args()

    if args.list:
        print("\n  ── 台本スタイル一覧 ──\n")
        for sid, style in STYLES.items():
            print(f"  {sid:15s}  {style['name']:15s}  {style['duration']}秒  {style['description']}")
        print()
        return

    if not args.theme:
        print("❌ --theme を指定してください（例: --theme 「眉毛の描き方」）")
        sys.exit(1)

    style = STYLES[args.style]

    # クライアントプロフィール読み込み
    profile = None
    if args.client:
        profile_path = os.path.join("clients", args.client, "profile.json")
        if os.path.exists(profile_path):
            with open(profile_path, encoding="utf-8") as f:
                profile = json.load(f)

    print(f"\n  テーマ: {args.theme}")
    print(f"  スタイル: {style['name']}（{style['duration']}秒）")
    print(f"  台本を生成中...\n")

    # 台本生成
    script = generate_script_ai(args.theme, style, profile)

    # 表示
    formatted = format_script(script)
    print(formatted)

    # 保存
    if args.client:
        save_dir = os.path.join("clients", args.client, "reports")
    else:
        save_dir = "reports"
    os.makedirs(save_dir, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    safe_theme = args.theme.replace(" ", "_").replace("/", "_")[:20]

    # テキスト版（Shimonに渡す用）
    txt_path = os.path.join(save_dir, f"script_{safe_theme}_{today}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(formatted)

    # JSON版（planner.pyで使う用）
    json_path = os.path.join(save_dir, f"script_{safe_theme}_{today}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)

    print(f"\n  保存しました:")
    print(f"    Shimonに渡す用: {txt_path}")
    print(f"    システム用:      {json_path}")
    print(f"\n  Shimonへの渡し方:")
    print(f"    → このテキストをLarkで送るだけ")


if __name__ == "__main__":
    main()
