#!/usr/bin/env python3
"""
フック最適化 - 冒頭2秒の離脱を防ぐ

TikTokの分析データから、視聴者は冒頭2秒で離脱判断する。
このスクリプトは素材動画から最もインパクトのあるシーンを検出し、
冒頭に配置 + フックテロップ3パターンを自動生成する。

使い方:
  python scripts/hook_optimizer.py input/video.mp4
  python scripts/hook_optimizer.py input/video.mp4 --genre beauty --theme "眉アート"
  python scripts/hook_optimizer.py input/video.mp4 --client shimon_brushup --max-duration 20
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

FONT_MAC = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
FONT_LINUX = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"


def get_font():
    if os.path.exists(FONT_MAC):
        return FONT_MAC
    if os.path.exists(FONT_LINUX):
        return FONT_LINUX
    return "sans"


# ═══════════════════════════════════════════════
#  Step 1: 動画解析 + シーン検出
# ═══════════════════════════════════════════════

def analyze_video(path):
    """ffprobe でメタデータ取得"""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    info = json.loads(result.stdout)
    vs = next((s for s in info.get("streams", []) if s["codec_type"] == "video"), None)
    duration = float(info.get("format", {}).get("duration", 0))
    return {
        "duration": round(duration, 2),
        "width": int(vs["width"]) if vs else 1080,
        "height": int(vs["height"]) if vs else 1920,
    }


def detect_scenes(path):
    """ffmpeg のシーンチェンジ検出で映像の切り替わり点を取得"""
    cmd = [
        "ffmpeg", "-i", path,
        "-vf", "select='gt(scene,0.3)',showinfo",
        "-vsync", "vfr",
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    scenes = []
    for line in result.stderr.split("\n"):
        if "pts_time:" in line:
            try:
                pts = float(line.split("pts_time:")[1].split()[0])
                scenes.append(pts)
            except (ValueError, IndexError):
                pass

    return sorted(set(scenes))


def detect_high_motion_frames(path, duration):
    """動きが大きいフレーム（＝視覚的にインパクトがある）を検出"""
    cmd = [
        "ffmpeg", "-i", path,
        "-vf", "select='gt(scene,0.15)',metadata=print:file=-",
        "-vsync", "vfr",
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    frames = []
    current_time = None
    current_score = None

    for line in result.stderr.split("\n"):
        if "pts_time:" in line:
            try:
                current_time = float(line.split("pts_time:")[1].split()[0])
            except (ValueError, IndexError):
                pass
        if "lavfi.scene_score=" in line:
            try:
                current_score = float(line.split("lavfi.scene_score=")[1].strip())
            except (ValueError, IndexError):
                pass

        if current_time is not None and current_score is not None:
            frames.append({"time": current_time, "score": current_score})
            current_time = None
            current_score = None

    # スコアが取れなかった場合、シーンチェンジのタイムスタンプだけ使う
    if not frames:
        scenes = detect_scenes(path)
        frames = [{"time": t, "score": 0.5} for t in scenes]

    # さらにフォールバック: 均等に5点サンプリング
    if not frames:
        step = max(duration / 6, 1)
        frames = [{"time": step * i, "score": 0.3} for i in range(1, 6)]

    return sorted(frames, key=lambda f: -f["score"])


def find_best_hook_moment(path, duration):
    """最もインパクトのあるシーン（＝フックに使うべき瞬間）を検出"""
    print("  🔍 インパクトのあるシーンを検出中...")

    high_frames = detect_high_motion_frames(path, duration)

    if high_frames:
        best = high_frames[0]
        print(f"    → ベストシーン: {best['time']:.1f}秒 (スコア: {best.get('score', '?')})")
        return best["time"]

    # フォールバック: 動画の30%地点
    fallback = duration * 0.3
    print(f"    → フォールバック: {fallback:.1f}秒")
    return fallback


# ═══════════════════════════════════════════════
#  Step 2: 文字起こし
# ═══════════════════════════════════════════════

def transcribe(path):
    """Whisper で文字起こし"""
    try:
        import whisper
        model = whisper.load_model(os.environ.get("WHISPER_MODEL", "medium"))
        result = model.transcribe(path, language="ja", word_timestamps=True, verbose=False)
        return result.get("text", "")
    except ImportError:
        pass

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return ""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        with open(path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-1", file=f, language="ja")
        return result.text
    except Exception:
        return ""


# ═══════════════════════════════════════════════
#  Step 3: GPT でフックテロップ3パターン生成
# ═══════════════════════════════════════════════

def generate_hooks(transcript, theme, genre, profile=None):
    """GPTで冒頭フックテロップを3パターン生成"""
    print("  🤖 フックテロップを3パターン生成中...")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return generate_hooks_fallback(theme)

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    brand_context = ""
    if profile:
        brand = profile.get("brand", {})
        brand_context = f"""
ブランド情報:
- ターゲット: {profile.get('target_audience', '')}
- トーン: {brand.get('tone', '')}
- NG表現: {', '.join(profile.get('ng_words', []))}"""

    prompt = f"""TikTok動画の冒頭フックテロップを3パターン作って。

テーマ: {theme or '(テーマなし)'}
ジャンル: {genre}
動画の内容: {transcript[:300] if transcript else '(音声なし)'}
{brand_context}

## ルール
- 冒頭0〜2秒に表示する一言
- 視聴者が「え？」となって離脱しない表現
- 10文字以内。短いほど強い
- 3パターンそれぞれ異なるアプローチ:
  A) 結果先出し型（「○○だけでこうなった」）
  B) 疑問・煽り型（「これ知ってた？」「○○してる？」）
  C) 共感型（「○○で悩んでる人見て」）

## 出力（JSON厳守）:
{{
  "hooks": [
    {{
      "type": "A_result",
      "text": "テロップ文（10文字以内）",
      "color": "white",
      "why": "なぜこれが効くか（1文）"
    }},
    {{
      "type": "B_question",
      "text": "テロップ文",
      "color": "yellow",
      "why": "理由"
    }},
    {{
      "type": "C_empathy",
      "text": "テロップ文",
      "color": "white",
      "why": "理由"
    }}
  ]
}}
JSONのみ出力。"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        return result.get("hooks", generate_hooks_fallback(theme))
    except Exception as e:
        print(f"    ⚠️  GPTエラー: {e}")
        return generate_hooks_fallback(theme)


def generate_hooks_fallback(theme):
    t = theme or "これ見て"
    return [
        {"type": "A_result", "text": t[:10], "color": "white", "why": ""},
        {"type": "B_question", "text": "知ってた？", "color": "yellow", "why": ""},
        {"type": "C_empathy", "text": "悩んでる人見て", "color": "white", "why": ""},
    ]


# ═══════════════════════════════════════════════
#  Step 4: 動画を再構成（フック→本編→CTA）
# ═══════════════════════════════════════════════

def build_optimized_video(path, hook_time, hook_text, hook_color, video_info, max_duration, font, output_path, cta_text="フォローで見届けて"):
    """フックシーンを冒頭に持ってきて、テロップ付きで書き出し"""

    duration = min(video_info["duration"], max_duration)

    # フックの切り出し範囲（前後1.5秒）
    hook_start = max(0, hook_time - 1.5)
    hook_end = min(video_info["duration"], hook_time + 1.5)
    hook_dur = hook_end - hook_start

    # 残りの本編（フック部分を除いた冒頭から）
    body_dur = duration - hook_dur - 3  # CTA分の3秒を引く
    if body_dur < 5:
        body_dur = duration - hook_dur

    # 中間ファイル
    tmp_dir = os.path.dirname(output_path) or "."
    tmp_hook = os.path.join(tmp_dir, "_tmp_hook.mp4")
    tmp_body = os.path.join(tmp_dir, "_tmp_body.mp4")
    tmp_cta = os.path.join(tmp_dir, "_tmp_cta.mp4")
    tmp_list = os.path.join(tmp_dir, "_tmp_list.txt")

    # 1. フック部分を切り出し
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(hook_start), "-t", str(hook_dur),
        "-i", path, "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", "30", "-an", tmp_hook
    ], capture_output=True)

    # 2. 本編部分（冒頭から）
    body_start = 0 if hook_start > 3 else hook_end
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(body_start), "-t", str(body_dur),
        "-i", path, "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", "30", "-an", tmp_body
    ], capture_output=True)

    # 3. CTA部分（最後の3秒をループ or 最後のフレームを伸ばす）
    cta_start = max(0, video_info["duration"] - 3)
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(cta_start), "-t", "3",
        "-i", path, "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", "30", "-an", tmp_cta
    ], capture_output=True)

    # 4. concat
    parts = [tmp_hook, tmp_body]
    if os.path.exists(tmp_cta) and body_dur > 5:
        parts.append(tmp_cta)

    with open(tmp_list, "w") as f:
        for p in parts:
            f.write(f"file '{os.path.abspath(p)}'\n")

    tmp_merged = os.path.join(tmp_dir, "_tmp_merged.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", tmp_list,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", tmp_merged
    ], capture_output=True)

    # 5. テロップ焼き込み
    merged_info = analyze_video(tmp_merged)
    final_dur = merged_info["duration"]

    color = hook_color
    if color.startswith("#"):
        color = "0x" + color[1:]

    text_escaped = hook_text.replace("'", "’").replace(":", "\\:")
    cta_escaped = cta_text.replace("'", "’").replace(":", "\\:")

    vf = (
        f"drawtext=text='{text_escaped}'"
        f":fontfile='{font}':fontsize=68:fontcolor={color}"
        f":borderw=5:bordercolor=black"
        f":x=(w-tw)/2:y=h*0.45"
        f":enable='between(t,0,2.5)',"
        f"drawtext=text='{cta_escaped}'"
        f":fontfile='{font}':fontsize=52:fontcolor=0xFFB6C1"
        f":borderw=4:bordercolor=black"
        f":x=(w-tw)/2:y=h*0.57"
        f":enable='between(t,{final_dur - 3},{final_dur})'"
    )

    result = subprocess.run([
        "ffmpeg", "-y", "-i", tmp_merged,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart",
        output_path
    ], capture_output=True, text=True)

    # クリーンアップ
    for tmp in [tmp_hook, tmp_body, tmp_cta, tmp_list, tmp_merged]:
        try:
            os.remove(tmp)
        except OSError:
            pass

    return result.returncode == 0


# ═══════════════════════════════════════════════
#  メイン
# ═══════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="フック最適化 - 冒頭2秒の離脱を防ぐ動画を自動生成",
    )
    parser.add_argument("input", help="入力動画ファイル")
    parser.add_argument("--theme", default="", help="動画のテーマ")
    parser.add_argument("--genre", default="beauty", help="ジャンル")
    parser.add_argument("--client", help="クライアントID")
    parser.add_argument("--max-duration", type=int, default=20, help="最大尺（秒）デフォルト20")
    parser.add_argument("--cta", default="フォローで見届けて", help="CTA文言")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ ファイルが見つかりません: {args.input}")
        sys.exit(1)

    print("=" * 55)
    print("  Video AIops - フック最適化")
    print("=" * 55)

    # クライアントプロフィール
    profile = None
    if args.client:
        profile_path = os.path.join("clients", args.client, "profile.json")
        if os.path.exists(profile_path):
            with open(profile_path, encoding="utf-8") as f:
                profile = json.load(f)
            print(f"  クライアント: {profile.get('name', args.client)}")

    # Step 1: 動画解析
    print(f"\n  入力: {args.input}")
    video_info = analyze_video(args.input)
    print(f"  尺: {video_info['duration']}秒 → {args.max_duration}秒に短縮")

    # フック検出
    hook_time = find_best_hook_moment(args.input, video_info["duration"])

    # Step 2: 文字起こし
    print("  📝 文字起こし中...")
    transcript = transcribe(args.input)
    if transcript:
        print(f"    → {len(transcript)}文字")

    # Step 3: フックテロップ3パターン
    hooks = generate_hooks(transcript, args.theme, args.genre, profile)

    # Step 4: 3バージョン書き出し
    print(f"\n🎬 3バージョンを書き出し中...")
    font = get_font()

    if args.client:
        output_dir = os.path.join("clients", args.client, "output")
    else:
        output_dir = "output/tiktok"
    os.makedirs(output_dir, exist_ok=True)

    basename = os.path.splitext(os.path.basename(args.input))[0]
    outputs = []

    for i, hook in enumerate(hooks[:3]):
        label = hook.get("type", f"v{i+1}")
        output_path = os.path.join(output_dir, f"{basename}_hook_{label}.mp4")
        print(f"\n  [{label}] 「{hook['text']}」")
        print(f"    理由: {hook.get('why', '')}")

        success = build_optimized_video(
            args.input, hook_time, hook["text"], hook.get("color", "white"),
            video_info, args.max_duration, font, output_path, args.cta
        )

        if success:
            out_info = analyze_video(output_path)
            print(f"    ✅ {output_path} ({out_info['duration']}秒)")
            outputs.append({"path": output_path, "hook": hook, "duration": out_info["duration"]})
        else:
            print(f"    ❌ 生成失敗")

    # 結果サマリー
    print(f"\n{'=' * 55}")
    print(f"  ✅ {len(outputs)}バージョン生成完了!")
    print(f"{'=' * 55}")

    print(f"\n  A/Bテストの進め方:")
    print(f"  1. 3本を別々の時間帯に投稿")
    print(f"  2. 24時間後に再生数・フル視聴率を比較")
    print(f"  3. 最も数字が良い型を特定")
    print(f"  4. 次の投稿からその型を使う")

    for out in outputs:
        h = out["hook"]
        print(f"\n  [{h['type']}] 「{h['text']}」")
        print(f"    → {out['path']}")

    # レポート保存
    if args.client:
        report_dir = os.path.join("clients", args.client, "reports")
    else:
        report_dir = "reports"
    os.makedirs(report_dir, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    report = {
        "date": today,
        "input": args.input,
        "hook_time": hook_time,
        "max_duration": args.max_duration,
        "hooks": hooks[:3],
        "outputs": [{"path": o["path"], "type": o["hook"]["type"]} for o in outputs],
    }
    report_path = os.path.join(report_dir, f"hook_test_{today}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n  📊 テスト結果はここに記録: {report_path}")
    print()


if __name__ == "__main__":
    main()
