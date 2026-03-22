#!/usr/bin/env python3
"""
素材監視 - input/ に動画が追加されたら自動でパイプラインを実行

使い方:
  python scripts/watch.py                    # デフォルト: beautyジャンル
  python scripts/watch.py --genre food       # ジャンル指定
  python scripts/watch.py --interval 5       # 5秒間隔でチェック

バックグラウンド実行:
  nohup python scripts/watch.py --genre beauty &

仕組み:
  - input/ フォルダを定期的にチェック
  - 新しい動画ファイルが追加されたら pipeline.py を自動実行
  - 処理済みファイルは input/done/ に移動
  - 標準ライブラリのみ使用（追加パッケージ不要）
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
INPUT_DIR = "input"
DONE_DIR = "input/done"
STATE_FILE = "input/.watch_state.json"


def get_video_files(directory):
    """ディレクトリ内の動画ファイルを取得"""
    files = []
    if not os.path.exists(directory):
        return files
    for name in os.listdir(directory):
        ext = os.path.splitext(name)[1].lower()
        if ext in VIDEO_EXTENSIONS:
            path = os.path.join(directory, name)
            if os.path.isfile(path):
                files.append(path)
    return sorted(files)


def load_state():
    """処理済みファイルの状態を読み込み"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"processed": []}


def save_state(state):
    """処理済みファイルの状態を保存"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def process_video(video_path, genre):
    """1つの動画に対してパイプラインを実行"""
    basename = os.path.basename(video_path)
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{timestamp}] 新しい素材を検出: {basename}")
    print(f"  → パイプライン実行中...")

    cmd = [sys.executable, "scripts/pipeline.py", video_path, "--genre", genre]
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print(f"  → 完了! output/ と reports/ を確認してください")
        # 処理済みファイルを done/ に移動
        os.makedirs(DONE_DIR, exist_ok=True)
        done_path = os.path.join(DONE_DIR, basename)
        if os.path.exists(done_path):
            # 同名ファイルがあればタイムスタンプ付き
            name, ext = os.path.splitext(basename)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            done_path = os.path.join(DONE_DIR, f"{name}_{ts}{ext}")
        shutil.move(video_path, done_path)
        print(f"  → 素材を移動: {done_path}")
        return True
    else:
        print(f"  → エラーが発生しました。素材はそのまま残しています。")
        return False


def watch(genre, interval):
    """input/ フォルダを監視して新規動画を自動処理"""
    os.makedirs(INPUT_DIR, exist_ok=True)
    state = load_state()
    processed = set(state.get("processed", []))

    print("=" * 50)
    print("  Video AIops - 素材監視モード")
    print("=" * 50)
    print(f"  監視フォルダ: {INPUT_DIR}/")
    print(f"  ジャンル:     {genre}")
    print(f"  チェック間隔: {interval}秒")
    print(f"  処理済み移動先: {DONE_DIR}/")
    print(f"")
    print(f"  input/ に動画を入れると自動でパイプラインが実行されます")
    print(f"  停止: Ctrl+C")
    print("=" * 50)

    try:
        while True:
            videos = get_video_files(INPUT_DIR)
            new_videos = [v for v in videos if os.path.basename(v) not in processed]

            for video in new_videos:
                basename = os.path.basename(video)
                # ファイルの書き込みが完了するまで少し待つ
                size1 = os.path.getsize(video)
                time.sleep(2)
                size2 = os.path.getsize(video)
                if size1 != size2:
                    # まだ書き込み中
                    continue

                success = process_video(video, genre)
                if success:
                    processed.add(basename)
                    state["processed"] = list(processed)
                    save_state(state)

            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\n\n  監視を停止しました。")
        print(f"  処理済み: {len(processed)}件")


def main():
    parser = argparse.ArgumentParser(
        description="素材監視 - input/ に動画が追加されたら自動でパイプラインを実行",
    )
    parser.add_argument("--genre", default="beauty",
                        choices=["beauty", "food", "travel", "fitness", "business", "lifestyle", "education", "product"],
                        help="動画のジャンル（デフォルト: beauty）")
    parser.add_argument("--interval", type=int, default=10,
                        help="チェック間隔（秒）（デフォルト: 10）")
    args = parser.parse_args()

    watch(args.genre, args.interval)


if __name__ == "__main__":
    main()
