#!/usr/bin/env python3
"""
投稿プランナー - 大量素材を投入 → 投稿プラン → 動画結合 → キャプション生成

友人が撮ってきた素材を全部 input/ に入れて実行するだけ。

使い方:
  python scripts/planner.py --genre beauty
  python scripts/planner.py --genre beauty --dry-run     # プラン確認のみ（動画生成しない）
  python scripts/planner.py --genre beauty --recycle      # リサイクル提案も生成

何をするか:
  1. input/ の全素材を ffprobe + Whisper で一括解析
  2. GPT が素材を仕分け → 投稿単位にグループ化
  3. 各投稿の素材を ffmpeg で結合 + テロップ焼き込み
  4. 各投稿のキャプション・ハッシュタグ・投稿スケジュール生成
  5. 同じ素材から別切り口の投稿を提案（素材リサイクル）
  6. reports/plan_YYYY-MM-DD.md に投稿プラン一覧を出力
"""
import argparse
import glob
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}

FONT_MAC = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
FONT_LINUX = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"


def get_font():
    if os.path.exists(FONT_MAC):
        return FONT_MAC
    if os.path.exists(FONT_LINUX):
        return FONT_LINUX
    try:
        result = subprocess.run(["fc-match", "--format=%{file}", "sans:lang=ja:weight=bold"],
                                capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    return "sans"


# ═══════════════════════════════════════════════════
#  Step 1: 全素材を一括解析
# ═══════════════════════════════════════════════════

def find_videos(input_dir="input"):
    """input/ 内の動画ファイルを全検出"""
    videos = []
    for name in sorted(os.listdir(input_dir)):
        ext = os.path.splitext(name)[1].lower()
        if ext in VIDEO_EXTENSIONS:
            videos.append(os.path.join(input_dir, name))
    return videos


def analyze_video(path):
    """ffprobe でメタデータ取得"""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"path": path, "error": result.stderr, "filename": os.path.basename(path)}

    info = json.loads(result.stdout)
    vs = next((s for s in info.get("streams", []) if s["codec_type"] == "video"), None)
    audio = next((s for s in info.get("streams", []) if s["codec_type"] == "audio"), None)
    duration = float(info.get("format", {}).get("duration", 0))

    return {
        "path": path,
        "filename": os.path.basename(path),
        "duration": round(duration, 1),
        "width": int(vs["width"]) if vs else 0,
        "height": int(vs["height"]) if vs else 0,
        "has_audio": audio is not None,
        "is_vertical": (int(vs["height"]) > int(vs["width"])) if vs else False,
        "fps": eval(vs.get("r_frame_rate", "30/1")) if vs else 30,
    }


def generate_thumbnail(path, output_path):
    """動画の1秒目をサムネイル化"""
    cmd = [
        "ffmpeg", "-y", "-ss", "1", "-i", path,
        "-vframes", "1", "-vf", "scale=320:-1",
        output_path
    ]
    subprocess.run(cmd, capture_output=True)


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
                "id": i,
                "start": round(seg["start"], 2),
                "end": round(seg["end"], 2),
                "text": seg["text"].strip(),
            })
        return {"text": result.text, "segments": segments}
    except Exception:
        return None


def analyze_all(videos):
    """全素材を一括解析"""
    print(f"\n🔍 {len(videos)}個の素材を解析中...")
    catalog = []

    for i, path in enumerate(videos):
        print(f"  [{i+1}/{len(videos)}] {os.path.basename(path)}", end="")
        info = analyze_video(path)

        # サムネイル生成
        thumb_dir = "reports/thumbnails"
        os.makedirs(thumb_dir, exist_ok=True)
        thumb_path = os.path.join(thumb_dir, os.path.splitext(info["filename"])[0] + ".jpg")
        generate_thumbnail(path, thumb_path)
        info["thumbnail"] = thumb_path

        # 文字起こし（音声ありの場合のみ）
        if info.get("has_audio") and not info.get("error"):
            transcript = transcribe_video(path)
            info["transcript"] = transcript.get("text", "") if transcript else ""
            info["segments"] = transcript.get("segments", []) if transcript else []
        else:
            info["transcript"] = ""
            info["segments"] = []

        print(f"  → {info.get('duration', 0)}秒, {'音声あり' if info.get('has_audio') else '音声なし'}")
        catalog.append(info)

    return catalog


# ═══════════════════════════════════════════════════
#  Step 2: GPT で投稿プランを生成
# ═══════════════════════════════════════════════════

def generate_post_plan(catalog, genre, recycle=False, profile=None):
    """GPTで素材を仕分け → 投稿プランを生成"""
    print(f"\n🤖 投稿プランを生成中...")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("  ⚠️  OPENAI_API_KEY 未設定。フォールバックプランを生成します。")
        return generate_fallback_plan(catalog, genre)

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    # 素材サマリーを作成
    material_summary = []
    for c in catalog:
        if c.get("error"):
            continue
        material_summary.append({
            "filename": c["filename"],
            "duration": c["duration"],
            "has_audio": c["has_audio"],
            "is_vertical": c["is_vertical"],
            "transcript": c.get("transcript", "")[:200],  # 先頭200文字
        })

    # クライアントブランド情報をプロンプトに注入
    brand_instruction = ""
    if profile:
        brand = profile.get("brand", {})
        fixed_tags = profile.get("hashtags_fixed", [])
        ng_tags = profile.get("hashtags_ng", [])
        ng_words = profile.get("ng_words", [])
        brand_instruction = f"""

## クライアントブランド設定（必ず反映すること）:
- クライアント名: {profile.get('name', '')}
- ターゲット層: {profile.get('target_audience', '')}
- トーン・文体: {brand.get('tone', '')}
- テロップメイン色: {brand.get('telop_color_main', 'white')}
- テロップ強調色: {brand.get('telop_color_accent', 'yellow')}
- テロップCTA色: {brand.get('telop_color_cta', '#FFB6C1')}
- キャプションルール: {profile.get('caption_rules', '')}
- 毎回つける固定ハッシュタグ: {' '.join(fixed_tags) if fixed_tags else 'なし'}
- 使用禁止ハッシュタグ: {' '.join(ng_tags) if ng_tags else 'なし'}
- NG表現（使ってはいけない言葉）: {', '.join(ng_words) if ng_words else 'なし'}"""

    recycle_instruction = ""
    if recycle:
        recycle_instruction = """

## 素材リサイクル提案（recycle_ideas）:
同じ素材から別の切り口で作れる投稿アイデアも3つ提案してください。
例: ビフォーアフターで使った素材を「過程にフォーカス」「ASMR風」「お客様の声」等の別切り口で再利用
各アイデアに「どの素材を使うか」「どんな切り口か」「想定キャプション」を含めてください。"""

    prompt = f"""あなたはTikTok運営のプロディレクターです。

以下の素材一覧から、最適な投稿プランを作成してください。

## 素材一覧
{json.dumps(material_summary, ensure_ascii=False, indent=2)}

## ジャンル: {genre}
{brand_instruction}

## ルール

### 投稿プラン（posts）:
- 素材を投稿単位にグループ分けする
- 1投稿は15〜60秒に収まるように（TikTok最適尺）
- 各投稿に使う素材のファイル名と使用順序を指定
- 各素材の使用する時間範囲を指定（トリミング）（例: 0秒〜8秒）
- 各投稿にテロップを設計（冒頭フック + 要所 + CTA）
- テロップは15文字以内、色指定付き（白・黄色・ピンク等）
- 似た内容の素材は別投稿に分散させる（ネタ被り防止）

### 各投稿のキャプション:
- TikTok向け投稿文（150文字以内、共感を誘う文体）
- ハッシュタグ10〜15個（バズタグ + ニッチタグ混合）

### 投稿スケジュール（schedule）:
- 生成した投稿数に応じた最適な投稿スケジュール
- 曜日と時間帯を指定
- 理由を添える
{recycle_instruction}

## 出力（JSON厳守）:
{{
  "posts": [
    {{
      "post_number": 1,
      "title": "投稿のタイトル（内部管理用）",
      "concept": "この投稿のコンセプト（1文）",
      "total_duration": 30,
      "clips": [
        {{
          "filename": "素材ファイル名.mp4",
          "start": 0,
          "end": 8.5,
          "order": 1,
          "note": "この素材の使い方"
        }}
      ],
      "captions": [
        {{"start": 0, "end": 2.5, "text": "テロップ内容", "size": 60, "color": "white", "y": 0.57}},
        {{"start": 2.5, "end": 5, "text": "テロップ2", "size": 56, "color": "yellow", "y": 0.57}}
      ],
      "post_caption": "投稿キャプション文",
      "hashtags": ["#タグ1", "#タグ2"]
    }}
  ],
  "schedule": [
    {{"post_number": 1, "day": "月曜", "time": "19:00", "reason": "理由"}}
  ],
  "recycle_ideas": [
    {{
      "idea": "切り口の説明",
      "source_clips": ["使う素材ファイル名"],
      "caption_draft": "想定キャプション"
    }}
  ]
}}

JSONのみ出力。"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        plan = json.loads(response.choices[0].message.content)
        return plan
    except Exception as e:
        print(f"  ⚠️  GPTエラー: {e}")
        return generate_fallback_plan(catalog, genre)


def generate_fallback_plan(catalog, genre):
    """GPTが使えない場合のフォールバック"""
    valid = [c for c in catalog if not c.get("error")]
    posts = []
    clips_per_post = 3
    for i in range(0, len(valid), clips_per_post):
        group = valid[i:i+clips_per_post]
        total_dur = sum(c["duration"] for c in group)
        clips = []
        offset = 0
        for c in group:
            clips.append({
                "filename": c["filename"],
                "start": 0,
                "end": min(c["duration"], 20),
                "order": len(clips) + 1,
                "note": "",
            })
            offset += min(c["duration"], 20)
        posts.append({
            "post_number": len(posts) + 1,
            "title": f"投稿{len(posts)+1}",
            "concept": f"{genre}の動画",
            "total_duration": min(offset, 60),
            "clips": clips,
            "captions": [
                {"start": 0, "end": 2, "text": "見てほしい", "size": 60, "color": "white", "y": 0.57},
                {"start": offset - 3, "end": offset, "text": "フォローしてね", "size": 54, "color": "#FFB6C1", "y": 0.60},
            ],
            "post_caption": "",
            "hashtags": [],
        })
    return {"posts": posts, "schedule": [], "recycle_ideas": []}


# ═══════════════════════════════════════════════════
#  Step 3: 素材結合 + テロップ焼き込み
# ═══════════════════════════════════════════════════

def build_post_video(post, catalog, font, output_dir="output/tiktok"):
    """1投稿分の動画を結合 + テロップ焼き込み"""
    os.makedirs(output_dir, exist_ok=True)

    clips = sorted(post.get("clips", []), key=lambda c: c.get("order", 0))
    if not clips:
        return None

    # ファイル名 → パスのマッピング
    path_map = {c["filename"]: c["path"] for c in catalog}

    # 各クリップをトリミングして中間ファイルを作成
    tmp_dir = "output/.tmp"
    os.makedirs(tmp_dir, exist_ok=True)
    trimmed_files = []

    for i, clip in enumerate(clips):
        src = path_map.get(clip["filename"])
        if not src or not os.path.exists(src):
            print(f"    ⚠️  素材が見つかりません: {clip['filename']}")
            continue

        tmp_path = os.path.join(tmp_dir, f"clip_{post['post_number']}_{i:03d}.mp4")
        start = clip.get("start", 0)
        end = clip.get("end", 999)
        duration = end - start

        # 縦動画（1080x1920）にリサイズ + トリミング
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start), "-t", str(duration),
            "-i", src,
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-an",
            tmp_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            trimmed_files.append(tmp_path)
        else:
            print(f"    ⚠️  トリミング失敗: {clip['filename']}: {result.stderr[-150:]}")

    if not trimmed_files:
        return None

    # concat で結合
    concat_path = os.path.join(tmp_dir, f"concat_{post['post_number']}.txt")
    with open(concat_path, "w") as f:
        for tf in trimmed_files:
            f.write(f"file '{os.path.abspath(tf)}'\n")

    merged_path = os.path.join(tmp_dir, f"merged_{post['post_number']}.mp4")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        merged_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    ⚠️  結合失敗: {result.stderr[-150:]}")
        return None

    # テロップ焼き込み
    captions = post.get("captions", [])
    if captions:
        vf_parts = []
        for c in captions:
            color = c.get("color", "white")
            if color.startswith("#"):
                color = "0x" + color[1:]
            text_escaped = c["text"].replace("'", "\u2019").replace(":", "\\:")
            vf_parts.append(
                f"drawtext=text='{text_escaped}'"
                f":fontfile='{font}'"
                f":fontsize={c.get('size', 56)}"
                f":fontcolor={color}"
                f":borderw=4:bordercolor=black"
                f":x=(w-tw)/2:y=h*{c.get('y', 0.57)}"
                f":enable='between(t,{c['start']},{c['end']})'"
            )
        vf = ",".join(vf_parts)
    else:
        vf = "null"

    safe_title = f"post{post['post_number']:02d}"
    final_path = os.path.join(output_dir, f"{safe_title}.mp4")

    cmd = [
        "ffmpeg", "-y", "-i", merged_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart",
        final_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # 中間ファイル削除
    for tf in trimmed_files:
        try:
            os.remove(tf)
        except OSError:
            pass
    try:
        os.remove(concat_path)
        os.remove(merged_path)
    except OSError:
        pass

    if result.returncode != 0:
        print(f"    ⚠️  テロップ焼き込み失敗: {result.stderr[-150:]}")
        return None

    return final_path


# ═══════════════════════════════════════════════════
#  Step 4: レポート生成
# ═══════════════════════════════════════════════════

def generate_report(plan, catalog, outputs, genre, reports_dir="reports"):
    """投稿プラン全体のレポートを生成"""
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = f"{reports_dir}/plan_{today}.md"
    os.makedirs(reports_dir, exist_ok=True)

    lines = [
        f"# 投稿プラン {today}",
        f"",
        f"**ジャンル**: {genre}  ",
        f"**素材数**: {len(catalog)}個  ",
        f"**投稿数**: {len(plan.get('posts', []))}本  ",
        f"",
        f"---",
    ]

    # 各投稿の詳細
    for post in plan.get("posts", []):
        pn = post["post_number"]
        output = outputs.get(pn, "")

        lines += [
            f"",
            f"## 投稿 {pn}: {post.get('title', '')}",
            f"",
            f"**コンセプト**: {post.get('concept', '')}  ",
            f"**尺**: {post.get('total_duration', 0)}秒  ",
        ]

        if output:
            lines.append(f"**ファイル**: `{output}`  ")

        # 使用素材
        lines += [f"", f"### 使用素材"]
        for clip in post.get("clips", []):
            lines.append(f"- {clip['filename']}（{clip.get('start', 0)}s〜{clip.get('end', 0)}s） {clip.get('note', '')}")

        # テロップ
        if post.get("captions"):
            lines += [f"", f"### テロップ", f"", f"| 時間 | テロップ | 色 |", f"|------|---------|-----|"]
            for c in post["captions"]:
                lines.append(f"| {c['start']}s〜{c['end']}s | {c['text']} | {c.get('color', 'white')} |")

        # キャプション（コピペ用）
        if post.get("post_caption"):
            lines += [f"", f"### キャプション（コピペ用）", f"", f"```", f"{post['post_caption']}", f"```"]

        # ハッシュタグ（コピペ用）
        if post.get("hashtags"):
            lines += [f"", f"### ハッシュタグ（コピペ用）", f"", f"```", f"{' '.join(post['hashtags'])}", f"```"]

        lines.append(f"")
        lines.append(f"---")

    # 投稿スケジュール
    if plan.get("schedule"):
        lines += [f"", f"## 投稿スケジュール", f""]
        for s in plan["schedule"]:
            lines.append(f"- **投稿{s.get('post_number', '?')}**: {s.get('day', '')} {s.get('time', '')} — {s.get('reason', '')}")

    # リサイクルアイデア
    if plan.get("recycle_ideas"):
        lines += [
            f"",
            f"---",
            f"",
            f"## 素材リサイクルアイデア（同じ素材から別投稿を作る）",
            f"",
        ]
        for i, idea in enumerate(plan["recycle_ideas"], 1):
            lines.append(f"### アイデア {i}")
            lines.append(f"")
            lines.append(f"**切り口**: {idea.get('idea', '')}")
            if idea.get("source_clips"):
                lines.append(f"**使う素材**: {', '.join(idea['source_clips'])}")
            if idea.get("caption_draft"):
                lines.append(f"**キャプション案**: {idea['caption_draft']}")
            lines.append(f"")

    report = "\n".join(lines) + "\n"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    return report_path


# ═══════════════════════════════════════════════════
#  Step 5: プランJSONの保存（修正して再実行用）
# ═══════════════════════════════════════════════════

def save_plan_json(plan, catalog, reports_dir="reports"):
    """プランをJSONで保存。手動で順序変更・テロップ修正して再実行可能"""
    today = datetime.now().strftime("%Y-%m-%d")
    plan_path = f"{reports_dir}/plan_{today}.json"
    os.makedirs(reports_dir, exist_ok=True)

    output = {
        "generated_at": datetime.now().isoformat(),
        "catalog": [
            {"filename": c["filename"], "path": c["path"], "duration": c["duration"]}
            for c in catalog if not c.get("error")
        ],
        "plan": plan,
    }

    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return plan_path


# ═══════════════════════════════════════════════════
#  メイン
# ═══════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="投稿プランナー - 大量素材 → 仕分け → 結合 → キャプション → 投稿プラン",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--genre", default="beauty",
                        choices=["beauty", "food", "travel", "fitness", "business", "lifestyle", "education", "product"],
                        help="ジャンル（デフォルト: beauty）")
    parser.add_argument("--input-dir", default="input", help="素材フォルダ（デフォルト: input/）")
    parser.add_argument("--client", help="クライアントID（clients/{id}/ のフォルダを使用）")
    parser.add_argument("--dry-run", action="store_true", help="プラン確認のみ（動画生成しない）")
    parser.add_argument("--recycle", action="store_true", help="素材リサイクル提案も生成")
    parser.add_argument("--plan-json", help="既存のプランJSONから動画を生成（プラン修正後の再実行用）")
    args = parser.parse_args()

    # クライアントモード: パスとプロフィールを自動設定
    client_profile = None
    if args.client:
        client_dir = os.path.join("clients", args.client)
        profile_path = os.path.join(client_dir, "profile.json")
        if os.path.exists(profile_path):
            with open(profile_path, encoding="utf-8") as f:
                client_profile = json.load(f)
            args.input_dir = os.path.join(client_dir, "input")
            args.genre = client_profile.get("genre", args.genre)
        else:
            print(f"  ⚠️  クライアント {args.client} のプロフィールが見つかりません。")
            print(f"  python ops.py でクライアントを登録してください。")
            sys.exit(1)

    print("=" * 55)
    print("  Video AIops - 投稿プランナー")
    if client_profile:
        print(f"  クライアント: {client_profile.get('name', args.client)}")
    print("=" * 55)

    # 既存プランからの再実行
    if args.plan_json:
        print(f"\n  既存プラン読み込み: {args.plan_json}")
        with open(args.plan_json, encoding="utf-8") as f:
            data = json.load(f)
        catalog = data["catalog"]
        plan = data["plan"]
    else:
        # 素材検出
        videos = find_videos(args.input_dir)
        if not videos:
            print(f"\n  ❌ {args.input_dir}/ に動画が見つかりません。")
            print(f"  素材を {args.input_dir}/ に入れてから再実行してください。")
            sys.exit(0)

        print(f"\n  素材: {len(videos)}個")
        print(f"  ジャンル: {args.genre}")

        # Step 1: 全素材解析
        catalog = analyze_all(videos)
        valid = [c for c in catalog if not c.get("error")]
        print(f"\n  → 有効な素材: {len(valid)}個")
        total_duration = sum(c["duration"] for c in valid)
        print(f"  → 合計尺: {total_duration:.0f}秒（{total_duration/60:.1f}分）")

        if not valid:
            print("  ❌ 有効な素材がありません。")
            sys.exit(1)

        # Step 2: 投稿プラン生成
        plan = generate_post_plan(catalog, args.genre, recycle=args.recycle, profile=client_profile)

    posts = plan.get("posts", [])
    print(f"\n  → {len(posts)}本の投稿プランを生成")

    # プラン表示
    print("\n" + "─" * 55)
    for post in posts:
        pn = post["post_number"]
        clip_names = [c["filename"] for c in post.get("clips", [])]
        print(f"  投稿{pn}: {post.get('title', '')}")
        print(f"    素材: {', '.join(clip_names)}")
        print(f"    尺: {post.get('total_duration', '?')}秒")
        print(f"    コンセプト: {post.get('concept', '')}")
        if post.get("captions"):
            hook = post["captions"][0]["text"] if post["captions"] else ""
            print(f"    冒頭テロップ: 「{hook}」")
        print()
    print("─" * 55)

    # クライアント別ディレクトリ
    if args.client:
        output_dir = os.path.join("clients", args.client, "output")
        reports_dir = os.path.join("clients", args.client, "reports")
    else:
        output_dir = "output/tiktok"
        reports_dir = "reports"

    # プランJSON保存
    plan_json_path = save_plan_json(plan, catalog, reports_dir)
    print(f"\n  📋 プランJSON保存: {plan_json_path}")
    print(f"     → 順序変更やテロップ修正後、--plan-json で再実行可能")

    # dry-run ならここまで
    if args.dry_run:
        report_path = generate_report(plan, catalog, {}, args.genre, reports_dir)
        print(f"  📊 レポート: {report_path}")
        print(f"\n  （--dry-run のため動画生成はスキップ）")
        print(f"  動画を生成するには:")
        print(f"    python scripts/planner.py --genre {args.genre}")
        print(f"  プランを修正して再実行:")
        print(f"    python scripts/planner.py --plan-json {plan_json_path}")
        return

    # Step 3: 動画生成
    print("\n🎬 動画を生成中...")
    font = get_font()
    outputs = {}

    for post in posts:
        pn = post["post_number"]
        print(f"\n  投稿{pn}: {post.get('title', '')}")
        result = build_post_video(post, catalog, font, output_dir)
        if result:
            outputs[pn] = result
            print(f"    ✅ {result}")
        else:
            print(f"    ❌ 生成失敗")

    # Step 4: レポート生成
    report_path = generate_report(plan, catalog, outputs, args.genre, reports_dir)

    # 完了サマリー
    print("\n" + "=" * 55)
    print("  ✅ 完了!")
    print("=" * 55)

    print(f"\n  📦 生成した動画: {len(outputs)}本")
    for pn, path in outputs.items():
        post = next((p for p in posts if p["post_number"] == pn), {})
        print(f"     投稿{pn}: {path}")

    if plan.get("schedule"):
        print(f"\n  📅 投稿スケジュール:")
        for s in plan["schedule"]:
            print(f"     投稿{s.get('post_number','?')}: {s.get('day','')} {s.get('time','')} — {s.get('reason','')}")

    if plan.get("recycle_ideas"):
        print(f"\n  ♻️  リサイクルアイデア: {len(plan['recycle_ideas'])}件")
        for idea in plan["recycle_ideas"]:
            print(f"     - {idea.get('idea', '')}")

    print(f"\n  📊 レポート: {report_path}")
    print(f"  📋 プランJSON: {plan_json_path}")
    print(f"")
    print(f"  次にやること:")
    print(f"  1. output/tiktok/ の動画をスマホに送る")
    print(f"  2. レポートからキャプション・ハッシュタグをコピー")
    print(f"  3. TikTokスタジオで予約投稿!")
    print(f"  4. BGMはTikTokアプリ内で追加")
    if plan.get("recycle_ideas"):
        print(f"  5. リサイクルアイデアで次の投稿も準備!")
    print()


if __name__ == "__main__":
    main()
