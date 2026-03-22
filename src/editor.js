// ── 動画編集エンジン (ffmpeg.wasm) ──
import { FFmpeg } from "@ffmpeg/ffmpeg";
import { toBlobURL, fetchFile } from "@ffmpeg/util";

let ffmpeg = null;
let loaded = false;

/**
 * FFmpeg を初期化（初回のみ）
 * @param {Function} onProgress - 進捗コールバック({ message, progress })
 */
export async function initFFmpeg(onProgress) {
  if (loaded) return;

  ffmpeg = new FFmpeg();

  ffmpeg.on("log", ({ message }) => {
    if (onProgress) onProgress({ message, progress: null });
  });

  ffmpeg.on("progress", ({ progress }) => {
    if (onProgress) onProgress({ message: null, progress });
  });

  const baseURL = "https://unpkg.com/@ffmpeg/core@0.12.6/dist/esm";
  await ffmpeg.load({
    coreURL: await toBlobURL(`${baseURL}/ffmpeg-core.js`, "text/javascript"),
    wasmURL: await toBlobURL(`${baseURL}/ffmpeg-core.wasm`, "application/wasm"),
  });

  loaded = true;
}

/**
 * 動画を編集して書き出す
 * @param {Object} options
 * @param {string} options.videoUrl - 元動画のURL
 * @param {string} options.filename - ファイル名
 * @param {Object} options.platform - { w, h, aspect }
 * @param {number} options.startTime - 開始秒
 * @param {number} options.endTime - 終了秒
 * @param {Array} options.subtitles - [{ text, startTime, endTime, position }]
 * @param {Function} options.onProgress - 進捗コールバック
 * @returns {Blob} 編集済み動画の Blob
 */
export async function editVideo({
  videoUrl,
  filename,
  platform,
  startTime = 0,
  endTime = null,
  subtitles = [],
  onProgress,
}) {
  await initFFmpeg(onProgress);

  if (onProgress) onProgress({ message: "動画を読み込み中...", progress: 0 });

  // Fetch source video
  const videoData = await fetchFile(videoUrl);
  const inputName = "input" + getExt(filename);
  await ffmpeg.writeFile(inputName, videoData);

  // Build FFmpeg command
  const args = buildFFmpegArgs({
    inputName,
    platform,
    startTime,
    endTime,
    subtitles,
  });

  if (onProgress) onProgress({ message: "編集処理中...", progress: 0.1 });

  const outputName = "output.mp4";
  await ffmpeg.exec(args.concat([outputName]));

  if (onProgress) onProgress({ message: "書き出し中...", progress: 0.9 });

  const data = await ffmpeg.readFile(outputName);

  // Cleanup
  await ffmpeg.deleteFile(inputName);
  await ffmpeg.deleteFile(outputName);

  if (onProgress) onProgress({ message: "完了", progress: 1 });

  return new Blob([data.buffer], { type: "video/mp4" });
}

function buildFFmpegArgs({ inputName, platform, startTime, endTime, subtitles }) {
  const args = ["-i", inputName];

  // Time range
  if (startTime > 0) {
    args.push("-ss", String(startTime));
  }
  if (endTime !== null && endTime > startTime) {
    args.push("-t", String(endTime - startTime));
  }

  // Build filter chain
  const filters = [];

  // Scale and pad to target resolution
  filters.push(
    `scale=${platform.w}:${platform.h}:force_original_aspect_ratio=decrease`,
    `pad=${platform.w}:${platform.h}:(ow-iw)/2:(oh-ih)/2:color=black`
  );

  // Add subtitles as drawtext filters
  for (const sub of subtitles) {
    const escapedText = sub.text
      .replace(/\\/g, "\\\\\\\\")
      .replace(/'/g, "\u2019")
      .replace(/:/g, "\\:");

    // Position: top, center, bottom
    let y = `h-th-60`; // default: bottom
    if (sub.position === "top") y = "60";
    else if (sub.position === "center") y = "(h-th)/2";

    let filter = `drawtext=text='${escapedText}'`;
    filter += `:fontsize=42`;
    filter += `:fontcolor=white`;
    filter += `:borderw=3`;
    filter += `:bordercolor=black`;
    filter += `:x=(w-tw)/2`;
    filter += `:y=${y}`;

    if (sub.startTime !== undefined && sub.endTime !== undefined) {
      filter += `:enable='between(t,${sub.startTime},${sub.endTime})'`;
    }

    filters.push(filter);
  }

  if (filters.length > 0) {
    args.push("-vf", filters.join(","));
  }

  // Remove audio (CLAUDE.md: BGMは音声なしで書き出す)
  args.push("-an");

  // Output settings
  args.push(
    "-c:v", "libx264",
    "-preset", "fast",
    "-crf", "23",
    "-pix_fmt", "yuv420p",
    "-movflags", "+faststart",
    "-y"
  );

  return args;
}

function getExt(filename) {
  const dot = filename.lastIndexOf(".");
  return dot >= 0 ? filename.substring(dot) : ".mp4";
}
