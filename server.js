import express from "express";
import multer from "multer";
import cors from "cors";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";
import { execFile } from "child_process";
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = express();
const PORT = process.env.PORT || 3000;

// ── Directories ──
const UPLOAD_DIR = path.join(__dirname, "uploads");
const OUTPUT_DIR = path.join(__dirname, "output");
const REEL_DIR = path.join(__dirname, "instagram", "output");
fs.mkdirSync(UPLOAD_DIR, { recursive: true });
fs.mkdirSync(OUTPUT_DIR, { recursive: true });

// ── Python resolver (venv 優先、なければシステム python3) ──
function resolvePython() {
  const venvPython = path.join(__dirname, "venv", "bin", "python3");
  const venvPythonWin = path.join(__dirname, "venv", "Scripts", "python.exe");
  if (fs.existsSync(venvPython)) return venvPython;
  if (fs.existsSync(venvPythonWin)) return venvPythonWin;
  return process.platform === "win32" ? "python" : "python3";
}

// Python スクリプトを実行し stdout の JSON を返す
function runPythonJson(args, { timeout = 120000 } = {}) {
  return new Promise((resolve, reject) => {
    execFile(
      resolvePython(),
      args,
      { cwd: __dirname, maxBuffer: 20 * 1024 * 1024, timeout },
      (error, stdout, stderr) => {
        if (error && !stdout) {
          return reject(new Error((stderr || error.message).trim()));
        }
        try {
          resolve(JSON.parse(stdout.trim()));
        } catch {
          reject(new Error("Python 出力の解析に失敗しました: " + (stderr || stdout).slice(0, 300)));
        }
      }
    );
  });
}

// ── Middleware ──
app.use(cors());
app.use(express.json({ limit: "10mb" }));
app.use("/uploads", express.static(UPLOAD_DIR));
app.use("/output", express.static(OUTPUT_DIR));
app.use("/reels", express.static(REEL_DIR));

// Serve frontend (Vite build output)
app.use(express.static(path.join(__dirname, "dist")));

// ── File Upload ──
const upload = multer({
  storage: multer.diskStorage({
    destination: UPLOAD_DIR,
    filename: (req, file, cb) => {
      const safe = file.originalname.replace(/[^a-zA-Z0-9._-]/g, "_");
      cb(null, `${Date.now()}_${safe}`);
    },
  }),
  limits: { fileSize: 500 * 1024 * 1024 },
  fileFilter: (req, file, cb) => {
    const allowed = [".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"];
    const ext = path.extname(file.originalname).toLowerCase();
    cb(null, allowed.includes(ext));
  },
});

app.post("/api/upload", upload.array("files", 10), (req, res) => {
  const files = (req.files || []).map((f) => ({
    name: f.originalname,
    filename: f.filename,
    url: `/uploads/${f.filename}`,
    size_mb: Math.round((f.size / (1024 * 1024)) * 10) / 10,
  }));
  res.json({ files, count: files.length });
});

app.get("/api/files", (req, res) => {
  try {
    const files = fs.readdirSync(UPLOAD_DIR)
      .filter((f) => /\.(mp4|mov|avi|mkv|webm|m4v)$/i.test(f))
      .map((f) => {
        const stat = fs.statSync(path.join(UPLOAD_DIR, f));
        return {
          name: f,
          url: `/uploads/${f}`,
          size_mb: Math.round((stat.size / (1024 * 1024)) * 10) / 10,
          uploaded: stat.mtime,
        };
      })
      .sort((a, b) => new Date(b.uploaded) - new Date(a.uploaded));
    res.json({ files });
  } catch {
    res.json({ files: [] });
  }
});

app.post("/api/delete", (req, res) => {
  const { filename } = req.body || {};
  if (!filename) return res.status(400).json({ error: "filename required" });
  const filepath = path.join(UPLOAD_DIR, path.basename(filename));
  if (fs.existsSync(filepath)) fs.unlinkSync(filepath);
  res.json({ deleted: true });
});

// ── Video Merge (ffmpeg concat) ──
app.post("/api/merge", async (req, res) => {
  const { filenames, order } = req.body || {};
  if (!filenames || !Array.isArray(filenames) || filenames.length < 2) {
    return res.status(400).json({ error: "2本以上のファイル名を指定してください" });
  }

  // Validate all files exist
  const paths = filenames.map((f) => path.join(UPLOAD_DIR, path.basename(f)));
  for (const p of paths) {
    if (!fs.existsSync(p)) {
      return res.status(404).json({ error: `ファイルが見つかりません: ${path.basename(p)}` });
    }
  }

  try {
    // Create concat list file
    const listFile = path.join(UPLOAD_DIR, `concat_${Date.now()}.txt`);
    const listContent = paths.map((p) => `file '${p}'`).join("\n");
    fs.writeFileSync(listFile, listContent);

    const outputFile = `merged_${Date.now()}.mp4`;
    const outputPath = path.join(UPLOAD_DIR, outputFile);

    // ffmpeg concat
    await new Promise((resolve, reject) => {
      execFile("ffmpeg", [
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", listFile,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        outputPath,
      ], { timeout: 300000 }, (error, stdout, stderr) => {
        fs.unlinkSync(listFile);
        if (error) reject(new Error(stderr || error.message));
        else resolve();
      });
    });

    const stat = fs.statSync(outputPath);
    console.log(`Merged ${filenames.length} files → ${outputFile}`);

    res.json({
      success: true,
      filename: outputFile,
      url: `/uploads/${outputFile}`,
      size_mb: Math.round((stat.size / (1024 * 1024)) * 10) / 10,
      count: filenames.length,
    });
  } catch (err) {
    console.error("Merge error:", err);
    res.status(500).json({ error: "動画の結合に失敗: " + err.message });
  }
});

// ── Whisper Transcription (ローカル / API 両対応) ──
app.post("/api/transcribe", async (req, res) => {
  const { filename } = req.body || {};
  if (!filename) return res.status(400).json({ error: "filename required" });

  const filepath = path.join(UPLOAD_DIR, path.basename(filename));
  if (!fs.existsSync(filepath)) {
    return res.status(404).json({ error: "ファイルが見つかりません" });
  }

  // Try local Whisper first (free), fall back to OpenAI API
  const venvPython = path.join(__dirname, "venv", "bin", "python3");
  const venvPythonWin = path.join(__dirname, "venv", "Scripts", "python.exe");
  const pythonPath = fs.existsSync(venvPython)
    ? venvPython
    : fs.existsSync(venvPythonWin)
      ? venvPythonWin
      : null;

  if (pythonPath) {
    // ── Local Whisper (free) ──
    console.log("Using local Whisper...");
    const scriptPath = path.join(__dirname, "scripts", "transcribe.py");

    const child = execFile(
      pythonPath,
      [scriptPath, filepath],
      { maxBuffer: 50 * 1024 * 1024, timeout: 600000 },
      (error, stdout, stderr) => {
        if (stderr) console.log("Whisper:", stderr.trim());
        if (error) {
          console.error("Whisper error:", error.message);
          return res.status(500).json({
            error: "ローカル Whisper でエラーが発生しました: " + error.message,
          });
        }
        try {
          const result = JSON.parse(stdout);
          if (result.error) {
            return res.status(500).json({ error: result.error });
          }
          return res.json(result);
        } catch {
          return res.status(500).json({ error: "Whisper の出力解析に失敗" });
        }
      }
    );
    return;
  }

  // ── OpenAI API fallback (if OPENAI_API_KEY is set) ──
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    return res.status(500).json({
      error: "Whisper が利用できません。setup.sh を実行するか、OPENAI_API_KEY を設定してください",
    });
  }

  try {
    const { default: OpenAI } = await import("openai");
    const openai = new OpenAI({ apiKey });
    const file = fs.createReadStream(filepath);

    const transcription = await openai.audio.transcriptions.create({
      file,
      model: "whisper-1",
      language: "ja",
      response_format: "verbose_json",
      timestamp_granularities: ["word", "segment"],
    });

    res.json({
      text: transcription.text,
      segments: (transcription.segments || []).map((s) => ({
        id: s.id, start: s.start, end: s.end, text: s.text,
      })),
      words: transcription.words || [],
      duration: transcription.duration,
    });
  } catch (err) {
    console.error("Transcribe error:", err);
    res.status(500).json({ error: err.message || "文字起こし失敗" });
  }
});

// ── HeyGen API ──
app.post("/api/heygen", async (req, res) => {
  const apiKey = process.env.HEYGEN_API_KEY;
  if (!apiKey) {
    return res.status(500).json({ error: "HEYGEN_API_KEY が未設定です" });
  }

  const { action, script, avatar_id, voice_id, video_id } = req.body || {};

  try {
    if (action === "list-avatars") {
      const r = await fetch("https://api.heygen.com/v2/avatars", {
        headers: { "X-Api-Key": apiKey },
      });
      const data = await r.json();
      return res.json({
        avatars: (data.data?.avatars || []).map((a) => ({
          avatar_id: a.avatar_id,
          avatar_name: a.avatar_name,
          preview_image_url: a.preview_image_url,
        })),
      });
    }

    if (action === "list-voices") {
      const r = await fetch("https://api.heygen.com/v2/voices", {
        headers: { "X-Api-Key": apiKey },
      });
      const data = await r.json();
      return res.json({
        voices: (data.data?.voices || [])
          .filter((v) => v.language === "Japanese" || v.language === "ja")
          .map((v) => ({
            voice_id: v.voice_id,
            name: v.name,
            gender: v.gender,
          })),
      });
    }

    if (action === "generate") {
      if (!script) return res.status(400).json({ error: "台本が必要です" });
      const r = await fetch("https://api.heygen.com/v2/video/generate", {
        method: "POST",
        headers: { "X-Api-Key": apiKey, "Content-Type": "application/json" },
        body: JSON.stringify({
          video_inputs: [{
            character: { type: "avatar", avatar_id: avatar_id || "default", avatar_style: "normal" },
            voice: { type: "text", input_text: script, voice_id: voice_id || "ja-JP-NanamiNeural" },
          }],
          dimension: { width: 1080, height: 1920 },
        }),
      });
      const data = await r.json();
      return res.json({ video_id: data.data?.video_id, status: "processing" });
    }

    if (action === "status") {
      if (!video_id) return res.status(400).json({ error: "video_id必要" });
      const r = await fetch(`https://api.heygen.com/v1/video_status.get?video_id=${video_id}`, {
        headers: { "X-Api-Key": apiKey },
      });
      const data = await r.json();
      return res.json({
        status: data.data?.status,
        video_url: data.data?.video_url || null,
      });
    }

    res.status(400).json({ error: "action必要" });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── Remotion Render ──
let bundlePromise = null;

async function getBundled() {
  if (!bundlePromise) {
    bundlePromise = bundle({
      entryPoint: path.resolve(__dirname, "remotion/index.ts"),
      webpackOverride: (config) => config,
    });
  }
  return bundlePromise;
}

app.post("/api/render", async (req, res) => {
  const {
    filename,
    subtitles = [],
    width = 1080,
    height = 1920,
    fps = 30,
    compositionId = "MainVideo",
    heygenVideoUrl,
  } = req.body || {};

  if (!filename && !heygenVideoUrl) {
    return res.status(400).json({ error: "filename or heygenVideoUrl required" });
  }

  try {
    console.log(`Render start: ${compositionId} ${width}x${height}`);
    const bundled = await getBundled();

    // Determine video source
    const videoSrc = heygenVideoUrl
      ? heygenVideoUrl
      : `http://localhost:${PORT}/uploads/${path.basename(filename)}`;

    const inputProps = heygenVideoUrl
      ? { avatarVideoUrl: heygenVideoUrl, subtitles, avatarLayout: "fullscreen" }
      : { videoSrc, subtitles, muted: true };

    // Calculate duration
    let durationInFrames = 300;
    if (subtitles.length > 0) {
      const maxEnd = Math.max(...subtitles.map((s) => s.end || 0));
      durationInFrames = Math.ceil(maxEnd * fps) + fps;
    }

    const composition = await selectComposition({
      serveUrl: bundled,
      id: compositionId,
      inputProps,
    });

    composition.width = width;
    composition.height = height;
    composition.fps = fps;
    composition.durationInFrames = durationInFrames;

    const outputFile = `render_${Date.now()}.mp4`;
    const outputPath = path.join(OUTPUT_DIR, outputFile);

    await renderMedia({
      composition,
      serveUrl: bundled,
      codec: "h264",
      outputLocation: outputPath,
      inputProps,
    });

    const stat = fs.statSync(outputPath);
    console.log(`Render done: ${outputFile} (${(stat.size / 1024 / 1024).toFixed(1)}MB)`);

    res.json({
      success: true,
      url: `/output/${outputFile}`,
      filename: outputFile,
      size_mb: Math.round((stat.size / (1024 * 1024)) * 10) / 10,
    });
  } catch (err) {
    console.error("Render error:", err);
    res.status(500).json({ error: err.message || "レンダリング失敗" });
  }
});

// ── List rendered outputs ──
app.get("/api/outputs", (req, res) => {
  try {
    const files = fs.readdirSync(OUTPUT_DIR)
      .filter((f) => f.endsWith(".mp4"))
      .map((f) => {
        const stat = fs.statSync(path.join(OUTPUT_DIR, f));
        return {
          name: f,
          url: `/output/${f}`,
          size_mb: Math.round((stat.size / (1024 * 1024)) * 10) / 10,
          created: stat.mtime,
        };
      })
      .sort((a, b) => new Date(b.created) - new Date(a.created));
    res.json({ files });
  } catch {
    res.json({ files: [] });
  }
});

// ── 台本生成（scripts/script.py） ──
app.post("/api/script", async (req, res) => {
  const { theme, style = "beforeafter", client } = req.body || {};
  if (!theme || !theme.trim()) {
    return res.status(400).json({ error: "テーマを入力してください" });
  }
  const args = ["scripts/script.py", "--theme", theme.trim(), "--style", style, "--json"];
  if (client) args.push("--client", client);
  try {
    const script = await runPythonJson(args, { timeout: 120000 });
    res.json(script);
  } catch (err) {
    console.error("Script error:", err.message);
    res.status(500).json({ error: "台本生成に失敗しました: " + err.message });
  }
});

// ── リール生成（instagram/script_writer.py → reel_editor.py） ──
app.post("/api/reel", async (req, res) => {
  const { hypothesis, type = "card" } = req.body || {};
  if (!hypothesis) {
    return res.status(400).json({ error: "仮説を選択してください" });
  }

  let script;
  try {
    script = await runPythonJson(
      ["instagram/script_writer.py", "--hypothesis", hypothesis, "--type", type, "--json"],
      { timeout: 120000 }
    );
    if (script.error) throw new Error(script.error);
  } catch (err) {
    console.error("Reel script error:", err.message);
    return res.status(500).json({ error: "スクリプト生成に失敗しました: " + err.message });
  }

  // スクリプトから動画レンダリングを試みる（Pillow/ffmpeg が必要。失敗してもスクリプトは返す）
  const scriptFile = path.join(REEL_DIR, `_api_script_${Date.now()}.json`);
  try {
    fs.mkdirSync(REEL_DIR, { recursive: true });
    fs.writeFileSync(scriptFile, JSON.stringify(script), "utf-8");
    const before = new Set(fs.existsSync(REEL_DIR) ? fs.readdirSync(REEL_DIR) : []);

    await new Promise((resolve, reject) => {
      execFile(
        resolvePython(),
        ["instagram/reel_editor.py", "--script", scriptFile],
        { cwd: __dirname, maxBuffer: 20 * 1024 * 1024, timeout: 300000 },
        (error, stdout, stderr) => (error ? reject(new Error(stderr || error.message)) : resolve(stdout))
      );
    });

    const produced = fs.readdirSync(REEL_DIR)
      .filter((f) => f.endsWith(".mp4") && !before.has(f))
      .map((f) => ({ f, m: fs.statSync(path.join(REEL_DIR, f)).mtimeMs }))
      .sort((a, b) => b.m - a.m)[0];

    if (produced) {
      script.output = `/reels/${produced.f}`;
    }
  } catch (err) {
    // レンダリング環境（Pillow 等）が無い場合はスクリプトのみ返す
    console.warn("Reel render skipped:", err.message.split("\n")[0]);
    script.render_note = "動画レンダリングはスキップされました（Pillow/ffmpeg 未導入）。スクリプトのみ生成しました。";
  } finally {
    if (fs.existsSync(scriptFile)) fs.unlinkSync(scriptFile);
  }

  res.json(script);
});

// ── クライアント一覧（scripts/client.py） ──
app.get("/api/clients", async (req, res) => {
  try {
    const data = await runPythonJson(["scripts/client.py", "list", "--json"], { timeout: 30000 });
    res.json(data);
  } catch (err) {
    console.error("Clients error:", err.message);
    res.json({ clients: [] });
  }
});

// ── 投稿プラン生成（scripts/planner.py、アップロード素材をプランのみ生成） ──
app.post("/api/plan", async (req, res) => {
  const { genre = "beauty", recycle = false, client } = req.body || {};
  const args = ["scripts/planner.py", "--input-dir", UPLOAD_DIR, "--genre", genre, "--json"];
  if (recycle) args.push("--recycle");
  if (client) args.push("--client", client);
  try {
    const data = await runPythonJson(args, { timeout: 600000 });
    if (data.error) return res.status(400).json(data);
    res.json(data);
  } catch (err) {
    console.error("Plan error:", err.message);
    res.status(500).json({ error: "投稿プラン生成に失敗しました: " + err.message });
  }
});

// ── フック最適化（scripts/hook_optimizer.py、フックテロップ3案を生成） ──
app.post("/api/hook", async (req, res) => {
  const { theme = "", genre = "beauty", max_duration = 20, filename, client } = req.body || {};
  const args = ["scripts/hook_optimizer.py"];
  if (filename) args.push(path.join(UPLOAD_DIR, path.basename(filename)));
  args.push("--theme", theme, "--genre", genre, "--max-duration", String(max_duration), "--json");
  if (client) args.push("--client", client);
  try {
    const data = await runPythonJson(args, { timeout: 300000 });
    res.json(data);
  } catch (err) {
    console.error("Hook error:", err.message);
    res.status(500).json({ error: "フック最適化に失敗しました: " + err.message });
  }
});

// ── バズ動画の型を分析（scripts/analyze_buzz.py） ──
app.post("/api/buzz", async (req, res) => {
  const { url, name, client } = req.body || {};
  if (!url || !url.trim()) return res.status(400).json({ error: "バズ動画URLを入力してください" });
  if (!name || !name.trim()) return res.status(400).json({ error: "型の名前を入力してください" });
  const args = ["scripts/analyze_buzz.py", url.trim(), "--name", name.trim(), "--json"];
  if (client) args.push("--client", client);
  try {
    const data = await runPythonJson(args, { timeout: 300000 });
    if (data.error) return res.status(400).json(data);
    res.json(data);
  } catch (err) {
    console.error("Buzz error:", err.message);
    res.status(500).json({ error: "バズ分析に失敗しました: " + err.message });
  }
});

// ── バズの型 一覧（scripts/analyze_buzz.py --list） ──
app.get("/api/templates", async (req, res) => {
  try {
    const data = await runPythonJson(["scripts/analyze_buzz.py", "--list"], { timeout: 30000 });
    res.json(data);
  } catch (err) {
    console.error("Templates error:", err.message);
    res.json({ templates: [] });
  }
});

// ── SPA fallback ──
app.use((req, res) => {
  res.sendFile(path.join(__dirname, "dist", "index.html"));
});

app.listen(PORT, () => {
  console.log(`\n  Video Ops サーバー起動`);
  console.log(`  http://localhost:${PORT}\n`);
});
