#!/usr/bin/env python3
"""
Video AIops パイプライン - 素材を投げるだけで全自動

使い方:
  python scripts/pipeline.py input/eyebrow.mp4
  python scripts/pipeline.py input/eyebrow.mp4 --genre beauty
  python scripts/pipeline.py input/eyebrow.mp4 --genre beauty --skip-render

何をするか:
  1. ffprobe で素材解析
  2. Whisper で音声文字起こし
  3. GPT でバズるテロップ構成を自動生成（色・サイズ・タイミング含む）
  4. TikTok / Reels / Shorts 向けに一括書き出し
  5. 投稿文・ハッシュタグ・ベスト投稿時間のレポート生成
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

# ───────────── 設定 ─────────────

PLATFORMS = {
    "tiktok": {"w": 1080, "h": 1920, "max_sec": 60, "label": "TikTok"},
    "reels":  {"w": 1080, "h": 1920, "max_sec": 90, "label": "Reels"},
    "shorts": {"w": 1080, "h": 1920, "max_sec": 60, "label": "YouTube Shorts"},
}

FONT_MAC = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
FONT_LINUX = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

def get_font():
    if os.path.exists(FONT_MAC):
        return FONT_MAC
    if os.path.exists(FONT_LINUX):
        return FONT_LINUX
    # fallback: try fc-match
    try:
        result = subprocess.run(["fc-match", "--format=%{file}", "sans:lang=ja:weight=bold"],
                                capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    print("警告: 日本語フォントが見つかりません。テロップが正しく表示されない可能性があります。")
    return "sans"

# ───────────── Step 1: 素材解析 ─────────────

def analyze_video(path):
    """ffprobe で動画のメタデータを取得"""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"エラー: ffprobe 失敗\n{result.stderr}")
        sys.exit(1)

    info = json.loads(result.stdout)
    video_stream = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    audio_stream = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)

    duration = float(info["format"].get("duration", 0))
    width = int(video_stream["width"]) if video_stream else 0
    height = int(video_stream["height"]) if video_stream else 0

    return {
        "duration": duration,
        "width": width,
        "height": height,
        "has_audio": audio_stream is not None,
        "fps": eval(video_stream.get("r_frame_rate", "30/1")) if video_stream else 30,
    }


# ───────────── Step 2: Whisper 文字起こし ─────────────

def transcribe(path):
    """Whisper で文字起こし。ローカル版を優先、なければ OpenAI API"""
    print("\n📝 文字起こし中...")

    # ローカル Whisper を試す
    try:
        import whisper
        model_name = os.environ.get("WHISPER_MODEL", "medium")
        sys.stderr.write(f"  Whisper '{model_name}' モデルを読み込み中...\n")
        model = whisper.load_model(model_name)
        sys.stderr.write(f"  文字起こし実行中...\n")
        result = model.transcribe(path, language="ja", word_timestamps=True, verbose=False)
        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "id": seg["id"],
                "start": round(seg["start"], 2),
                "end": round(seg["end"], 2),
                "text": seg["text"].strip(),
            })
        return {"text": result.get("text", ""), "segments": segments}
    except ImportError:
        pass

    # OpenAI API フォールバック
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("  ⚠️  Whisper もインストールされておらず、OPENAI_API_KEY も未設定です。")
        print("  → テロップは手動入力モードになります。")
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        with open(path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="ja",
                response_format="verbose_json",
                timestamp_granularities=["segment"]
            )
        segments = []
        for i, seg in enumerate(result.segments or []):
            segments.append({
                "id": i,
                "start": round(seg["start"], 2),
                "end": round(seg["end"], 2),
                "text": seg["text"].strip(),
            })
        return {"text": result.text, "segments": segments}
    except Exception as e:
        print(f"  ⚠️  OpenAI API エラー: {e}")
        return None


# ───────────── Step 3: GPT でバズるテロップ構成を生成 ─────────────

def generate_telop_and_strategy(transcript, video_info, genre):
    """GPTでテロップ構成 + 投稿戦略を一括生成"""
    print("\n🤖 AIがテロップ構成と投稿戦略を生成中...")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("  ⚠️  OPENAI_API_KEY が未設定です。デフォルトテロップを使用します。")
        return generate_fallback(transcript, video_info)

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    duration = video_info["duration"]
    transcript_text = transcript["text"] if transcript else "(音声なし)"
    segments_json = json.dumps(transcript["segments"], ensure_ascii=False) if transcript else "[]"

    prompt = f"""あなたはTikTok/Reelsのバズ動画を作るプロの編集者です。

以下の動画素材の文字起こしを元に、バズるテロップ構成と投稿戦略を生成してください。

## 素材情報
- 長さ: {duration:.1f}秒
- ジャンル: {genre}
- 文字起こし全文: {transcript_text}
- セグメント（タイミング付き）: {segments_json}

## 生成ルール

### テロップ（captions）:
- 動画の長さに合わせて自然なタイミングで配置
- 冒頭2秒で「引き」のあるフックテロップ（視聴者が離脱しないように）
- 話の内容を要約・強調する形で（文字起こしそのままではなく、短く刺さる表現に）
- 重要なシーンは色を変える（yellow, #FF69B4 など）
- 最後にCTA（フォロー誘導）を入れる。色はライトピンク(#FFB6C1)で親しみやすく
- 各テロップは15文字以内が理想
- y位置は 0.55〜0.60 の範囲（画面中央やや下）

### 投稿キャプション（post_caption）:
- TikTok向けの投稿文（150文字以内）
- 共感を誘う文体で
- 絵文字は控えめに

### ハッシュタグ（hashtags）:
- 10〜15個
- バズタグ + ニッチタグを混ぜる（大：中：小 = 3:4:3 の比率）
- 先頭に最も重要なタグ

### 投稿タイミング（best_times）:
- 曜日と時間帯を3つ提案
- ジャンルのターゲット層を考慮

## 出力フォーマット（JSON厳守）:
{{
  "captions": [
    {{"start": 0, "end": 2.5, "text": "テロップ内容", "size": 60, "color": "white", "y": 0.57}},
    ...
  ],
  "post_caption": "投稿文テキスト",
  "hashtags": ["#タグ1", "#タグ2", ...],
  "best_times": [
    {{"day": "金曜", "time": "19:00-21:00", "reason": "理由"}},
    ...
  ],
  "hook_analysis": "冒頭の引きの解説（1文）",
  "target_audience": "ターゲット層（1文）"
}}

JSONのみを出力してください。説明文は不要です。"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        print(f"  ⚠️  GPT生成エラー: {e}")
        return generate_fallback(transcript, video_info)


def generate_fallback(transcript, video_info):
    """GPTが使えない場合のフォールバック"""
    duration = video_info["duration"]
    captions = []
    if transcript and transcript.get("segments"):
        for seg in transcript["segments"]:
            text = seg["text"]
            if len(text) > 15:
                text = text[:14] + "…"
            captions.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": text,
                "size": 56,
                "color": "white",
                "y": 0.57,
            })
        # CTA追加
        captions.append({
            "start": duration - 4,
            "end": duration,
            "text": "フォローで見守ってね",
            "size": 54,
            "color": "#FFB6C1",
            "y": 0.60,
        })
    return {
        "captions": captions,
        "post_caption": "",
        "hashtags": [],
        "best_times": [],
        "hook_analysis": "",
        "target_audience": "",
    }


# ───────────── Step 4: マルチプラットフォーム書き出し ─────────────

def render_all_platforms(input_path, captions, video_info, font):
    """TikTok / Reels / Shorts に一括書き出し"""
    print("\n🎬 マルチプラットフォーム書き出し中...")

    outputs = {}
    for platform_id, spec in PLATFORMS.items():
        output_dir = f"output/{platform_id}"
        os.makedirs(output_dir, exist_ok=True)

        basename = os.path.splitext(os.path.basename(input_path))[0]
        output_path = f"{output_dir}/{basename}_final.mp4"

        # 尺の制限
        duration = min(video_info["duration"], spec["max_sec"])

        # drawtext フィルタ構築
        vf_parts = []
        for c in captions:
            if c["start"] >= duration:
                continue
            color = c["color"]
            if color.startswith("#"):
                color = "0x" + color[1:]
            end = min(c["end"], duration)
            text_escaped = c["text"].replace("'", "\u2019").replace(":", "\\:")
            vf_parts.append(
                f"drawtext=text='{text_escaped}'"
                f":fontfile='{font}'"
                f":fontsize={c['size']}"
                f":fontcolor={color}"
                f":borderw=4:bordercolor=black"
                f":x=(w-tw)/2:y=h*{c['y']}"
                f":enable='between(t,{c['start']},{end})'"
            )

        vf = ",".join(vf_parts) if vf_parts else "null"

        cmd = [
            "ffmpeg", "-y",
            "-ss", "0", "-t", str(duration),
            "-i", input_path,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart",
            output_path
        ]

        print(f"  📦 {spec['label']} → {output_path}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"    ❌ エラー: {result.stderr[-200:]}")
        else:
            outputs[platform_id] = output_path

    return outputs


# ───────────── Step 5: レポート生成 ─────────────

def generate_report(video_info, transcript, ai_result, outputs, input_path, genre):
    """投稿戦略レポートを生成"""
    print("\n📊 投稿戦略レポート生成中...")

    today = datetime.now().strftime("%Y-%m-%d")
    report_path = f"reports/strategy_{today}.md"
    os.makedirs("reports", exist_ok=True)

    basename = os.path.basename(input_path)

    lines = [
        f"# 投稿戦略レポート",
        f"",
        f"**生成日**: {today}  ",
        f"**素材**: {basename}  ",
        f"**ジャンル**: {genre}  ",
        f"**素材尺**: {video_info['duration']:.1f}秒  ",
        f"",
        f"---",
        f"",
        f"## フック分析",
        f"",
        f"{ai_result.get('hook_analysis', '(未生成)')}",
        f"",
        f"## ターゲット",
        f"",
        f"{ai_result.get('target_audience', '(未生成)')}",
        f"",
        f"---",
        f"",
        f"## 投稿キャプション（コピペ用）",
        f"",
        f"```",
        f"{ai_result.get('post_caption', '')}",
        f"```",
        f"",
        f"## ハッシュタグ（コピペ用）",
        f"",
        f"```",
        f"{' '.join(ai_result.get('hashtags', []))}",
        f"```",
        f"",
        f"## ベスト投稿タイミング",
        f"",
    ]

    for bt in ai_result.get("best_times", []):
        lines.append(f"- **{bt.get('day', '')} {bt.get('time', '')}** — {bt.get('reason', '')}")

    lines += [
        f"",
        f"---",
        f"",
        f"## 書き出しファイル",
        f"",
    ]

    for platform_id, path in outputs.items():
        label = PLATFORMS[platform_id]["label"]
        lines.append(f"- **{label}**: `{path}`")

    lines += [
        f"",
        f"---",
        f"",
        f"## テロップ構成",
        f"",
        f"| 時間 | テロップ | 色 |",
        f"|------|----------|-----|",
    ]

    for c in ai_result.get("captions", []):
        lines.append(f"| {c['start']:.1f}s〜{c['end']:.1f}s | {c['text']} | {c['color']} |")

    if transcript:
        lines += [
            f"",
            f"---",
            f"",
            f"## 文字起こし（全文）",
            f"",
            f"```",
            f"{transcript.get('text', '')}",
            f"```",
        ]

    report = "\n".join(lines) + "\n"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    return report_path


# ───────────── メイン ─────────────

def main():
    parser = argparse.ArgumentParser(
        description="Video AIops パイプライン - 素材投入→テロップ→書き出し→投稿戦略を全自動",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", help="入力動画ファイルのパス")
    parser.add_argument("--genre", default="beauty",
                        choices=["beauty", "food", "travel", "fitness", "business", "lifestyle", "education", "product"],
                        help="動画のジャンル（デフォルト: beauty）")
    parser.add_argument("--skip-render", action="store_true", help="動画書き出しをスキップ")
    parser.add_argument("--skip-transcribe", action="store_true", help="文字起こしをスキップ")
    parser.add_argument("--captions-json", help="既存のcaptions.jsonを使用")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ ファイルが見つかりません: {args.input}")
        sys.exit(1)

    print("=" * 50)
    print("  Video AIops パイプライン")
    print("=" * 50)
    print(f"  入力: {args.input}")
    print(f"  ジャンル: {args.genre}")

    # Step 1: 素材解析
    print("\n🔍 素材を解析中...")
    video_info = analyze_video(args.input)
    print(f"  → {video_info['width']}x{video_info['height']}, {video_info['duration']:.1f}秒, 音声{'あり' if video_info['has_audio'] else 'なし'}")

    # Step 2: 文字起こし
    transcript = None
    if not args.skip_transcribe and video_info["has_audio"]:
        transcript = transcribe(args.input)
        if transcript:
            print(f"  → {len(transcript['segments'])}セグメント取得")
    else:
        print("\n📝 文字起こしスキップ")

    # Step 3: AIテロップ構成 + 投稿戦略
    if args.captions_json:
        with open(args.captions_json, encoding="utf-8") as f:
            ai_result = {"captions": json.load(f), "post_caption": "", "hashtags": [], "best_times": []}
    else:
        ai_result = generate_telop_and_strategy(transcript, video_info, args.genre)

    captions = ai_result.get("captions", [])
    print(f"  → テロップ {len(captions)}個生成")

    # テロップJSON保存
    captions_path = "scripts/captions_generated.json"
    with open(captions_path, "w", encoding="utf-8") as f:
        json.dump(captions, f, ensure_ascii=False, indent=2)
    print(f"  → テロップ保存: {captions_path}")

    # Step 4: マルチプラットフォーム書き出し
    outputs = {}
    font = get_font()
    if not args.skip_render:
        outputs = render_all_platforms(args.input, captions, video_info, font)
    else:
        print("\n🎬 書き出しスキップ")

    # Step 5: レポート生成
    report_path = generate_report(video_info, transcript, ai_result, outputs, args.input, args.genre)
    print(f"  → レポート保存: {report_path}")

    # 完了サマリー
    print("\n" + "=" * 50)
    print("  ✅ 完了!")
    print("=" * 50)

    if outputs:
        print("\n  📦 書き出しファイル:")
        for pid, path in outputs.items():
            print(f"     {PLATFORMS[pid]['label']}: {path}")

    if ai_result.get("post_caption"):
        print(f"\n  📝 投稿キャプション:")
        print(f"     {ai_result['post_caption'][:80]}...")

    if ai_result.get("hashtags"):
        print(f"\n  #️ ハッシュタグ:")
        print(f"     {' '.join(ai_result['hashtags'][:5])}...")

    if ai_result.get("best_times"):
        print(f"\n  ⏰ ベスト投稿タイミング:")
        for bt in ai_result["best_times"][:2]:
            print(f"     {bt.get('day', '')} {bt.get('time', '')} — {bt.get('reason', '')}")

    print(f"\n  📊 詳細レポート: {report_path}")
    print(f"  💡 テロップ修正: {captions_path} を編集して再レンダリング可能")
    print(f"     → python scripts/pipeline.py {args.input} --captions-json {captions_path}")
    print()


if __name__ == "__main__":
    main()
