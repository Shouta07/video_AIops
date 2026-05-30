#!/usr/bin/env python3
"""
His Recoveries リールスクリプト自動生成

仮説に基づいてリールのスクリプトをGemini/GPTで自動生成。
生成されたJSONをreel_editor.pyに渡すと動画が自動生成される。

使い方:
  python instagram/script_writer.py --hypothesis hygiene --type card
  python instagram/script_writer.py --hypothesis confidence --type slide
  python instagram/script_writer.py --hypothesis loneliness --type question
  python instagram/script_writer.py --hypothesis hygiene --batch  # 全タイプ一括生成
"""
import argparse
import json
import os
import sys
from datetime import datetime

# ── 仮説定義 ──

HYPOTHESES = {
    "hygiene": {
        "name": "清潔感",
        "insight": "清潔感は顔じゃなくて手入れで決まる",
        "target_emotion": "気づき",
        "keywords": ["清潔感", "手入れ", "身だしなみ", "整える"],
    },
    "aging_anxiety": {
        "name": "加齢不安",
        "insight": "30代で肌が変わる。気づいた時がスタート",
        "target_emotion": "焦りと安心",
        "keywords": ["老化", "肌", "30代", "エイジング"],
    },
    "confidence": {
        "name": "自信",
        "insight": "自信は整えた先にある",
        "target_emotion": "共感と希望",
        "keywords": ["自信", "自己肯定", "変わりたい", "整える"],
    },
    "presence": {
        "name": "第一印象",
        "insight": "印象は3秒で決まる。整え方で変わる",
        "target_emotion": "危機感",
        "keywords": ["第一印象", "印象", "見た目", "3秒"],
    },
    "recovery_story": {
        "name": "回復体験",
        "insight": "過去の自分と向き合った記録",
        "target_emotion": "共感と勇気",
        "keywords": ["体験談", "回復", "過去", "変化"],
    },
    "loneliness": {
        "name": "孤独",
        "insight": "誰にも言えない悩みがある。それでいい",
        "target_emotion": "深い共感",
        "keywords": ["孤独", "悩み", "相談", "一人"],
    },
    "self_investment": {
        "name": "自己投資",
        "insight": "毎朝5分の投資が、1年後の自分を変える",
        "target_emotion": "納得と行動",
        "keywords": ["自己投資", "習慣", "毎朝", "5分"],
    },
    "conditioning": {
        "name": "コンディション",
        "insight": "整えるのは見た目じゃなくて、体調から",
        "target_emotion": "ハッとする気づき",
        "keywords": ["体調", "睡眠", "疲労", "回復"],
    },
}

REEL_TYPES = {
    "card": "一言カード型（テキスト1枚 + BGM / 5-10秒）",
    "slide": "3段階スライド型（過去→現在→気づき / 15秒）",
    "question": "問いかけ型（質問 + 選択肢 / 5-10秒）",
}


def generate_script(hypothesis_id, reel_type):
    """GPT/Geminiでスクリプトを生成"""
    hyp = HYPOTHESES.get(hypothesis_id)
    if not hyp:
        print(f"  ❌ 仮説が見つかりません: {hypothesis_id}")
        print(f"  使える仮説: {', '.join(HYPOTHESES.keys())}")
        return None

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("  ⚠️  OPENAI_API_KEY 未設定。テンプレートスクリプトを生成します。")
        return generate_fallback(hypothesis_id, reel_type, hyp)

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    type_instructions = {
        "card": """
一言カード型:
- テキストは1文。30文字以内。句読点で余韻を残す
- Aesop/Kinfolk的な静かな知性。説教しない
- 読んだ人が2秒止まる言葉
出力: {"type": "card", "text": "テキスト", "subtitle": "サブ（任意）", "duration": 8}""",
        "slide": """
3段階スライド型:
- 3枚のテキストカード: 過去→現在→気づき（ただ、〜）
- 各テキスト20文字以内
- 3枚目で視聴者がハッとする構成
出力: {"type": "slide", "texts": ["1枚目", "2枚目", "3枚目"], "duration_per_slide": 5}""",
        "question": """
問いかけ型:
- 質問は1文。20文字以内
- 選択肢は3-4個。短く
- 「あるある」で共感を誘う
出力: {"type": "question", "question": "質問文", "options": ["選択肢1", "選択肢2", "選択肢3"], "duration": 10}""",
    }

    prompt = f"""His Recoveriesのリールスクリプトを書いてください。

ブランド: His Recoveries（男性の整えを支援するブランド）
仮説: {hyp['name']}
インサイト: {hyp['insight']}
狙う感情: {hyp['target_emotion']}
キーワード: {', '.join(hyp['keywords'])}

トーン:
- 静かな知性。Monocle的
- 押し付けない。気づかせる
- 顔出しなし。テキストで語る
- 「〜してください」は使わない
- 自然体。飾らない

リール型:
{type_instructions[reel_type]}

追加フィールド（必須）:
- "hypothesis": "{hypothesis_id}"
- "mood": 推奨BGMジャンル（lo-fi / ambient / chill / acoustic）
- "visual_note": 推奨ビジュアル（手元 / 窓際 / 朝の光 / シルエット 等）

JSONのみ出力。"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            response_format={"type": "json_object"},
        )
        script = json.loads(response.choices[0].message.content)
        script["hypothesis"] = hypothesis_id
        return script
    except Exception as e:
        print(f"  ⚠️  APIエラー: {e}")
        return generate_fallback(hypothesis_id, reel_type, hyp)


def generate_fallback(hypothesis_id, reel_type, hyp):
    """APIなしのフォールバック"""
    if reel_type == "card":
        return {
            "type": "card",
            "text": hyp["insight"],
            "subtitle": "",
            "duration": 8,
            "hypothesis": hypothesis_id,
            "mood": "lo-fi",
            "visual_note": "暖色の背景",
        }
    elif reel_type == "slide":
        return {
            "type": "slide",
            "texts": [
                f"{hyp['keywords'][0]}を気にしてなかった",
                "ある日ふと気づいた",
                f"ただ、{hyp['insight'][:15]}",
            ],
            "duration_per_slide": 5,
            "hypothesis": hypothesis_id,
            "mood": "ambient",
            "visual_note": "朝の光→鏡→静かな空間",
        }
    elif reel_type == "question":
        return {
            "type": "question",
            "question": f"{hyp['name']}で一番気になるのは？",
            "options": hyp["keywords"][:4],
            "duration": 10,
            "hypothesis": hypothesis_id,
            "mood": "chill",
            "visual_note": "ベージュ背景",
        }


def main():
    parser = argparse.ArgumentParser(
        description="His Recoveries リールスクリプト自動生成",
    )
    parser.add_argument("--hypothesis", help="仮説ID（hygiene, confidence, etc.）")
    parser.add_argument("--type", choices=list(REEL_TYPES.keys()), help="リール型")
    parser.add_argument("--batch", action="store_true", help="全タイプを一括生成")
    parser.add_argument("--list", action="store_true", help="仮説・リール型の一覧")
    args = parser.parse_args()

    if args.list:
        print("\n  ── 仮説一覧 ──")
        for hid, hyp in HYPOTHESES.items():
            print(f"  {hid:20s}  {hyp['name']:8s}  {hyp['insight']}")
        print("\n  ── リール型 ──")
        for tid, desc in REEL_TYPES.items():
            print(f"  {tid:12s}  {desc}")
        print()
        return

    if not args.hypothesis:
        print("  ❌ --hypothesis を指定してください（--list で一覧表示）")
        sys.exit(1)

    print("=" * 50)
    print("  His Recoveries - スクリプト生成")
    print("=" * 50)

    os.makedirs("instagram/output", exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    if args.batch:
        types = list(REEL_TYPES.keys())
    elif args.type:
        types = [args.type]
    else:
        types = ["card"]

    for rtype in types:
        print(f"\n  仮説: {args.hypothesis} / 型: {rtype}")
        script = generate_script(args.hypothesis, rtype)
        if script:
            filename = f"script_{args.hypothesis}_{rtype}_{today}.json"
            filepath = os.path.join("instagram/output", filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(script, f, ensure_ascii=False, indent=2)
            print(f"  ✅ {filepath}")

            # プレビュー
            if rtype == "card":
                print(f"    → 「{script.get('text', '')}」")
            elif rtype == "slide":
                for i, t in enumerate(script.get("texts", []), 1):
                    print(f"    → [{i}] {t}")
            elif rtype == "question":
                print(f"    → 「{script.get('question', '')}」")
                for opt in script.get("options", []):
                    print(f"       - {opt}")

            print(f"    BGM: {script.get('mood', '')}")
            print(f"    ビジュアル: {script.get('visual_note', '')}")
            print(f"\n    動画生成: python instagram/reel_editor.py --script {filepath}")

    print()


if __name__ == "__main__":
    main()
