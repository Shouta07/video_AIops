#!/usr/bin/env node
// ── Remotion レンダリングスクリプト ──
// 使い方:
//   node render.mjs --video public/input.mp4 --subtitles public/subtitles.json --out output/final.mp4
//   node render.mjs --heygen <heygen_video_url> --subtitles public/subtitles.json --out output/final.mp4

import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import path from "path";
import fs from "fs";

const args = process.argv.slice(2);

function getArg(name) {
  const idx = args.indexOf(`--${name}`);
  return idx >= 0 && idx + 1 < args.length ? args[idx + 1] : null;
}

async function main() {
  const videoPath = getArg("video");
  const heygenUrl = getArg("heygen");
  const subtitlesPath = getArg("subtitles");
  const outputPath = getArg("out") || "output/final.mp4";
  const width = parseInt(getArg("width") || "1080");
  const height = parseInt(getArg("height") || "1920");
  const fps = parseInt(getArg("fps") || "30");

  // Load subtitles
  let subtitles = [];
  if (subtitlesPath && fs.existsSync(subtitlesPath)) {
    subtitles = JSON.parse(fs.readFileSync(subtitlesPath, "utf-8"));
  }

  // Determine composition
  const compositionId = heygenUrl ? "HeyGenVideo" : "MainVideo";

  console.log(`\n  Remotion レンダリング開始`);
  console.log(`  コンポジション: ${compositionId}`);
  console.log(`  解像度: ${width}x${height}`);
  console.log(`  テロップ: ${subtitles.length}件\n`);

  // Bundle the Remotion project
  console.log("  バンドル中...");
  const bundled = await bundle({
    entryPoint: path.resolve("remotion/index.ts"),
    webpackOverride: (config) => config,
  });

  // Build input props
  const inputProps = heygenUrl
    ? {
        avatarVideoUrl: heygenUrl,
        subtitles,
        avatarLayout: "fullscreen",
      }
    : {
        videoSrc: videoPath?.startsWith("http")
          ? videoPath
          : `file://${path.resolve(videoPath || "")}`,
        subtitles,
        muted: true,
      };

  // Calculate duration from subtitles or default
  let durationInFrames = 300; // default 10s
  if (subtitles.length > 0) {
    const maxEnd = Math.max(...subtitles.map((s) => s.end));
    durationInFrames = Math.ceil(maxEnd * fps) + fps; // +1s buffer
  }

  // Select composition
  const composition = await selectComposition({
    serveUrl: bundled,
    id: compositionId,
    inputProps,
  });

  composition.width = width;
  composition.height = height;
  composition.fps = fps;
  composition.durationInFrames = durationInFrames;

  // Ensure output directory exists
  const outDir = path.dirname(outputPath);
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  // Render
  console.log("  レンダリング中...");
  await renderMedia({
    composition,
    serveUrl: bundled,
    codec: "h264",
    outputLocation: outputPath,
    inputProps,
    onProgress: ({ progress }) => {
      process.stdout.write(`\r  進捗: ${Math.round(progress * 100)}%`);
    },
  });

  console.log(`\n\n  完了！ ${outputPath}\n`);
}

main().catch((err) => {
  console.error("レンダリングエラー:", err.message);
  process.exit(1);
});
