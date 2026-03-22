#!/usr/bin/env python3
"""
バズ動画構成アナライザー

TikTok/Reels/Shorts等のURLから動画をDL → 構成を抽象化 → テンプレートとして保存。
複数URLを渡すと共通パターンを抽出してより強い型を生成。

使い方:
  # 1本のバズ動画から型を作る
  python scripts/analyze_buzz.py "https://www.tiktok.com/..." --client eyebrow_salon --name "ビフォアフ王道"

  # 複数のバズ動画から共通パターンを抽出
  python scripts/analyze_buzz.py "URL1" "URL2" "URL3" --client eyebrow_salon --name "美容系バズ型"

  # クライアントなしでも使える（templates/ に保存）
  python scripts/analyze_buzz.py "URL" --name "料理バズ型"
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime


# ═══════════════════════════════════════════════════
#  Step 1: 動画ダウンロード
# ═══════════════════════════════════════════════════

def download_video(url, output_dir):
    """yt-dlp で動画をダウンロード"""
    print(f"  ⬇️  ダウンロード中: {url[:60]}...")

    output_path = os.path.join(output_dir, "%(id)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f", "mp4/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", output_path,
        "--print", "after_move:filepath",
        "--no-warnings",
        url
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    ❌ ダウンロード失敗: {result.stderr[-200:]}")
        return None

    filepath = result.stdout.strip().split("\n")[-1]
    if os.path.exists(filepath):
        return filepath

    # fallback: output_dir内の最新mp4を探す
    mp4s = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith(".mp4")]
    return max(mp4s, key=os.path.getmtime) if mp4s else None


# ═══════════════════════════════════════════════════
#  Step 2: 動画解析（ffprobe + Whisper）
# ═══════════════════════════════════════════════════

def analyze_video(path):
    """ffprobe でメタデータ取得"""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"duration": 0, "width": 0, "height": 0}

    info = json.loads(result.stdout)
    vs = next((s for s in info.get("streams", []) if s["codec_type"] == "video"), None)
    duration = float(info.get("format", {}).get("duration", 0))

    return {
        "duration": round(duration, 1),
        "width": int(vs["width"]) if vs else 0,
        "height": int(vs["height"]) if vs else 0,
    }


def transcribe_video(path):
    """Whisper で文字起こし"""
    try:
        import whisper
        model_name = os.environ.get("WHISPER_MODEL", "medium")
        model = whisper.load_model(model_name)
        result = model.transcribe(path, language="ja", word_timestamps=True, verbose=False)
        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": round(seg["start"], 2),
                "end": round(seg["end"], 2),
                "text": seg["text"].strip(),
            })
        return {"text": result.get("text", ""), "segments": segments}
    except ImportError:
        pass

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        with open(path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-1", file=f, language="ja",
                response_format="verbose_json",
                timestamp_granularities=["segment"]
            )
        segments = []
        for i, seg in enumerate(result.segments or []):
            segments.append({
                "start": round(seg["start"], 2),
                "end": round(seg["end"], 2),
                "text": seg["text"].strip(),
            })
        return {"text": result.text, "segments": segments}
    except Exception:
        return None


# ═══════════════════════════════════════════════════
#  Step 3: GPT で構成を抽象化
# ═══════════════════════════════════════════════════

def abstract_structure_single(video_info, transcript, url):
    """1本の動画から構成を抽象化"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("  ⚠️  OPENAI_API_KEY が必要です。")
        return None

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    duration = video_info["duration"]
    text = transcript.get("text", "") if transcript else "(音声なし)"
    segments_json = json.dumps(transcript.get("segments", []), ensure_ascii=False) if transcript else "[]"

    prompt = f"""あなたはTikTokのバズ動画を分析するプロです。

以下のバズ動画の構成を分析し、**再利用可能なテンプレート**として抽象化してください。

## 動画情報
- URL: {url}
- 尺: {duration}秒
- 文字起こし: {text}
- セグメント: {segments_json}

## 分析して欲しいこと

### 構成テンプレート（structure）:
動画の構成を時間軸で分解し、各パートの「役割」を抽象化してください。
具体的な内容ではなく「どんな役割のパートか」を記述。
例: 「完成品を見せてフックする」「過程を早送りで見せる」「CTAで締める」

### 各パートのテロップ指示（telop_guide）:
テンプレートとして使える形で、各パートにどんなテロップを入れるべきか。
具体的な文面ではなく、方針を記述。
例: 「結果を端的に（8文字以内）」「手順番号+動作（○○する）」

### この型が効く理由（why_it_works）:
なぜこの構成がバズるのか。心理的なメカニズムを1-2文で。

### この型の適用ジャンル（applicable_genres）:
この構成が使えるジャンルのリスト。

## 出力（JSON厳守）:
{{
  "template_name": "この型の名前（例: 完成品フック型）",
  "total_duration": {duration},
  "structure": [
    {{
      "part_name": "パートの名前",
      "role": "このパートの役割（抽象的に）",
      "start_ratio": 0.0,
      "end_ratio": 0.1,
      "duration_sec": 3,
      "telop_guide": "テロップの方針",
      "telop_position": "center",
      "telop_color": "white",
      "camera_guide": "撮影時のカメラワーク指示",
      "editing_note": "編集時の注意点"
    }}
  ],
  "why_it_works": "この型が効く理由",
  "applicable_genres": ["beauty", "food"],
  "hook_pattern": "冒頭のフックパターンの説明",
  "cta_pattern": "CTAの型",
  "source_transcript": "{text[:100]}"
}}

JSONのみ出力。"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"  ⚠️  GPTエラー: {e}")
        return None


def merge_templates(templates):
    """複数のテンプレートから共通パターンを抽出"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return templates[0] if templates else None

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    templates_json = json.dumps(templates, ensure_ascii=False, indent=2)

    prompt = f"""以下の{len(templates)}本のバズ動画から抽出した構成テンプレートがあります。

{templates_json}

これらの共通パターンを分析し、1つの「最強テンプレート」に統合してください。

ルール:
- 全てのテンプレートに共通する要素を抽出
- 時間配分は平均値を使う
- 各パートのroleは抽象的に（特定の動画に依存しない表現で）
- 共通していないパートは除外するか、オプションとして注記
- template_nameは統合された型の名前をつける

出力は1つのテンプレートJSON（先ほどと同じフォーマット）。
追加フィールド:
- "source_count": 統合元の動画数
- "confidence": 共通度合い（0.0〜1.0、全パートが共通なら1.0）
- "variations": 動画ごとに異なっていた点のリスト

JSONのみ出力。"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"  ⚠️  統合エラー: {e}")
        return templates[0] if templates else None


# ═══════════════════════════════════════════════════
#  Step 4: テンプレート保存
# ═══════════════════════════════════════════════════

def save_template(template, name, client_id=None):
    """テンプレートを保存"""
    if client_id:
        tmpl_dir = os.path.join("clients", client_id, "templates")
    else:
        tmpl_dir = "templates"
    os.makedirs(tmpl_dir, exist_ok=True)

    safe_name = name.replace(" ", "_").replace("/", "_")
    filename = f"{safe_name}.json"
    filepath = os.path.join(tmpl_dir, filename)

    # メタデータ追加
    template["_meta"] = {
        "name": name,
        "created_at": datetime.now().isoformat(),
        "client_id": client_id,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)

    return filepath


def list_templates(client_id=None):
    """保存済みテンプレート一覧"""
    dirs = []
    if client_id:
        dirs.append(os.path.join("clients", client_id, "templates"))
    dirs.append("templates")  # グローバルも含む

    templates = []
    for d in dirs:
        if not os.path.exists(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith(".json"):
                path = os.path.join(d, f)
                with open(path, encoding="utf-8") as fh:
                    tmpl = json.load(fh)
                templates.append({
                    "path": path,
                    "name": tmpl.get("_meta", {}).get("name", f),
                    "template_name": tmpl.get("template_name", ""),
                    "duration": tmpl.get("total_duration", 0),
                    "parts": len(tmpl.get("structure", [])),
                })
    return templates


# ═══════════════════════════════════════════════════
#  メイン
# ═══════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="バズ動画の構成を抽象化 → テンプレートとして保存",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("urls", nargs="+", help="バズ動画のURL（複数指定で共通パターン抽出）")
    parser.add_argument("--name", required=True, help="テンプレートの名前（例: ビフォアフ王道）")
    parser.add_argument("--client", help="クライアントID")
    parser.add_argument("--keep-video", action="store_true", help="DLした動画を残す")
    args = parser.parse_args()

    print("=" * 55)
    print("  Video AIops - バズ動画構成アナライザー")
    print("=" * 55)
    print(f"\n  動画数: {len(args.urls)}本")
    print(f"  テンプレート名: {args.name}")
    if args.client:
        print(f"  クライアント: {args.client}")

    # 作業ディレクトリ
    work_dir = tempfile.mkdtemp(prefix="buzz_")

    templates = []

    for i, url in enumerate(args.urls):
        print(f"\n{'─' * 55}")
        print(f"  [{i+1}/{len(args.urls)}] {url[:70]}")
        print(f"{'─' * 55}")

        # ダウンロード
        video_path = download_video(url, work_dir)
        if not video_path:
            print("  → スキップ")
            continue

        # 解析
        print(f"  🔍 動画を解析中...")
        video_info = analyze_video(video_path)
        print(f"    → {video_info['duration']}秒, {video_info['width']}x{video_info['height']}")

        # 文字起こし
        print(f"  📝 文字起こし中...")
        transcript = transcribe_video(video_path)
        if transcript:
            print(f"    → {len(transcript.get('segments', []))}セグメント")
        else:
            print(f"    → 音声なし or 文字起こし失敗")

        # 構成抽象化
        print(f"  🤖 構成を抽象化中...")
        template = abstract_structure_single(video_info, transcript, url)
        if template:
            template["source_url"] = url
            templates.append(template)
            print(f"    → {template.get('template_name', '?')}")
            print(f"    → {len(template.get('structure', []))}パート構成")
            print(f"    → 理由: {template.get('why_it_works', '')[:60]}")
        else:
            print(f"    → 抽象化失敗")

        # DL動画を削除（--keep-videoでなければ）
        if not args.keep_video and os.path.exists(video_path):
            os.remove(video_path)

    if not templates:
        print("\n  ❌ テンプレートを生成できませんでした。")
        sys.exit(1)

    # 複数テンプレートの統合
    if len(templates) > 1:
        print(f"\n🔀 {len(templates)}本の型を統合中...")
        merged = merge_templates(templates)
        if merged:
            merged["source_urls"] = [t.get("source_url", "") for t in templates]
            final_template = merged
        else:
            final_template = templates[0]
    else:
        final_template = templates[0]

    # 保存
    filepath = save_template(final_template, args.name, args.client)

    # 結果表示
    print(f"\n{'=' * 55}")
    print(f"  ✅ テンプレート保存完了!")
    print(f"{'=' * 55}")
    print(f"\n  📋 ファイル: {filepath}")
    print(f"  📛 型の名前: {final_template.get('template_name', args.name)}")
    print(f"  ⏱️  目標尺: {final_template.get('total_duration', '?')}秒")

    structure = final_template.get("structure", [])
    if structure:
        print(f"\n  ── 構成 ──")
        for part in structure:
            dur = part.get("duration_sec", "?")
            print(f"    [{dur}秒] {part.get('part_name', '')} — {part.get('role', '')}")

    print(f"\n  💡 理由: {final_template.get('why_it_works', '')}")

    if final_template.get("applicable_genres"):
        print(f"  🎯 適用ジャンル: {', '.join(final_template['applicable_genres'])}")

    print(f"\n  次のステップ:")
    print(f"  → python ops.py でメニューから「バズの型で投稿プラン生成」を選択")
    print(f"  → または: python scripts/planner.py --client {args.client or 'CLIENT_ID'} --template {filepath}")
    print()

    # 作業ディレクトリのクリーンアップ
    try:
        os.rmdir(work_dir)
    except OSError:
        pass


if __name__ == "__main__":
    main()
