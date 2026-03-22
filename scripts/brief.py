#!/usr/bin/env python3
"""
撮影指示書ジェネレーター

友人に渡す撮影指示書を自動生成する。
ジャンルとパターンを選ぶだけで「何を・どう撮るか」が明確になる。

使い方:
  python scripts/brief.py --genre beauty
  python scripts/brief.py --genre beauty --pattern before-after
  python scripts/brief.py --list                # パターン一覧表示
  python scripts/brief.py --genre food --theme "自家製パスタ"
"""
import argparse
import json
import os
import sys
from datetime import datetime

# ── patterns.js と同等のパターン辞書（Python版） ──

GENRES = {
    "food": {
        "name": "料理・グルメ",
        "patterns": {
            "result-first": {
                "name": "完成品フック型",
                "description": "完成品を冒頭に見せて「どうやって作るの？」と興味を引く",
                "duration": 30,
                "structure": [
                    {"name": "完成品フック", "seconds": "0-2秒", "note": "完成品のアップ。一番映えるアングルで", "camera": "真上 or 45度、寄り"},
                    {"name": "材料紹介", "seconds": "2-5秒", "note": "材料を並べて撮る", "camera": "真上、全体が入るように"},
                    {"name": "調理過程", "seconds": "5-24秒", "note": "各工程を撮る。手元アップ多め", "camera": "横45度、手元アップ"},
                    {"name": "盛り付け", "seconds": "24-28秒", "note": "お皿に盛る過程", "camera": "横から、スロー推奨"},
                    {"name": "実食リアクション", "seconds": "28-30秒", "note": "食べて美味しいリアクション", "camera": "正面バストアップ"},
                ],
                "tips": [
                    "完成品は必ず最初と最後に撮る（2回）",
                    "調理は全工程を通しで撮ってOK（早送りにする）",
                    "湯気・チーズが溶ける等の「シズル感」は長めに撮る",
                    "まな板の上は常にきれいに",
                ],
            },
            "asmr": {
                "name": "ASMR調理型",
                "description": "調理音を活かしたASMR風",
                "duration": 45,
                "structure": [
                    {"name": "食材カット音", "seconds": "0-3秒", "note": "包丁で切る音", "camera": "手元アップ、マイク近め"},
                    {"name": "調理過程", "seconds": "3-35秒", "note": "焼く・炒める・注ぐ音を活かす", "camera": "手元アップ、音がよく録れる距離"},
                    {"name": "完成", "seconds": "35-42秒", "note": "完成品のアップ", "camera": "45度、湯気が見える位置"},
                    {"name": "CTA", "seconds": "42-45秒", "note": "笑顔で締め", "camera": "正面"},
                ],
                "tips": [
                    "周囲の雑音を消す（エアコン切る等）",
                    "スマホのマイクを食材に近づける",
                    "切る・焼く・注ぐのアップショットを多めに",
                    "BGMなしが正解（音が主役）",
                ],
            },
        },
    },
    "travel": {
        "name": "旅行・Vlog",
        "patterns": {
            "transition": {
                "name": "トランジション旅型",
                "description": "場面転換のトランジションで視聴者を飽きさせない",
                "duration": 30,
                "structure": [
                    {"name": "到着フック", "seconds": "0-3秒", "note": "到着の瞬間・絶景を撮る", "camera": "広角、ダイナミックに"},
                    {"name": "スポット1", "seconds": "3-10秒", "note": "観光地や食事", "camera": "1カット3秒以内でテンポよく"},
                    {"name": "スポット2", "seconds": "10-18秒", "note": "別の場所", "camera": "トランジション用に手でレンズを覆う→次の場所"},
                    {"name": "ハイライト", "seconds": "18-26秒", "note": "最も映えるシーン", "camera": "スローで撮りたいならスマホのスロー機能ON"},
                    {"name": "まとめ", "seconds": "26-30秒", "note": "感想を一言 or 絶景で締め", "camera": "正面 or 広角"},
                ],
                "tips": [
                    "各スポットは長めに撮る（10-15秒ずつ）→ 編集で切る",
                    "トランジション用に手でレンズを覆う動作を各場面でやる",
                    "場所名がわかる看板も撮っておく",
                    "食べ物は一口目のリアクションを撮る",
                ],
            },
            "cinematic": {
                "name": "シネマティック旅型",
                "description": "映画のような雰囲気。スローモーション多用",
                "duration": 45,
                "structure": [
                    {"name": "広角ショット", "seconds": "0-5秒", "note": "壮大な風景", "camera": "広角・パン撮影"},
                    {"name": "日常シーン", "seconds": "5-20秒", "note": "歩く・食べる・触れる", "camera": "スロー撮影、手持ち"},
                    {"name": "ハイライト", "seconds": "20-38秒", "note": "最も美しいシーン", "camera": "三脚推奨、スロー"},
                    {"name": "余韻", "seconds": "38-45秒", "note": "夕日やフェードアウト的なシーン", "camera": "固定・広角"},
                ],
                "tips": [
                    "スロー撮影を多用する（スマホの240fps設定）",
                    "手持ちでゆっくり歩きながら撮ると映画感",
                    "朝・夕方の光が一番きれい（昼は避ける）",
                    "同じ場所を広角と寄りの2パターンで撮る",
                ],
            },
        },
    },
    "beauty": {
        "name": "美容・コスメ",
        "patterns": {
            "before-after": {
                "name": "ビフォーアフター型",
                "description": "変身前→変身後のギャップで伸びる（GRWM定番）",
                "duration": 30,
                "structure": [
                    {"name": "Before", "seconds": "0-3秒", "note": "すっぴん or 施術前の状態", "camera": "正面アップ、明るい照明"},
                    {"name": "施術/メイク過程", "seconds": "3-22秒", "note": "施術の過程を全部撮る", "camera": "手元アップ + 引きの2アングル"},
                    {"name": "After", "seconds": "22-28秒", "note": "完成した状態", "camera": "Beforeと同じ角度・距離で！"},
                    {"name": "リアクション", "seconds": "28-30秒", "note": "嬉しいリアクション", "camera": "正面バストアップ"},
                ],
                "tips": [
                    "BeforeとAfterは必ず同じアングル・同じ照明で撮る",
                    "施術過程は長めに撮ってOK（早送りにする）",
                    "使用した商品・道具が映るように撮る",
                    "照明は自然光がベスト（窓際で）",
                    "鏡越しでなく直接カメラを見て撮る",
                ],
            },
        },
    },
    "fitness": {
        "name": "筋トレ・フィットネス",
        "patterns": {
            "routine": {
                "name": "ルーティン紹介型",
                "description": "「○日で腹筋割れる」等の具体的な数字フックで引きつけ",
                "duration": 30,
                "structure": [
                    {"name": "数字フック", "seconds": "0-3秒", "note": "カメラ目線で宣言", "camera": "正面バストアップ"},
                    {"name": "種目1", "seconds": "3-10秒", "note": "1つ目のエクササイズ", "camera": "横から全身が入る"},
                    {"name": "種目2", "seconds": "10-17秒", "note": "2つ目のエクササイズ", "camera": "同上"},
                    {"name": "種目3", "seconds": "17-24秒", "note": "3つ目のエクササイズ", "camera": "同上"},
                    {"name": "結果・CTA", "seconds": "24-30秒", "note": "ビフォアフ or 一言コメント", "camera": "正面"},
                ],
                "tips": [
                    "各種目は3セットくらい撮って一番フォームが綺麗なのを使う",
                    "横からのアングルで全身が映るように",
                    "回数のカウントを声に出しながら撮る",
                    "汗が見える照明だとリアリティ UP",
                ],
            },
        },
    },
    "business": {
        "name": "ビジネス・ノウハウ",
        "patterns": {
            "list": {
                "name": "リスト型（○選）",
                "description": "「知らないと損する○選」でリーチを取る",
                "duration": 45,
                "structure": [
                    {"name": "煽りフック", "seconds": "0-3秒", "note": "カメラ目線で強い一言", "camera": "正面バストアップ"},
                    {"name": "ポイント1", "seconds": "3-12秒", "note": "1つ目を解説", "camera": "正面、手振りを入れる"},
                    {"name": "ポイント2", "seconds": "12-22秒", "note": "2つ目を解説", "camera": "同上"},
                    {"name": "ポイント3", "seconds": "22-32秒", "note": "最もインパクトのある内容", "camera": "寄り（力強く）"},
                    {"name": "まとめ・CTA", "seconds": "32-45秒", "note": "まとめてフォロー誘導", "camera": "正面バストアップ"},
                ],
                "tips": [
                    "背景はシンプルに（白壁、オフィス）",
                    "各ポイントの冒頭で指を立てる（1, 2, 3）",
                    "早口すぎず、1ポイント1呼吸で",
                    "テロップ前提なので滑舌は8割でOK",
                ],
            },
            "story": {
                "name": "体験談ストーリー型",
                "description": "共感→転機→結果のストーリー構成",
                "duration": 60,
                "structure": [
                    {"name": "共感フック", "seconds": "0-5秒", "note": "「昔の自分は○○だった」", "camera": "正面、真剣な表情"},
                    {"name": "問題提起", "seconds": "5-15秒", "note": "困っていたこと", "camera": "正面"},
                    {"name": "転機", "seconds": "15-25秒", "note": "何が変わったか", "camera": "表情が明るくなるように"},
                    {"name": "変化・結果", "seconds": "25-45秒", "note": "具体的な成果", "camera": "画面共有やスクショがあればベスト"},
                    {"name": "教訓・CTA", "seconds": "45-60秒", "note": "学びとフォロー誘導", "camera": "正面バストアップ"},
                ],
                "tips": [
                    "数字（月収、フォロワー数等）があると説得力UP",
                    "顔出しの方が圧倒的に信頼される",
                    "通しで撮ってOK（テロップで補足する）",
                ],
            },
        },
    },
    "lifestyle": {
        "name": "ライフスタイル・日常",
        "patterns": {
            "routine": {
                "name": "モーニングルーティン型",
                "description": "「丁寧な暮らし」系。朝の過ごし方を淡々と見せる",
                "duration": 45,
                "structure": [
                    {"name": "起床", "seconds": "0-5秒", "note": "目覚まし・ストレッチ", "camera": "ベッド横から"},
                    {"name": "朝食準備", "seconds": "5-18秒", "note": "コーヒー淹れる・朝食作り", "camera": "手元アップ、音を拾う"},
                    {"name": "朝食・支度", "seconds": "18-32秒", "note": "食べる・身支度", "camera": "引きで生活感"},
                    {"name": "出発", "seconds": "32-42秒", "note": "家を出る", "camera": "玄関→外"},
                    {"name": "CTA", "seconds": "42-45秒", "note": "「今日も頑張ろう」的な一言", "camera": "正面 or テキストのみ"},
                ],
                "tips": [
                    "朝の自然光で撮る（カーテン開ける場面から始めると◎）",
                    "生活音（水の音、コーヒーの音）を大事に",
                    "部屋は片付けてから撮る",
                    "時計が映ると時間経過がわかりやすい",
                ],
            },
        },
    },
    "education": {
        "name": "教育・解説",
        "patterns": {
            "explain": {
                "name": "図解・解説型",
                "description": "複雑な概念を短時間でわかりやすく",
                "duration": 30,
                "structure": [
                    {"name": "問いかけ", "seconds": "0-3秒", "note": "「○○って知ってる？」", "camera": "正面バストアップ"},
                    {"name": "解説1", "seconds": "3-12秒", "note": "ポイント1", "camera": "正面 or 画面共有"},
                    {"name": "解説2", "seconds": "12-22秒", "note": "ポイント2", "camera": "同上"},
                    {"name": "まとめ", "seconds": "22-28秒", "note": "結論をシンプルに", "camera": "正面"},
                    {"name": "CTA", "seconds": "28-30秒", "note": "「保存して復習して」", "camera": "正面"},
                ],
                "tips": [
                    "ホワイトボードやiPadがあると図解しやすい",
                    "1メッセージ1画面を意識",
                    "難しい言葉を使わない",
                    "通しで撮ってOK",
                ],
            },
        },
    },
    "product": {
        "name": "商品紹介・レビュー",
        "patterns": {
            "review": {
                "name": "正直レビュー型",
                "description": "メリット・デメリット両方見せて信頼感UP",
                "duration": 30,
                "structure": [
                    {"name": "商品フック", "seconds": "0-3秒", "note": "商品を見せる", "camera": "商品アップ + 手持ち"},
                    {"name": "メリット", "seconds": "3-13秒", "note": "良い点を2-3個", "camera": "使用シーン + 顔リアクション"},
                    {"name": "デメリット", "seconds": "13-20秒", "note": "正直に悪い点も", "camera": "正面で語る"},
                    {"name": "総評", "seconds": "20-27秒", "note": "「○○な人にはおすすめ」", "camera": "正面バストアップ"},
                    {"name": "CTA", "seconds": "27-30秒", "note": "「リンクはプロフ」等", "camera": "正面 + 商品"},
                ],
                "tips": [
                    "開封シーンがあるとワクワク感UP",
                    "実際に使っている場面を必ず撮る",
                    "価格が映る場面を入れる",
                    "デメリットも言うと信頼される",
                ],
            },
        },
    },
}

# ── 共通の撮影ルール ──

UNIVERSAL_RULES = """
━━━ 基本ルール（毎回守ること） ━━━

  撮影方向:  縦撮り（スマホ縦持ち）必須！！
  解像度:    1080x1920 以上（スマホのカメラ設定で確認）
  明るさ:    自然光ベスト。暗い場所NG
  手ブレ:    三脚 or 壁に肘をつけて安定させる
  余白:      上下に余白を残す（テロップを入れるので）
  音声:      周囲の雑音に注意（エアコン、テレビ消す）
  長さ:      各カット、指定秒数の2倍くらい長めに撮る（編集で切る）
  保存:      撮ったらすぐ input/ フォルダに入れる
""".strip()


def list_genres():
    """ジャンル・パターン一覧を表示"""
    print("\n━━━ 使えるジャンル・パターン一覧 ━━━\n")
    for gid, genre in GENRES.items():
        print(f"  {genre['name']} (--genre {gid})")
        for pid, pattern in genre["patterns"].items():
            print(f"    └ {pattern['name']} (--pattern {pid})")
            print(f"      {pattern['description']}  [{pattern['duration']}秒]")
        print()


def generate_brief(genre_id, pattern_id=None, theme=None):
    """撮影指示書を生成"""
    genre = GENRES.get(genre_id)
    if not genre:
        print(f"❌ ジャンルが見つかりません: {genre_id}")
        print("  使えるジャンル: " + ", ".join(GENRES.keys()))
        sys.exit(1)

    # パターン未指定なら最初のパターンを使用
    if pattern_id is None:
        pattern_id = list(genre["patterns"].keys())[0]

    pattern = genre["patterns"].get(pattern_id)
    if not pattern:
        print(f"❌ パターンが見つかりません: {pattern_id}")
        print(f"  使えるパターン: {', '.join(genre['patterns'].keys())}")
        sys.exit(1)

    # GPTでテーマに合わせた指示書を生成
    ai_brief = None
    if theme:
        ai_brief = generate_ai_brief(genre, pattern, theme)

    # 指示書を組み立て
    today = datetime.now().strftime("%Y-%m-%d")
    theme_str = theme or f"{genre['name']}動画"

    lines = []
    lines.append("=" * 50)
    lines.append(f"  撮影指示書")
    lines.append("=" * 50)
    lines.append(f"")
    lines.append(f"  作成日:  {today}")
    lines.append(f"  テーマ:  {theme_str}")
    lines.append(f"  ジャンル: {genre['name']}")
    lines.append(f"  パターン: {pattern['name']}")
    lines.append(f"  目標尺:  {pattern['duration']}秒")
    lines.append(f"  {pattern['description']}")
    lines.append(f"")
    lines.append(UNIVERSAL_RULES)
    lines.append(f"")
    lines.append(f"━━━ 撮影カット表 ━━━")
    lines.append(f"")

    for i, shot in enumerate(pattern["structure"], 1):
        lines.append(f"  [{i}] {shot['name']}（{shot['seconds']}）")
        lines.append(f"      内容: {shot['note']}")
        lines.append(f"      カメラ: {shot['camera']}")
        if ai_brief and i <= len(ai_brief.get("shots", [])):
            lines.append(f"      具体的に: {ai_brief['shots'][i-1]}")
        lines.append(f"")

    lines.append(f"━━━ 撮影のコツ ━━━")
    lines.append(f"")
    for tip in pattern["tips"]:
        lines.append(f"  - {tip}")

    if ai_brief and ai_brief.get("extra_tips"):
        lines.append(f"")
        lines.append(f"━━━ テーマ固有のアドバイス ━━━")
        lines.append(f"")
        for tip in ai_brief["extra_tips"]:
            lines.append(f"  - {tip}")

    lines.append(f"")
    lines.append("=" * 50)
    lines.append(f"  撮り終わったら input/ に動画を入れて")
    lines.append(f"  run.sh を実行するだけ！")
    lines.append("=" * 50)

    return "\n".join(lines)


def generate_ai_brief(genre, pattern, theme):
    """GPTでテーマに合わせた具体的な撮影指示を生成"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        shots_desc = "\n".join(
            f"  カット{i+1}: {s['name']}（{s['seconds']}） - {s['note']}"
            for i, s in enumerate(pattern["structure"])
        )

        prompt = f"""テーマ「{theme}」の{genre['name']}TikTok動画の撮影指示を作って。

パターン: {pattern['name']}（{pattern['duration']}秒）
カット構成:
{shots_desc}

以下のJSON形式で出力:
{{
  "shots": ["カット1の具体的な撮影内容", "カット2の...", ...],
  "extra_tips": ["テーマ固有のアドバイス1", "アドバイス2", "アドバイス3"]
}}

- 各shotは1行で、何を撮ればいいか具体的に
- 撮影者が迷わないシンプルな指示
- JSONのみ出力"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"  (AI指示生成スキップ: {e})")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="撮影指示書ジェネレーター - 友人に渡す撮影ブリーフを自動生成",
    )
    parser.add_argument("--genre", help="ジャンル (beauty, food, travel, fitness, business, lifestyle, education, product)")
    parser.add_argument("--pattern", help="パターン (before-after, asmr, transition, etc.)")
    parser.add_argument("--theme", help="具体的なテーマ（例: 眉毛サロン体験）")
    parser.add_argument("--list", action="store_true", help="ジャンル・パターン一覧を表示")
    parser.add_argument("--save", action="store_true", help="ファイルに保存する")
    args = parser.parse_args()

    if args.list:
        list_genres()
        return

    if not args.genre:
        print("❌ --genre を指定してください。一覧は --list で確認できます。")
        sys.exit(1)

    brief = generate_brief(args.genre, args.pattern, args.theme)
    print(brief)

    if args.save:
        today = datetime.now().strftime("%Y-%m-%d")
        save_path = f"reports/brief_{args.genre}_{today}.txt"
        os.makedirs("reports", exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(brief)
        print(f"\n  保存しました: {save_path}")
        print(f"  → このファイルを友人に送ってください")


if __name__ == "__main__":
    main()
