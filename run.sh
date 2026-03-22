#!/bin/bash
#
# run.sh - 素材を入れてダブルクリックするだけ
#
# input/ の素材を全部解析 → AIが投稿プランを作成 → 動画生成 → レポート出力
#
# 使い方:
#   1. input/ に動画ファイルを入れる
#   2. bash run.sh（または chmod +x run.sh してダブルクリック）
#   3. output/ に完成動画、reports/ に投稿プラン＆キャプションが出力される
#

set -e

cd "$(dirname "$0")"

echo ""
echo "=================================================="
echo "  Video AIops - 投稿プランナー"
echo "=================================================="
echo ""

# input/ ディレクトリの確認
if [ ! -d "input" ]; then
    mkdir -p input
    echo "  input/ フォルダを作りました。"
    echo "  動画ファイルを入れてから再実行してください。"
    echo ""
    exit 0
fi

# 動画ファイルを検出
VIDEOS=$(find input/ -maxdepth 1 -type f \( -name "*.mp4" -o -name "*.mov" -o -name "*.avi" -o -name "*.mkv" -o -name "*.webm" -o -name "*.m4v" \) 2>/dev/null | sort)

if [ -z "$VIDEOS" ]; then
    echo "  input/ に動画ファイルが見つかりません。"
    echo ""
    echo "  対応形式: .mp4 .mov .avi .mkv .webm .m4v"
    echo "  動画を input/ に入れてから再実行してください。"
    echo ""
    exit 0
fi

COUNT=$(echo "$VIDEOS" | wc -l | tr -d ' ')
echo "  ${COUNT}個の素材を検出"
echo ""

# ジャンル選択
echo "  ジャンルを選んでください:"
echo ""
echo "    1) beauty    - 美容・コスメ"
echo "    2) food      - 料理・グルメ"
echo "    3) travel    - 旅行・Vlog"
echo "    4) fitness   - 筋トレ・フィットネス"
echo "    5) business  - ビジネス・ノウハウ"
echo "    6) lifestyle - ライフスタイル・日常"
echo "    7) education - 教育・解説"
echo "    8) product   - 商品紹介・レビュー"
echo ""
read -p "  番号を入力 (デフォルト: 1): " GENRE_NUM

case "${GENRE_NUM:-1}" in
    1) GENRE="beauty" ;;
    2) GENRE="food" ;;
    3) GENRE="travel" ;;
    4) GENRE="fitness" ;;
    5) GENRE="business" ;;
    6) GENRE="lifestyle" ;;
    7) GENRE="education" ;;
    8) GENRE="product" ;;
    *) GENRE="beauty" ;;
esac

# 素材リサイクル提案も出すか
echo ""
read -p "  素材リサイクル提案も出す？ (y/N): " RECYCLE
RECYCLE_FLAG=""
if [ "$RECYCLE" = "y" ] || [ "$RECYCLE" = "Y" ]; then
    RECYCLE_FLAG="--recycle"
fi

echo ""
echo "  ジャンル: $GENRE"
echo "  実行します..."
echo ""

# プランナー実行
python3 scripts/planner.py --genre "$GENRE" $RECYCLE_FLAG

echo ""
echo "=================================================="
echo "  次にやること:"
echo "    1. output/tiktok/ の動画をスマホに送る"
echo "    2. reports/plan_*.md からキャプションとハッシュタグをコピー"
echo "    3. TikTokスタジオで予約投稿"
echo "    4. BGMはTikTokアプリ内で追加"
echo "=================================================="
echo ""
echo "  プランを修正して再生成したい場合:"
echo "    reports/plan_*.json を編集して:"
echo "    python3 scripts/planner.py --plan-json reports/plan_YYYY-MM-DD.json"
echo ""
