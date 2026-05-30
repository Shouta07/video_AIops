#!/usr/bin/env python3
"""
His Recoveries リール自動編集エンジン

仮説に基づいてリール動画を自動生成。
顔出しなし。テキストカード + BGM + トランジションで構成。

使い方:
  # 一言カード型
  python instagram/reel_editor.py --type card --text "清潔感は、手入れしてるかどうか。"

  # 3段階スライド型
  python instagram/reel_editor.py --type slide --texts "昔は気にしてなかった" "ある日鏡を見て気づいた" "ただ、まだ間に合う"

  # 問いかけ型
  python instagram/reel_editor.py --type question --text "一番長く悩んだのはどれ？" --options "肌荒れ" "体臭" "清潔感" "自信"

  # スクリプトJSONから自動生成
  python instagram/reel_editor.py --script script.json

  # BGM付き
  python instagram/reel_editor.py --type card --text "整えるのは、体調から。" --bgm instagram/assets/bgm/lofi01.mp3
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow が必要です: pip install Pillow")
    sys.exit(1)

# ── ビジュアルガイドライン ──

BRAND = {
    "width": 1080,
    "height": 1920,
    "bg_color": (245, 240, 235),       # #F5F0EB 暖色ベージュ
    "text_color": (44, 44, 44),         # #2C2C2C ダークグレー
    "accent_color": (139, 115, 85),     # #8B7355 ウォームブラウン
    "sub_color": (160, 140, 120),       # サブテキスト
    "font_size_main": 64,
    "font_size_sub": 36,
    "font_size_small": 28,
    "line_spacing": 1.6,
}

FONT_PATHS = [
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "instagram/assets/fonts/NotoSansJP-Medium.ttf",
]

OUTPUT_DIR = "instagram/output"


def find_font(bold=False):
    """利用可能なフォントを検索"""
    preferred = [1, 3] if bold else [0, 2, 4]
    for idx in preferred:
        if idx < len(FONT_PATHS) and os.path.exists(FONT_PATHS[idx]):
            return FONT_PATHS[idx]
    for p in FONT_PATHS:
        if os.path.exists(p):
            return p
    return None


def load_font(size, bold=False):
    """フォントをロード"""
    path = find_font(bold)
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


# ═══════════════════════════════════════════════
#  テキストカード画像生成（Pillow）
# ═══════════════════════════════════════════════

def create_text_card(text, subtitle="", bg_color=None, text_color=None, accent_color=None):
    """Aesop/Kinfolk的な静かなテキストカードを生成"""
    w, h = BRAND["width"], BRAND["height"]
    bg = bg_color or BRAND["bg_color"]
    tc = text_color or BRAND["text_color"]
    ac = accent_color or BRAND["accent_color"]

    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)

    # メインテキスト（中央配置）
    font_main = load_font(BRAND["font_size_main"])
    font_sub = load_font(BRAND["font_size_sub"])
    font_brand = load_font(BRAND["font_size_small"])

    # テキストを改行処理
    lines = wrap_text(text, font_main, w - 160)
    total_text_height = sum(font_main.getbbox(line)[3] - font_main.getbbox(line)[1] for line in lines)
    total_text_height += (len(lines) - 1) * int(BRAND["font_size_main"] * 0.5)

    # 描画開始位置（中央やや上）
    y_start = (h - total_text_height) // 2 - 50

    for line in lines:
        bbox = font_main.getbbox(line)
        tw = bbox[2] - bbox[0]
        x = (w - tw) // 2
        draw.text((x, y_start), line, font=font_main, fill=tc)
        y_start += (bbox[3] - bbox[1]) + int(BRAND["font_size_main"] * 0.5)

    # サブテキスト
    if subtitle:
        sub_bbox = font_sub.getbbox(subtitle)
        sub_w = sub_bbox[2] - sub_bbox[0]
        draw.text(
            ((w - sub_w) // 2, y_start + 40),
            subtitle, font=font_sub, fill=BRAND["sub_color"]
        )

    # ブランドマーク（下部）
    brand_text = "His Recoveries"
    brand_bbox = font_brand.getbbox(brand_text)
    brand_w = brand_bbox[2] - brand_bbox[0]
    draw.text(
        ((w - brand_w) // 2, h - 120),
        brand_text, font=font_brand, fill=ac
    )

    # 上下のアクセントライン
    line_y_top = 180
    line_y_bottom = h - 180
    line_margin = 200
    draw.line([(line_margin, line_y_top), (w - line_margin, line_y_top)], fill=ac, width=1)
    draw.line([(line_margin, line_y_bottom), (w - line_margin, line_y_bottom)], fill=ac, width=1)

    return img


def wrap_text(text, font, max_width):
    """テキストを指定幅で折り返し"""
    lines = []
    current = ""
    for char in text:
        test = current + char
        bbox = font.getbbox(test)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines


# ═══════════════════════════════════════════════
#  リール動画生成（FFmpeg）
# ═══════════════════════════════════════════════

def create_card_reel(text, subtitle="", duration=8, bgm_path=None, output_name=None):
    """一言カード型リール：テキスト1枚 + フェードイン/アウト + BGM"""
    print(f"  🎬 一言カード型リール生成中...")
    print(f"    テキスト: 「{text}」")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_name = output_name or f"reel_card_{timestamp}.mp4"
    output_path = os.path.join(OUTPUT_DIR, output_name)

    # 1. テキストカード画像を生成
    card = create_text_card(text, subtitle)
    tmp_img = os.path.join(OUTPUT_DIR, f"_tmp_card_{timestamp}.png")
    card.save(tmp_img)

    # 2. 画像→動画変換（フェードイン/アウト付き）
    fade_in = 0.8
    fade_out = 0.8

    vf = (
        f"loop={duration * 30}:size=1:start=0,"
        f"fps=30,"
        f"fade=t=in:st=0:d={fade_in},"
        f"fade=t=out:st={duration - fade_out}:d={fade_out},"
        f"scale=1080:1920"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", tmp_img,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-t", str(duration),
    ]

    # BGM合成
    if bgm_path and os.path.exists(bgm_path):
        cmd += ["-i", bgm_path, "-c:a", "aac", "-b:a", "192k", "-shortest"]
    else:
        cmd += ["-an"]

    cmd += ["-movflags", "+faststart", output_path]

    result = subprocess.run(cmd, capture_output=True, text=True)

    # クリーンアップ
    try:
        os.remove(tmp_img)
    except OSError:
        pass

    if result.returncode == 0:
        print(f"    ✅ {output_path}")
        return output_path
    else:
        print(f"    ❌ 生成失敗: {result.stderr[-200:]}")
        return None


def create_slide_reel(texts, duration_per_slide=5, bgm_path=None, output_name=None):
    """3段階スライド型リール：複数テキストカードをトランジション付きで結合"""
    print(f"  🎬 スライド型リール生成中... ({len(texts)}枚)")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_name = output_name or f"reel_slide_{timestamp}.mp4"
    output_path = os.path.join(OUTPUT_DIR, output_name)

    # 各スライドの色を段階的に変える
    colors = [
        (BRAND["bg_color"], BRAND["text_color"]),       # ベージュ背景
        (BRAND["bg_color"], BRAND["accent_color"]),     # ブラウンテキスト
        ((44, 44, 44), (245, 240, 235)),                # ダーク背景・ライトテキスト
    ]

    # 各スライドを動画化
    slide_paths = []
    for i, text in enumerate(texts):
        bg, tc = colors[i % len(colors)]
        card = create_text_card(text, bg_color=bg, text_color=tc)
        tmp_img = os.path.join(OUTPUT_DIR, f"_tmp_slide_{timestamp}_{i}.png")
        card.save(tmp_img)

        tmp_vid = os.path.join(OUTPUT_DIR, f"_tmp_slide_{timestamp}_{i}.mp4")
        fade_in = 0.6
        fade_out = 0.6

        vf = (
            f"loop={duration_per_slide * 30}:size=1:start=0,"
            f"fps=30,"
            f"fade=t=in:st=0:d={fade_in},"
            f"fade=t=out:st={duration_per_slide - fade_out}:d={fade_out},"
            f"scale=1080:1920"
        )

        subprocess.run([
            "ffmpeg", "-y", "-i", tmp_img,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-t", str(duration_per_slide),
            "-an", tmp_vid
        ], capture_output=True)

        slide_paths.append(tmp_vid)
        os.remove(tmp_img)

    # 結合
    concat_file = os.path.join(OUTPUT_DIR, f"_tmp_concat_{timestamp}.txt")
    with open(concat_file, "w") as f:
        for p in slide_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
    ]

    if bgm_path and os.path.exists(bgm_path):
        cmd += ["-i", bgm_path, "-c:a", "aac", "-b:a", "192k", "-shortest"]
    else:
        cmd += ["-an"]

    cmd += ["-movflags", "+faststart", output_path]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # クリーンアップ
    for p in slide_paths:
        try:
            os.remove(p)
        except OSError:
            pass
    try:
        os.remove(concat_file)
    except OSError:
        pass

    if result.returncode == 0:
        total_dur = duration_per_slide * len(texts)
        print(f"    ✅ {output_path} ({total_dur}秒)")
        return output_path
    else:
        print(f"    ❌ 生成失敗: {result.stderr[-200:]}")
        return None


def create_question_reel(question, options, duration=10, bgm_path=None, output_name=None):
    """問いかけ型リール：質問 + 選択肢"""
    print(f"  🎬 問いかけ型リール生成中...")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_name = output_name or f"reel_question_{timestamp}.mp4"
    output_path = os.path.join(OUTPUT_DIR, output_name)

    w, h = BRAND["width"], BRAND["height"]
    img = Image.new("RGB", (w, h), BRAND["bg_color"])
    draw = ImageDraw.Draw(img)

    font_q = load_font(56, bold=True)
    font_opt = load_font(40)
    font_brand = load_font(BRAND["font_size_small"])

    # 質問テキスト
    q_lines = wrap_text(question, font_q, w - 160)
    y = 500
    for line in q_lines:
        bbox = font_q.getbbox(line)
        tw = bbox[2] - bbox[0]
        draw.text(((w - tw) // 2, y), line, font=font_q, fill=BRAND["text_color"])
        y += (bbox[3] - bbox[1]) + 20

    y += 60

    # 選択肢
    for i, opt in enumerate(options):
        # 選択肢ボックス
        box_w = w - 200
        box_h = 80
        box_x = 100
        box_y = y

        # 角丸風ボックス
        draw.rounded_rectangle(
            [(box_x, box_y), (box_x + box_w, box_y + box_h)],
            radius=15,
            fill=(255, 255, 255),
            outline=BRAND["accent_color"],
            width=2
        )

        bbox = font_opt.getbbox(opt)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(
            ((w - tw) // 2, box_y + (box_h - th) // 2),
            opt, font=font_opt, fill=BRAND["text_color"]
        )
        y += box_h + 20

    # ブランドマーク
    brand_text = "His Recoveries"
    brand_bbox = font_brand.getbbox(brand_text)
    brand_w = brand_bbox[2] - brand_bbox[0]
    draw.text(((w - brand_w) // 2, h - 120), brand_text, font=font_brand, fill=BRAND["accent_color"])

    tmp_img = os.path.join(OUTPUT_DIR, f"_tmp_q_{timestamp}.png")
    img.save(tmp_img)

    # 動画化
    vf = (
        f"loop={duration * 30}:size=1:start=0,"
        f"fps=30,"
        f"fade=t=in:st=0:d=0.8,"
        f"fade=t=out:st={duration - 0.8}:d=0.8,"
        f"scale=1080:1920"
    )

    cmd = [
        "ffmpeg", "-y", "-i", tmp_img,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-t", str(duration),
    ]

    if bgm_path and os.path.exists(bgm_path):
        cmd += ["-i", bgm_path, "-c:a", "aac", "-b:a", "192k", "-shortest"]
    else:
        cmd += ["-an"]

    cmd += ["-movflags", "+faststart", output_path]
    result = subprocess.run(cmd, capture_output=True, text=True)

    try:
        os.remove(tmp_img)
    except OSError:
        pass

    if result.returncode == 0:
        print(f"    ✅ {output_path}")
        return output_path
    else:
        print(f"    ❌ 生成失敗")
        return None


# ═══════════════════════════════════════════════
#  スクリプトJSONからの自動生成
# ═══════════════════════════════════════════════

def create_from_script(script_path, bgm_path=None):
    """スクリプトJSONから自動生成"""
    with open(script_path, encoding="utf-8") as f:
        script = json.load(f)

    reel_type = script.get("type", "card")
    output_name = script.get("output_name")
    bgm = bgm_path or script.get("bgm")

    if reel_type == "card":
        return create_card_reel(
            script["text"],
            subtitle=script.get("subtitle", ""),
            duration=script.get("duration", 8),
            bgm_path=bgm,
            output_name=output_name,
        )
    elif reel_type == "slide":
        return create_slide_reel(
            script["texts"],
            duration_per_slide=script.get("duration_per_slide", 5),
            bgm_path=bgm,
            output_name=output_name,
        )
    elif reel_type == "question":
        return create_question_reel(
            script["question"],
            script["options"],
            duration=script.get("duration", 10),
            bgm_path=bgm,
            output_name=output_name,
        )
    else:
        print(f"  ❌ 未対応のリール型: {reel_type}")
        return None


# ═══════════════════════════════════════════════
#  メイン
# ═══════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="His Recoveries リール自動編集エンジン",
    )
    parser.add_argument("--type", choices=["card", "slide", "question"],
                        help="リール型（card/slide/question）")
    parser.add_argument("--text", help="メインテキスト（card型用）")
    parser.add_argument("--texts", nargs="+", help="複数テキスト（slide型用）")
    parser.add_argument("--options", nargs="+", help="選択肢（question型用）")
    parser.add_argument("--subtitle", default="", help="サブテキスト")
    parser.add_argument("--duration", type=int, default=8, help="尺（秒）")
    parser.add_argument("--bgm", help="BGMファイルパス")
    parser.add_argument("--script", help="スクリプトJSONパス")
    parser.add_argument("--output", help="出力ファイル名")
    args = parser.parse_args()

    print("=" * 50)
    print("  His Recoveries - リール自動編集")
    print("=" * 50)

    if args.script:
        result = create_from_script(args.script, args.bgm)
    elif args.type == "card" and args.text:
        result = create_card_reel(args.text, args.subtitle, args.duration, args.bgm, args.output)
    elif args.type == "slide" and args.texts:
        result = create_slide_reel(args.texts, args.duration, args.bgm, args.output)
    elif args.type == "question" and args.text:
        result = create_question_reel(args.text, args.options or [], args.duration, args.bgm, args.output)
    else:
        parser.print_help()
        return

    if result:
        print(f"\n  📱 完成: {result}")
        print(f"  → Instagram投稿 or プレビュー確認してください")
    print()


if __name__ == "__main__":
    main()
