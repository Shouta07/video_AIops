#!/bin/bash
#
# run.sh - 素材を入れてダブルクリックするだけ
#
# input/ フォルダ内の動画ファイルを自動検出して
# パイプラインを実行 → テロップ付き動画 + 投稿戦略レポートを生成
#
# 使い方:
#   1. input/ に動画ファイルを入れる
#   2. このファイルをダブルクリック（または bash run.sh）
#   3. output/ に完成動画、reports/ に投稿戦略が出力される
#

set -e

# スクリプトのあるディレクトリに移動
cd "$(dirname "$0")"

echo ""
echo "=================================================="
echo "  Video AIops - ワンクリック実行"
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

# 動画ファイル一覧を表示
COUNT=$(echo "$VIDEOS" | wc -l | tr -d ' ')
echo "  ${COUNT}個の動画を検出しました:"
echo ""
echo "$VIDEOS" | while read -r f; do
    echo "    - $(basename "$f")"
done
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

echo ""
echo "  ジャンル: $GENRE"
echo ""

# 各動画に対してパイプラインを実行
SUCCESS=0
FAIL=0

echo "$VIDEOS" | while read -r VIDEO; do
    echo "=================================================="
    echo "  処理中: $(basename "$VIDEO")"
    echo "=================================================="

    if python3 scripts/pipeline.py "$VIDEO" --genre "$GENRE"; then
        SUCCESS=$((SUCCESS + 1))
    else
        echo "  ⚠️  エラーが発生しました: $(basename "$VIDEO")"
        FAIL=$((FAIL + 1))
    fi

    echo ""
done

# 完了メッセージ
echo "=================================================="
echo "  全て完了!"
echo "=================================================="
echo ""
echo "  出力先:"
echo "    動画:     output/tiktok/  output/reels/  output/shorts/"
echo "    レポート:  reports/"
echo ""
echo "  次のステップ:"
echo "    1. output/ の動画をスマホに送る"
echo "    2. reports/ のレポートから投稿文とハッシュタグをコピー"
echo "    3. TikTok / Instagram / YouTube に投稿!"
echo ""
echo "  ※ BGMはTikTokアプリ内で追加してください"
echo ""
