#!/bin/bash
# 眉アート動画にテロップを追加するスクリプト
# 使い方: bash scripts/add_captions.sh input.mp4

INPUT="${1:-output/eyebrow_tiktok.mp4}"
OUTPUT="output/tiktok/eyebrow_final.mp4"
FONT="/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"

mkdir -p output/tiktok

# テロップ定義: 開始,終了,テキスト,フォントサイズ,色,Y位置
CAPTIONS=(
  "0,3,眉アート行ってみた,60,white,0.57"
  "3,6,仕上がりがこちら,56,white,0.57"
  "7,10,もともとこんな感じで,56,white,0.57"
  "10,14,眉毛ほぼなかったんよ,56,white,0.57"
  "14,17,メイクで描くの毎日大変で,52,white,0.57"
  "17,20,ずっと悩んでた,56,white,0.57"
  "20,22,それがこうなりました,56,yellow,0.57"
  "22,25,ちょっと濃くて太くね？ww,52,white,0.57"
  "25,28,でもすっぴんでこの眉嬉しい,48,white,0.57"
  "28,32,経過また報告するね,52,0xFFB6C1,0.54"
  "28,32,フォローで見守ってね,54,0xFFB6C1,0.60"
)

# drawtext フィルタを組み立て
FILTER=""
for cap in "${CAPTIONS[@]}"; do
  IFS=',' read -r start end text size color ypos <<< "$cap"
  [ -n "$FILTER" ] && FILTER+=","
  FILTER+="drawtext=text='${text}'"
  FILTER+=":fontfile='${FONT}'"
  FILTER+=":fontsize=${size}"
  FILTER+=":fontcolor=${color}"
  FILTER+=":borderw=4:bordercolor=black"
  FILTER+=":x=(w-tw)/2:y=h*${ypos}"
  FILTER+=":enable='between(t,${start},${end})'"
done

ffmpeg -y -ss 0 -t 32 -i "$INPUT" \
  -vf "$FILTER" \
  -c:v libx264 -preset fast -crf 18 \
  -pix_fmt yuv420p -an -movflags +faststart \
  "$OUTPUT"

echo ""
echo "完成: $OUTPUT"
