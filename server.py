import os
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="web", static_url_path="")

INPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input")
os.makedirs(INPUT_DIR, exist_ok=True)

ALLOWED_EXT = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


@app.route("/")
def index():
    return send_from_directory("web", "index.html")


@app.route("/upload", methods=["POST"])
def upload():
    if "files" not in request.files:
        return jsonify({"error": "ファイルが選択されていません"}), 400

    files = request.files.getlist("files")
    saved = []
    for f in files:
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in ALLOWED_EXT:
            continue
        safe_name = f.filename.replace("/", "_").replace("\\", "_")
        dest = os.path.join(INPUT_DIR, safe_name)
        f.save(dest)
        size_mb = os.path.getsize(dest) / (1024 * 1024)
        saved.append({"name": safe_name, "size_mb": round(size_mb, 1)})

    return jsonify({"uploaded": saved, "count": len(saved)})


@app.route("/files")
def list_files():
    files = []
    for name in sorted(os.listdir(INPUT_DIR)):
        ext = os.path.splitext(name)[1].lower()
        if ext in ALLOWED_EXT:
            path = os.path.join(INPUT_DIR, name)
            size_mb = os.path.getsize(path) / (1024 * 1024)
            files.append({"name": name, "size_mb": round(size_mb, 1)})
    return jsonify({"files": files})


if __name__ == "__main__":
    print("\n  動画アップロードサーバー起動中...")
    print("  http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
