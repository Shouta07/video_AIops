#!/usr/bin/env python3
"""
テロップ付き動画を生成する。

使い方:
  python scripts/add_telop.py                          # デフォルト設定で実行
  python scripts/add_telop.py -i input.mp4             # 入力ファイル指定
  python scripts/add_telop.py -c scripts/captions.json # テロップJSON指定
  python scripts/add_telop.py -o output/final.mp4      # 出力先指定
"""
import json, subprocess, sys, os, argparse

def hex_to_ffmpeg(color):
    """#RRGGBB → 0xRRGGBB に変換。名前付き色はそのまま返す。"""
    if color.startswith("#"):
        return "0x" + color[1:]
    return color

def build_filter(captions, font):
    parts = []
    for c in captions:
        color = hex_to_ffmpeg(c["color"])
        parts.append(
            f"drawtext=text='{c['text']}'"
            f":fontfile='{font}'"
            f":fontsize={c['size']}"
            f":fontcolor={color}"
            f":borderw=4:bordercolor=black"
            f":x=(w-tw)/2:y=h*{c['y']}"
            f":enable='between(t,{c['start']},{c['end']})'"
        )
    return ",".join(parts)

def main():
    parser = argparse.ArgumentParser(description="動画にテロップを追加")
    parser.add_argument("-i", "--input",    default="output/eyebrow_tiktok.mp4")
    parser.add_argument("-o", "--output",   default="output/tiktok/eyebrow_final.mp4")
    parser.add_argument("-c", "--captions", default="scripts/captions.json")
    parser.add_argument("-f", "--font",     default="/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"エラー: 入力ファイルが見つかりません: {args.input}")
        sys.exit(1)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    with open(args.captions, encoding="utf-8") as f:
        captions = json.load(f)

    vf = build_filter(captions, args.font)

    cmd = [
        "ffmpeg", "-y", "-i", args.input,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart",
        args.output
    ]

    print(f"入力: {args.input}")
    print(f"出力: {args.output}")
    print(f"テロップ数: {len(captions)}")
    print()

    result = subprocess.run(cmd)
    if result.returncode == 0:
        print(f"\n完成: {args.output}")
    else:
        print(f"\nエラーが発生しました (code: {result.returncode})")
        sys.exit(result.returncode)

if __name__ == "__main__":
    main()
