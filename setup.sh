#!/bin/bash
# ── Video Ops ワンコマンドセットアップ ──
# 使い方: bash setup.sh

set -e
echo ""
echo "  === Video Ops セットアップ ==="
echo ""

# ── Node.js 確認 ──
if ! command -v node &>/dev/null; then
  echo "  ❌ Node.js が見つかりません"
  echo "     https://nodejs.org/ からインストールしてください"
  exit 1
fi
NODE_VER=$(node -v | sed 's/v//' | cut -d. -f1)
if [ "$NODE_VER" -lt 18 ]; then
  echo "  ❌ Node.js 18以上が必要です (現在: $(node -v))"
  exit 1
fi
echo "  ✅ Node.js $(node -v)"

# ── Python 確認 ──
PYTHON=""
if command -v python3 &>/dev/null; then
  PYTHON="python3"
elif command -v python &>/dev/null; then
  PYTHON="python"
fi

if [ -z "$PYTHON" ]; then
  echo "  ⚠️  Python が見つかりません（自動字幕なしで続行）"
else
  echo "  ✅ Python $($PYTHON --version 2>&1 | awk '{print $2}')"
fi

# ── ffmpeg 確認 ──
if command -v ffmpeg &>/dev/null; then
  echo "  ✅ ffmpeg $(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')"
else
  echo "  ⚠️  ffmpeg が見つかりません"
  echo "     Mac: brew install ffmpeg"
  echo "     Ubuntu: sudo apt install ffmpeg"
fi

# ── npm install ──
echo ""
echo "  📦 npm パッケージをインストール中..."
npm install --silent 2>&1 | tail -1

# ── Python venv + Whisper ──
if [ -n "$PYTHON" ]; then
  echo "  🐍 Python 仮想環境をセットアップ中..."
  $PYTHON -m venv venv 2>/dev/null || true

  if [ -f "venv/bin/pip" ]; then
    PIP="venv/bin/pip"
    VPYTHON="venv/bin/python3"
  elif [ -f "venv/Scripts/pip.exe" ]; then
    PIP="venv/Scripts/pip.exe"
    VPYTHON="venv/Scripts/python.exe"
  else
    echo "  ⚠️  venv の作成に失敗（自動字幕なしで続行）"
    PIP=""
  fi

  if [ -n "$PIP" ]; then
    echo "  📦 Whisper をインストール中（初回は数分かかります）..."
    $PIP install --quiet --upgrade pip 2>/dev/null
    $PIP install --quiet openai-whisper torch torchaudio 2>/dev/null

    # Verify
    if $VPYTHON -c "import whisper; print('OK')" 2>/dev/null | grep -q OK; then
      echo "  ✅ Whisper インストール完了"

      echo "  📥 Whisper モデルをダウンロード中（初回のみ、約1.5GB）..."
      $VPYTHON -c "import whisper; whisper.load_model('medium'); print('done')" 2>/dev/null | grep -q done && \
        echo "  ✅ Whisper medium モデル準備完了" || \
        echo "  ⚠️  モデルダウンロード失敗（後で自動ダウンロードされます）"
    else
      echo "  ⚠️  Whisper インストール失敗（自動字幕なしで続行）"
    fi
  fi
fi

# ── Build frontend ──
echo ""
echo "  🔨 フロントエンドをビルド中..."
npm run build --silent 2>&1 | tail -1

# ── Create directories ──
mkdir -p uploads output

echo ""
echo "  ✅ セットアップ完了！"
echo ""
echo "  起動方法:"
echo "    npm start"
echo ""
echo "  ブラウザで開く:"
echo "    http://localhost:3000"
echo ""
