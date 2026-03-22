#!/usr/bin/env python3
"""ローカル Whisper で動画を文字起こし → JSON 出力"""
import sys
import json
import os

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "使い方: python transcribe.py <video_path>"}))
        sys.exit(1)

    video_path = sys.argv[1]
    if not os.path.exists(video_path):
        print(json.dumps({"error": f"ファイルが見つかりません: {video_path}"}))
        sys.exit(1)

    # Model selection: prefer medium for balance of speed/accuracy
    model_name = os.environ.get("WHISPER_MODEL", "medium")

    try:
        import whisper
    except ImportError:
        print(json.dumps({"error": "whisper がインストールされていません。setup.sh を実行してください"}))
        sys.exit(1)

    sys.stderr.write(f"Whisper モデル '{model_name}' を読み込み中...\n")
    model = whisper.load_model(model_name)

    sys.stderr.write(f"文字起こし中: {video_path}\n")
    result = model.transcribe(
        video_path,
        language="ja",
        word_timestamps=True,
        verbose=False,
    )

    # Build output
    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "id": seg["id"],
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"].strip(),
        })

    words = []
    for seg in result.get("segments", []):
        for w in seg.get("words", []):
            words.append({
                "word": w["word"].strip(),
                "start": round(w["start"], 2),
                "end": round(w["end"], 2),
            })

    output = {
        "text": result.get("text", ""),
        "segments": segments,
        "words": words,
        "duration": round(result.get("segments", [{}])[-1].get("end", 0), 2) if segments else 0,
    }

    print(json.dumps(output, ensure_ascii=False))

if __name__ == "__main__":
    main()
