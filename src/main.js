import { upload } from "@vercel/blob/client";
import { generateConcepts, PLATFORM_SPECS } from "./concepts.js";
import { GENRES, buildConceptFromPattern, adjustPatternByReference } from "./patterns.js";
import { generateSubtitles, exportSRT } from "./subtitles.js";
import "./style.css";

// ── DOM Elements ──
const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const progressList = document.getElementById("progressList");
const fileGrid = document.getElementById("fileGrid");
const fileCountBadge = document.getElementById("fileCount");
const setupBanner = document.getElementById("setupBanner");
const urlInput = document.getElementById("urlInput");
const urlImportBtn = document.getElementById("urlImportBtn");

// ── SVG Icons ──
const icons = {
  film: `<svg viewBox="0 0 24 24"><rect x="2" y="2" width="20" height="20" rx="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="2" y1="17" x2="7" y2="17"/><line x1="17" y1="17" x2="22" y2="17"/><line x1="17" y1="7" x2="22" y2="7"/></svg>`,
  download: `<svg viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>`,
  trash: `<svg viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>`,
  link: `<svg viewBox="0 0 24 24"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>`,
};

// ── Tab Switching ──
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById("tab-" + tab.dataset.tab).classList.add("active");
  });
});

// ── Drop Zone Events ──
dropZone.addEventListener("click", () => fileInput.click());
dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("dragover");
});
dropZone.addEventListener("dragleave", () =>
  dropZone.classList.remove("dragover")
);
dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  handleFiles(e.dataTransfer.files);
});
fileInput.addEventListener("change", () => {
  handleFiles(fileInput.files);
  fileInput.value = "";
});

function handleFiles(files) {
  for (const file of files) {
    uploadFile(file);
  }
}

// ── File Upload ──
async function uploadFile(file) {
  const sizeMB = (file.size / 1024 / 1024).toFixed(1);

  const item = createProgressItem(escapeHtml(file.name), sizeMB + " MB", "アップロード中...");
  progressList.prepend(item);

  const bar = item.querySelector(".bar");
  const status = item.querySelector(".status");
  const meta = item.querySelector(".meta");

  try {
    await upload("videos/" + file.name, file, {
      access: "public",
      handleUploadUrl: "/api/upload",
      onUploadProgress: ({ percentage }) => {
        bar.style.width = percentage + "%";
      },
    });
    status.textContent = "完了";
    status.className = "status status-done";
    bar.style.width = "100%";
    bar.classList.add("bar-done");
    setupBanner.style.display = "none";
    loadFileList();
  } catch (err) {
    const msg = err.message || "アップロードに失敗しました";
    status.textContent = "エラー";
    status.className = "status status-error";
    meta.textContent = sizeMB + " MB - " + msg;
    showSetupBannerIfNeeded(msg);
  }
}

// ── URL Import ──
urlImportBtn.addEventListener("click", () => importFromUrl());
urlInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") importFromUrl();
});

async function importFromUrl() {
  const url = urlInput.value.trim();
  if (!url) return;

  urlImportBtn.disabled = true;
  urlImportBtn.textContent = "取り込み中...";

  // Extract display name from URL
  let displayName;
  try {
    const parsed = new URL(url);
    const segments = parsed.pathname.split("/").filter(Boolean);
    displayName = segments.length > 0
      ? decodeURIComponent(segments[segments.length - 1]).substring(0, 60)
      : parsed.hostname;
  } catch {
    displayName = url.substring(0, 60);
  }

  const item = createProgressItem(escapeHtml(displayName), "URLから取り込み", "取り込み中...");
  progressList.prepend(item);

  const bar = item.querySelector(".bar");
  const status = item.querySelector(".status");
  const meta = item.querySelector(".meta");

  // Indeterminate progress animation
  bar.style.width = "30%";
  const progressTimer = setInterval(() => {
    const current = parseFloat(bar.style.width);
    if (current < 90) bar.style.width = current + 5 + "%";
  }, 500);

  try {
    const res = await fetch("/api/import-url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });

    clearInterval(progressTimer);
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || "取り込みに失敗しました");
    }

    status.textContent = "完了";
    status.className = "status status-done";
    bar.style.width = "100%";
    bar.classList.add("bar-done");
    meta.textContent = data.size_mb ? data.size_mb + " MB" : "完了";
    urlInput.value = "";
    setupBanner.style.display = "none";
    loadFileList();
  } catch (err) {
    clearInterval(progressTimer);
    status.textContent = "エラー";
    status.className = "status status-error";
    bar.style.width = "100%";
    bar.style.background = "var(--red)";
    meta.textContent = err.message;
    showSetupBannerIfNeeded(err.message);
  } finally {
    urlImportBtn.disabled = false;
    urlImportBtn.textContent = "取り込み";
  }
}

// ── File List ──
async function loadFileList() {
  try {
    const res = await fetch("/api/files");
    if (!res.ok) {
      fileGrid.innerHTML = '<div class="empty-state">ファイル一覧を取得できません</div>';
      return;
    }
    const data = await res.json();
    if (!data.files || !data.files.length) {
      fileGrid.innerHTML =
        '<div class="empty-state">まだ動画がアップロードされていません</div>';
      fileCountBadge.style.display = "none";
      return;
    }

    fileCountBadge.textContent = data.files.length + " 本";
    fileCountBadge.style.display = "inline-flex";

    // Build file list with DOM API (no innerHTML for user data)
    fileGrid.innerHTML = "";
    for (const f of data.files) {
      fileGrid.appendChild(createFileCard(f));
    }
  } catch {
    fileGrid.innerHTML =
      '<div class="empty-state">まだ動画がアップロードされていません</div>';
    fileCountBadge.style.display = "none";
  }
}

// ── Merge Selection ──
const mergeBar = document.getElementById("mergeBar");
const mergeCount = document.getElementById("mergeCount");
const btnMerge = document.getElementById("btnMerge");
let mergeSelected = []; // ordered list of filenames

function updateMergeBar() {
  if (mergeSelected.length >= 2) {
    mergeBar.style.display = "flex";
    mergeCount.textContent = `${mergeSelected.length}本選択中（クリック順に結合）`;
  } else {
    mergeBar.style.display = mergeSelected.length === 1 ? "flex" : "none";
    mergeCount.textContent = mergeSelected.length === 1 ? "1本選択中（もう1本以上選んでください）" : "";
  }
}

function toggleMergeSelect(filename, card) {
  const idx = mergeSelected.indexOf(filename);
  if (idx >= 0) {
    mergeSelected.splice(idx, 1);
    card.classList.remove("selected-for-merge");
    const badge = card.querySelector(".merge-order");
    if (badge) badge.remove();
  } else {
    mergeSelected.push(filename);
    card.classList.add("selected-for-merge");
    const badge = document.createElement("div");
    badge.className = "merge-order";
    badge.textContent = mergeSelected.length;
    card.insertBefore(badge, card.firstChild);
  }
  // Update all badge numbers
  document.querySelectorAll(".file-card").forEach((c) => {
    const fn = c.dataset.filename;
    const order = mergeSelected.indexOf(fn);
    const b = c.querySelector(".merge-order");
    if (b) b.textContent = order >= 0 ? order + 1 : "";
  });
  updateMergeBar();
}

btnMerge.addEventListener("click", async () => {
  if (mergeSelected.length < 2) return;
  btnMerge.disabled = true;
  btnMerge.textContent = "結合中...";

  try {
    const res = await fetch("/api/merge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filenames: mergeSelected }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    mergeSelected = [];
    updateMergeBar();
    loadFileList();
    alert(`結合完了！ ${data.count}本 → 1本（${data.size_mb}MB）`);
  } catch (err) {
    alert("結合エラー: " + err.message);
  } finally {
    btnMerge.disabled = false;
    btnMerge.textContent = "選択した動画を結合";
  }
});

function createFileCard(f) {
  const card = document.createElement("div");
  card.className = "file-card";
  card.dataset.filename = f.name;

  // Icon
  const iconDiv = document.createElement("div");
  iconDiv.className = "file-icon";
  iconDiv.innerHTML = icons.film;

  // Info
  const infoDiv = document.createElement("div");
  infoDiv.className = "file-info";
  const nameEl = document.createElement("div");
  nameEl.className = "file-name";
  nameEl.textContent = f.name;
  const sizeEl = document.createElement("div");
  sizeEl.className = "file-size";
  sizeEl.textContent = f.size_mb + " MB";
  infoDiv.appendChild(nameEl);
  infoDiv.appendChild(sizeEl);

  // Actions
  const actionsDiv = document.createElement("div");
  actionsDiv.className = "file-actions";

  // Open button
  const openBtn = document.createElement("button");
  openBtn.className = "btn-icon";
  openBtn.title = "開く";
  openBtn.innerHTML = icons.link;
  openBtn.addEventListener("click", () => window.open(f.url, "_blank"));

  // Download link
  const dlLink = document.createElement("a");
  dlLink.className = "btn-icon";
  dlLink.title = "ダウンロード";
  dlLink.href = f.url;
  dlLink.download = f.name;
  dlLink.innerHTML = icons.download;

  // Delete button
  const delBtn = document.createElement("button");
  delBtn.className = "btn-icon delete";
  delBtn.title = "削除";
  delBtn.innerHTML = icons.trash;
  delBtn.addEventListener("click", async (e) => {
    e.stopPropagation();
    if (!confirm("この動画を削除しますか？")) return;
    delBtn.disabled = true;
    try {
      const res = await fetch("/api/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: f.name }),
      });
      if (res.ok) loadFileList();
      else alert("削除に失敗しました");
    } catch {
      alert("削除に失敗しました");
    }
  });

  // Analyze button
  const analyzeBtn = document.createElement("button");
  analyzeBtn.className = "btn-icon";
  analyzeBtn.title = "解析";
  analyzeBtn.innerHTML = `<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`;
  analyzeBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    openAnalyze(f);
  });

  actionsDiv.appendChild(analyzeBtn);
  actionsDiv.appendChild(openBtn);
  actionsDiv.appendChild(dlLink);
  actionsDiv.appendChild(delBtn);

  // Click card to select for merge, double-click to analyze
  card.style.cursor = "pointer";
  card.addEventListener("click", (e) => {
    if (e.target.closest(".file-actions")) return; // don't trigger on action buttons
    toggleMergeSelect(f.name, card);
  });
  card.addEventListener("dblclick", (e) => {
    if (e.target.closest(".file-actions")) return;
    openAnalyze(f);
  });

  card.appendChild(iconDiv);
  card.appendChild(infoDiv);
  card.appendChild(actionsDiv);

  return card;
}

// ── Helpers ──
function createProgressItem(name, metaText, statusText) {
  const item = document.createElement("div");
  item.className = "progress-item";
  item.innerHTML = `
    <div class="progress-top">
      <div class="file-icon">${icons.film}</div>
      <div class="info">
        <span class="name">${name}</span>
        <span class="meta">${metaText}</span>
      </div>
      <span class="status status-uploading">${statusText}</span>
    </div>
    <div class="bar-wrap"><div class="bar"></div></div>
  `;
  return item;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function showSetupBannerIfNeeded(msg) {
  if (
    msg.includes("token") ||
    msg.includes("401") ||
    msg.includes("403") ||
    msg.includes("BLOB")
  ) {
    setupBanner.style.display = "block";
  }
}

// ── Analyze Modal ──
const analyzeModal = document.getElementById("analyzeModal");
const analyzeVideo = document.getElementById("analyzeVideo");
const analyzeGrid = document.getElementById("analyzeGrid");
const modalTitle = document.getElementById("modalTitle");
const modalClose = document.getElementById("modalClose");
const btnAnalyzeAll = document.getElementById("btnAnalyzeAll");
const reportSection = document.getElementById("reportSection");
const reportBody = document.getElementById("reportBody");
const btnCloseReport = document.getElementById("btnCloseReport");

modalClose.addEventListener("click", closeModal);
analyzeModal.addEventListener("click", (e) => {
  if (e.target === analyzeModal) closeModal();
});

function closeModal() {
  analyzeModal.classList.remove("open");
  analyzeVideo.pause();
  analyzeVideo.src = "";
}

function openAnalyze(file) {
  modalTitle.textContent = file.name;
  analyzeGrid.innerHTML = '<div class="analyze-loading">解析中...</div>';
  analyzeVideo.src = file.url;
  analyzeModal.classList.add("open");

  analyzeVideo.addEventListener("loadedmetadata", function onMeta() {
    analyzeVideo.removeEventListener("loadedmetadata", onMeta);
    const meta = extractMetadata(analyzeVideo, file);
    renderAnalysis(meta);
  });

  analyzeVideo.addEventListener("error", function onErr() {
    analyzeVideo.removeEventListener("error", onErr);
    analyzeGrid.innerHTML = '<div class="analyze-loading">この動画は解析できませんでした</div>';
  });
}

function extractMetadata(video, file) {
  const w = video.videoWidth;
  const h = video.videoHeight;
  const dur = video.duration;

  // Determine aspect ratio
  let aspect = "不明";
  let platform = [];
  if (w && h) {
    const ratio = w / h;
    if (Math.abs(ratio - 9 / 16) < 0.05) {
      aspect = "9:16 (縦)";
      platform.push("TikTok", "Reels", "Shorts");
    } else if (Math.abs(ratio - 16 / 9) < 0.05) {
      aspect = "16:9 (横)";
      platform.push("YouTube");
    } else if (Math.abs(ratio - 1) < 0.05) {
      aspect = "1:1 (正方形)";
      platform.push("Instagram Feed");
    } else if (Math.abs(ratio - 4 / 5) < 0.05) {
      aspect = "4:5";
      platform.push("Instagram Feed");
    } else {
      aspect = `${w}:${h}`;
    }
  }

  // Resolution class
  let quality = "不明";
  if (h >= 2160) quality = "4K";
  else if (h >= 1440) quality = "2K";
  else if (h >= 1080) quality = "Full HD";
  else if (h >= 720) quality = "HD";
  else if (h > 0) quality = "SD";

  return {
    width: w,
    height: h,
    duration: dur,
    durationStr: formatDuration(dur),
    aspect,
    quality,
    platform,
    sizeMB: file.size_mb,
    name: file.name,
    url: file.url,
  };
}

function renderAnalysis(meta) {
  analyzeGrid.innerHTML = "";
  const items = [
    { label: "解像度", value: `${meta.width} x ${meta.height}` },
    { label: "画質", value: meta.quality },
    { label: "尺", value: meta.durationStr },
    { label: "アスペクト比", value: meta.aspect },
    { label: "ファイルサイズ", value: meta.sizeMB + " MB" },
    {
      label: "適合プラットフォーム",
      value: meta.platform.length > 0 ? meta.platform.join(", ") : "カスタム",
      full: true,
    },
  ];

  for (const item of items) {
    const el = document.createElement("div");
    el.className = "analyze-item" + (item.full ? " full" : "");
    const labelEl = document.createElement("div");
    labelEl.className = "label";
    labelEl.textContent = item.label;
    const valEl = document.createElement("div");
    valEl.className = "value";
    valEl.textContent = item.value;
    el.appendChild(labelEl);
    el.appendChild(valEl);
    analyzeGrid.appendChild(el);
  }
}

// ── Batch Analysis Report ──
btnAnalyzeAll.addEventListener("click", async () => {
  closeModal();
  await generateReport();
});

btnCloseReport.addEventListener("click", () => {
  reportSection.style.display = "none";
});

async function generateReport() {
  reportSection.style.display = "block";
  reportBody.innerHTML = '<div class="analyze-loading">全素材を解析中...</div>';
  reportSection.scrollIntoView({ behavior: "smooth" });

  try {
    const res = await fetch("/api/files");
    const data = await res.json();
    if (!data.files || !data.files.length) {
      reportBody.innerHTML = '<div class="analyze-loading">素材がありません</div>';
      return;
    }

    const results = [];
    for (const f of data.files) {
      try {
        const meta = await analyzeVideoFromUrl(f);
        results.push(meta);
      } catch {
        results.push({
          name: f.name,
          sizeMB: f.size_mb,
          error: true,
        });
      }
    }

    renderReport(results);

    // Show pattern selection after analysis
    const validResults = results.filter((r) => !r.error);
    if (validResults.length > 0) {
      currentAnalysisResults = validResults;
      showPatternSelection();
    }
  } catch {
    reportBody.innerHTML = '<div class="analyze-loading">レポート生成に失敗しました</div>';
  }
}

function analyzeVideoFromUrl(file) {
  return new Promise((resolve, reject) => {
    const video = document.createElement("video");
    video.preload = "metadata";
    video.crossOrigin = "anonymous";
    video.muted = true;

    video.addEventListener("loadedmetadata", () => {
      resolve(extractMetadata(video, file));
      video.src = "";
    });
    video.addEventListener("error", () => {
      reject(new Error("Failed to load"));
    });

    video.src = file.url;
  });
}

function renderReport(results) {
  const valid = results.filter((r) => !r.error);
  const totalDuration = valid.reduce((s, r) => s + (r.duration || 0), 0);
  const totalSize = results.reduce((s, r) => s + (r.sizeMB || 0), 0);

  reportBody.innerHTML = "";

  // Summary
  const summary = document.createElement("div");
  summary.className = "report-summary";
  summary.innerHTML = `
    <div class="report-summary-grid">
      <div class="report-summary-item">
        <div class="num">${results.length}</div>
        <div class="label">素材数</div>
      </div>
      <div class="report-summary-item">
        <div class="num">${formatDuration(totalDuration)}</div>
        <div class="label">合計尺</div>
      </div>
      <div class="report-summary-item">
        <div class="num">${totalSize.toFixed(1)} MB</div>
        <div class="label">合計サイズ</div>
      </div>
    </div>
  `;
  reportBody.appendChild(summary);

  // Each file
  for (const r of results) {
    const card = document.createElement("div");
    card.className = "report-card";

    const header = document.createElement("div");
    header.className = "report-card-header";
    const nameEl = document.createElement("span");
    nameEl.className = "name";
    nameEl.textContent = r.name;
    header.appendChild(nameEl);

    card.appendChild(header);

    if (r.error) {
      const tag = document.createElement("span");
      tag.className = "report-tag warn";
      tag.textContent = "解析不可";
      header.appendChild(tag);
    } else {
      const metaDiv = document.createElement("div");
      metaDiv.className = "report-meta";

      const tags = [
        { text: `${r.width}x${r.height}`, cls: r.height >= 1080 ? "good" : "" },
        { text: r.quality, cls: r.quality === "Full HD" || r.quality === "4K" ? "good" : "" },
        { text: r.durationStr, cls: "" },
        { text: r.aspect, cls: "" },
        { text: r.sizeMB + " MB", cls: "" },
      ];

      if (r.platform.length > 0) {
        tags.push({ text: r.platform.join(" / "), cls: "good" });
      }

      for (const t of tags) {
        const tag = document.createElement("span");
        tag.className = "report-tag" + (t.cls ? " " + t.cls : "");
        tag.textContent = t.text;
        metaDiv.appendChild(tag);
      }

      card.appendChild(metaDiv);
    }

    reportBody.appendChild(card);
  }
}

function formatDuration(seconds) {
  if (!seconds || !isFinite(seconds)) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return m + ":" + s.toString().padStart(2, "0");
}

// ── Pattern Selection (STEP 2) ──
const patternSection = document.getElementById("patternSection");
const platformSelect = document.getElementById("platformSelect");
const genreSelect = document.getElementById("genreSelect");
const refVideoUrl = document.getElementById("refVideoUrl");
const btnAnalyzeRef = document.getElementById("btnAnalyzeRef");
const refResult = document.getElementById("refResult");
const patternListBlock = document.getElementById("patternListBlock");
const patternList = document.getElementById("patternList");
const patternDesc = document.getElementById("patternDesc");

let selectedPlatform = "tiktok";
let selectedGenre = null;
let refVideoDuration = null;

function showPatternSelection() {
  patternSection.style.display = "block";
  patternSection.scrollIntoView({ behavior: "smooth" });

  // Render platform buttons
  const platforms = [
    { id: "tiktok", name: "TikTok" },
    { id: "reels", name: "Reels" },
    { id: "shorts", name: "Shorts" },
    { id: "youtube", name: "YouTube" },
  ];
  platformSelect.innerHTML = "";
  for (const p of platforms) {
    const btn = document.createElement("button");
    btn.className = "platform-btn" + (p.id === selectedPlatform ? " active" : "");
    btn.textContent = p.name;
    btn.addEventListener("click", () => {
      selectedPlatform = p.id;
      platformSelect.querySelectorAll(".platform-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      if (selectedGenre) showPatterns();
    });
    platformSelect.appendChild(btn);
  }

  // Render genre buttons
  genreSelect.innerHTML = "";
  for (const g of GENRES) {
    const btn = document.createElement("button");
    btn.className = "genre-btn";
    btn.textContent = `${g.icon} ${g.name}`;
    btn.addEventListener("click", () => {
      selectedGenre = g.id;
      genreSelect.querySelectorAll(".genre-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      showPatterns();
    });
    genreSelect.appendChild(btn);
  }
}

// Reference video analysis
btnAnalyzeRef.addEventListener("click", async () => {
  const url = refVideoUrl.value.trim();
  if (!url) return;

  btnAnalyzeRef.disabled = true;
  btnAnalyzeRef.textContent = "解析中...";
  refResult.style.display = "none";
  refVideoDuration = null;

  try {
    const duration = await analyzeReferenceVideo(url);
    refVideoDuration = duration;
    refResult.style.display = "block";
    refResult.innerHTML = `
      <span class="ref-tag">参考動画</span>
      尺: ${formatDuration(duration)} — この尺に合わせてパターンを調整します
    `;
    if (selectedGenre) showPatterns();
  } catch {
    refResult.style.display = "block";
    refResult.textContent = "この動画は直接解析できません。尺だけ手動入力もできます。";
  } finally {
    btnAnalyzeRef.disabled = false;
    btnAnalyzeRef.textContent = "解析";
  }
});

function analyzeReferenceVideo(url) {
  return new Promise((resolve, reject) => {
    const video = document.createElement("video");
    video.preload = "metadata";
    video.crossOrigin = "anonymous";
    video.muted = true;
    video.addEventListener("loadedmetadata", () => {
      resolve(video.duration);
      video.src = "";
    });
    video.addEventListener("error", () => reject(new Error("Load failed")));
    video.src = url;
  });
}

function showPatterns() {
  const genre = GENRES.find((g) => g.id === selectedGenre);
  if (!genre) return;

  patternListBlock.style.display = "block";
  patternDesc.textContent = `${genre.icon} ${genre.name} のバズパターン（${genre.patterns.length}種類）`;

  patternList.innerHTML = "";
  for (const pattern of genre.patterns) {
    let concept = buildConceptFromPattern(
      selectedGenre,
      pattern.id,
      currentAnalysisResults || [],
      selectedPlatform
    );
    if (!concept) continue;

    // Adjust by reference video duration
    if (refVideoDuration) {
      concept = adjustPatternByReference(concept, refVideoDuration);
    }

    const card = createConceptCard(concept);

    // Add tips section
    if (concept.tips && concept.tips.length > 0) {
      const tipsDiv = document.createElement("div");
      tipsDiv.className = "concept-tips";
      const tipsTitle = document.createElement("div");
      tipsTitle.className = "concept-tips-title";
      tipsTitle.textContent = "バズるためのポイント";
      tipsDiv.appendChild(tipsTitle);
      const ul = document.createElement("ul");
      for (const tip of concept.tips) {
        const li = document.createElement("li");
        li.textContent = tip;
        ul.appendChild(li);
      }
      tipsDiv.appendChild(ul);
      // Insert before approve button
      const approveRow = card.querySelector(".concept-approve-row");
      card.insertBefore(tipsDiv, approveRow);
    }

    patternList.appendChild(card);
  }

  patternListBlock.scrollIntoView({ behavior: "smooth" });
}

// ── Concept Proposal ──
const conceptSection = document.getElementById("conceptSection");
const conceptGrid = document.getElementById("conceptGrid");
const conceptStatus = document.getElementById("conceptStatus");
const approvedSection = document.getElementById("approvedSection");
const approvedBanner = document.getElementById("approvedBanner");

let currentAnalysisResults = null;
let approvedConcept = null;

const conceptIcons = {
  zap: `<svg viewBox="0 0 24 24"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`,
  book: `<svg viewBox="0 0 24 24"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>`,
  star: `<svg viewBox="0 0 24 24"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
  film: `<svg viewBox="0 0 24 24"><rect x="2" y="2" width="20" height="20" rx="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/></svg>`,
  repeat: `<svg viewBox="0 0 24 24"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>`,
};

async function showConceptProposals(analysisResults) {
  currentAnalysisResults = analysisResults;
  const concepts = generateConcepts(analysisResults);

  if (concepts.length === 0) {
    conceptSection.style.display = "none";
    return;
  }

  conceptSection.style.display = "block";
  conceptStatus.textContent = concepts.length + " プラン";
  conceptStatus.style.display = "inline-flex";
  approvedSection.style.display = "none";
  approvedConcept = null;

  conceptGrid.innerHTML = "";
  for (const concept of concepts) {
    conceptGrid.appendChild(createConceptCard(concept));
  }

  conceptSection.scrollIntoView({ behavior: "smooth" });
}

function createConceptCard(concept) {
  const card = document.createElement("div");
  card.className = "concept-card";

  // Header
  const header = document.createElement("div");
  header.className = "concept-card-header";

  const iconDiv = document.createElement("div");
  iconDiv.className = "concept-icon";
  iconDiv.innerHTML = conceptIcons[concept.styleIcon] || conceptIcons.film;

  const titleArea = document.createElement("div");
  titleArea.className = "concept-title-area";
  const title = document.createElement("div");
  title.className = "concept-title";
  title.textContent = concept.styleName;
  const platform = document.createElement("div");
  platform.className = "concept-platform";
  platform.textContent = concept.platform;
  titleArea.appendChild(title);
  titleArea.appendChild(platform);

  header.appendChild(iconDiv);
  header.appendChild(titleArea);
  card.appendChild(header);

  // Description
  const desc = document.createElement("div");
  desc.className = "concept-desc";
  desc.textContent = concept.styleDescription;
  card.appendChild(desc);

  // Specs
  const specs = document.createElement("div");
  specs.className = "concept-specs";
  const specItems = [
    `尺: ${concept.targetDurationStr}`,
    `${concept.clipCount}/${concept.totalClips} クリップ使用`,
    concept.resolution,
    concept.aspect,
    `トランジション: ${concept.transition}`,
  ];
  for (const text of specItems) {
    const tag = document.createElement("span");
    tag.className = "concept-spec";
    tag.textContent = text;
    specs.appendChild(tag);
  }
  card.appendChild(specs);

  // Structure
  const structDiv = document.createElement("div");
  structDiv.className = "concept-structure";
  const structTitle = document.createElement("div");
  structTitle.className = "concept-structure-title";
  structTitle.textContent = "構成";
  structDiv.appendChild(structTitle);

  for (const step of concept.structure) {
    const stepEl = document.createElement("div");
    stepEl.className = "structure-step";
    const dot = document.createElement("div");
    dot.className = "structure-dot";
    const info = document.createElement("div");
    info.className = "structure-info";
    const name = document.createElement("div");
    name.className = "structure-name";
    name.textContent = `${step.name}（${step.duration}）`;
    const detail = document.createElement("div");
    detail.className = "structure-detail";
    detail.textContent = step.note;
    info.appendChild(name);
    info.appendChild(detail);
    stepEl.appendChild(dot);
    stepEl.appendChild(info);
    structDiv.appendChild(stepEl);
  }
  card.appendChild(structDiv);

  // Approve button
  const approveRow = document.createElement("div");
  approveRow.className = "concept-approve-row";
  const approveBtn = document.createElement("button");
  approveBtn.className = "btn-approve";
  approveBtn.textContent = "このコンセプトで進める";
  approveBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    approveConcept(concept);
  });
  approveRow.appendChild(approveBtn);
  card.appendChild(approveRow);

  // Click card to select (visual)
  card.addEventListener("click", () => {
    document.querySelectorAll(".concept-card").forEach((c) => c.classList.remove("selected"));
    card.classList.add("selected");
  });

  return card;
}

function approveConcept(concept) {
  approvedConcept = concept;

  // Hide concept grid, show approved banner
  conceptSection.style.display = "none";

  approvedSection.style.display = "block";
  approvedBanner.innerHTML = "";

  const header = document.createElement("div");
  header.className = "approved-header";
  const check = document.createElement("div");
  check.className = "approved-check";
  check.innerHTML = `<svg viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>`;
  const title = document.createElement("div");
  title.className = "approved-title";
  title.textContent = "コンセプト承認済み";
  header.appendChild(check);
  header.appendChild(title);
  approvedBanner.appendChild(header);

  const detail = document.createElement("div");
  detail.className = "approved-detail";
  detail.innerHTML = `
    <strong>${escapeHtml(concept.styleName)}</strong> / ${escapeHtml(concept.platform)}<br>
    尺: ${escapeHtml(concept.targetDurationStr)} / ${concept.clipCount}クリップ使用 / ${escapeHtml(concept.resolution)} (${escapeHtml(concept.aspect)})<br>
    トランジション: ${escapeHtml(concept.transition)}
  `;
  approvedBanner.appendChild(detail);

  const actions = document.createElement("div");
  actions.className = "approved-actions";

  const nextBtn = document.createElement("button");
  nextBtn.className = "btn-next";
  nextBtn.textContent = "編集に進む";
  nextBtn.addEventListener("click", () => openEditor(concept));
  actions.appendChild(nextBtn);

  const reselectBtn = document.createElement("button");
  reselectBtn.className = "btn-reselect";
  reselectBtn.textContent = "コンセプトを選び直す";
  reselectBtn.addEventListener("click", () => {
    approvedSection.style.display = "none";
    approvedConcept = null;
    showConceptProposals(currentAnalysisResults);
  });
  actions.appendChild(reselectBtn);

  approvedBanner.appendChild(actions);
  approvedSection.scrollIntoView({ behavior: "smooth" });
}

// ── Editor Section ──
const editorSection = document.getElementById("editorSection");
const editorPreview = document.getElementById("editorPreview");
const trimStart = document.getElementById("trimStart");
const trimEnd = document.getElementById("trimEnd");
const subtitleList = document.getElementById("subtitleList");
const btnAddSubtitle = document.getElementById("btnAddSubtitle");
const btnExport = document.getElementById("btnExport");
const exportProgress = document.getElementById("exportProgress");
const exportBar = document.getElementById("exportBar");
const exportStatus = document.getElementById("exportStatus");
const exportInfo = document.getElementById("exportInfo");
const downloadBlock = document.getElementById("downloadBlock");
const btnDownload = document.getElementById("btnDownload");

let editorConcept = null;
let subtitleCounter = 0;

function openEditor(concept) {
  editorConcept = concept;
  editorSection.style.display = "block";
  downloadBlock.style.display = "none";
  exportProgress.style.display = "none";
  btnExport.disabled = false;

  // Load first material into preview
  const firstMaterial = concept.materials[0];
  if (firstMaterial) {
    editorPreview.src = firstMaterial.url;
    editorPreview.addEventListener("loadedmetadata", function onMeta() {
      editorPreview.removeEventListener("loadedmetadata", onMeta);
      trimStart.value = concept.structure[0] ? 0 : 0;
      trimEnd.value = Math.min(
        editorPreview.duration,
        concept.targetDuration
      ).toFixed(1);
      trimEnd.max = editorPreview.duration.toFixed(1);
      trimStart.max = editorPreview.duration.toFixed(1);
    });
  }

  // Export info
  const platformSpec = PLATFORM_SPECS[concept.platformId];
  exportInfo.textContent =
    `${concept.platform} / ${platformSpec.resolution.w}x${platformSpec.resolution.h} ` +
    `(${concept.aspect}) / 無音 / MP4`;

  // Pre-fill subtitles from pattern structure
  subtitleList.innerHTML = "";
  subtitleCounter = 0;
  if (concept.rawStructure && concept.rawStructure.length > 0) {
    for (const step of concept.rawStructure) {
      addSubtitleRow(
        step.note || step.name,
        step.start,
        step.end,
        step.position || "bottom"
      );
    }
  } else {
    addSubtitleRow("", 0, concept.targetDuration, "bottom");
  }

  editorSection.scrollIntoView({ behavior: "smooth" });
}

// Add subtitle
btnAddSubtitle.addEventListener("click", () => {
  const end = parseFloat(trimEnd.value) || 10;
  addSubtitleRow("", 0, end, "bottom");
});

function addSubtitleRow(text, start, end, position) {
  const id = "sub-" + subtitleCounter++;
  const row = document.createElement("div");
  row.className = "subtitle-row";
  row.id = id;

  const textInput = document.createElement("textarea");
  textInput.className = "sub-text";
  textInput.placeholder = "テロップのテキスト";
  textInput.value = text;
  textInput.rows = 1;

  const startInput = document.createElement("input");
  startInput.className = "sub-time";
  startInput.type = "number";
  startInput.step = "0.1";
  startInput.min = "0";
  startInput.value = start;
  startInput.title = "開始(秒)";

  const endInput = document.createElement("input");
  endInput.className = "sub-time";
  endInput.type = "number";
  endInput.step = "0.1";
  endInput.min = "0";
  endInput.value = end;
  endInput.title = "終了(秒)";

  const posSelect = document.createElement("select");
  posSelect.className = "sub-pos";
  for (const [val, label] of [["bottom", "下"], ["center", "中"], ["top", "上"]]) {
    const opt = document.createElement("option");
    opt.value = val;
    opt.textContent = label;
    if (val === position) opt.selected = true;
    posSelect.appendChild(opt);
  }

  const removeBtn = document.createElement("button");
  removeBtn.className = "btn-sub-remove";
  removeBtn.textContent = "\u00d7";
  removeBtn.addEventListener("click", () => row.remove());

  row.appendChild(textInput);
  row.appendChild(startInput);
  row.appendChild(endInput);
  row.appendChild(posSelect);
  row.appendChild(removeBtn);
  subtitleList.appendChild(row);
}

// ── Auto Subtitle Generation ──
const btnAutoSubtitle = document.getElementById("btnAutoSubtitle");
const autoSubProgress = document.getElementById("autoSubProgress");
const autoSubBar = document.getElementById("autoSubBar");
const autoSubStatus = document.getElementById("autoSubStatus");
const btnDownloadSRT = document.getElementById("btnDownloadSRT");

let currentSubtitles = [];

btnAutoSubtitle.addEventListener("click", async () => {
  if (!editorConcept || !editorConcept.materials[0]) return;

  btnAutoSubtitle.disabled = true;
  autoSubProgress.style.display = "block";
  autoSubBar.style.width = "20%";
  autoSubStatus.textContent = "音声を文字起こし中...（数十秒かかります）";

  const progressTimer = setInterval(() => {
    const w = parseFloat(autoSubBar.style.width);
    if (w < 85) autoSubBar.style.width = w + 3 + "%";
  }, 1000);

  try {
    const res = await fetch("/api/transcribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: editorConcept.materials[0].name }),
    });

    clearInterval(progressTimer);
    const data = await res.json();

    if (!res.ok) throw new Error(data.error || "文字起こしに失敗しました");

    autoSubBar.style.width = "90%";
    autoSubStatus.textContent = "テロップを生成中...";

    // Generate subtitles from Whisper segments
    const subtitles = generateSubtitles(data.segments || []);
    currentSubtitles = subtitles;

    // Fill subtitle list
    subtitleList.innerHTML = "";
    subtitleCounter = 0;
    for (const sub of subtitles) {
      const text = sub.lines ? sub.lines.join("\n") : sub.text;
      addSubtitleRow(text, sub.startTime, sub.endTime, sub.position || "bottom");
    }

    autoSubBar.style.width = "100%";
    autoSubBar.classList.add("bar-done");
    autoSubStatus.textContent = `完了！${subtitles.length}件のテロップを生成しました`;
  } catch (err) {
    clearInterval(progressTimer);
    autoSubBar.style.width = "100%";
    autoSubBar.style.background = "var(--red)";
    autoSubStatus.textContent = "エラー: " + err.message;
  } finally {
    btnAutoSubtitle.disabled = false;
  }
});

// SRT Download
btnDownloadSRT.addEventListener("click", () => {
  // Gather current subtitles from UI
  const subs = [];
  subtitleList.querySelectorAll(".subtitle-row").forEach((row) => {
    const text = row.querySelector(".sub-text").value.trim();
    if (!text) return;
    subs.push({
      text,
      lines: text.split("\n"),
      startTime: parseFloat(row.querySelectorAll(".sub-time")[0].value) || 0,
      endTime: parseFloat(row.querySelectorAll(".sub-time")[1].value) || 0,
    });
  });

  if (subs.length === 0) {
    alert("テロップがありません。先に自動字幕生成を実行してください。");
    return;
  }

  const srt = exportSRT(subs);
  const blob = new Blob([srt], { type: "text/srt;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `subtitles_${Date.now()}.srt`;
  a.click();
  URL.revokeObjectURL(url);
});

// Export via Cloudinary API
btnExport.addEventListener("click", async () => {
  if (!editorConcept) return;

  btnExport.disabled = true;
  exportProgress.style.display = "block";
  downloadBlock.style.display = "none";
  exportBar.style.width = "10%";
  exportBar.classList.remove("bar-done");
  exportBar.style.background = "";
  exportStatus.textContent = "サーバーで動画を処理中...";

  // Gather subtitles
  const subtitles = [];
  subtitleList.querySelectorAll(".subtitle-row").forEach((row) => {
    const text = row.querySelector(".sub-text").value.trim();
    if (!text) return;
    subtitles.push({
      text,
      startTime: parseFloat(row.querySelectorAll(".sub-time")[0].value) || 0,
      endTime: parseFloat(row.querySelectorAll(".sub-time")[1].value) || 10,
      position: row.querySelector(".sub-pos").value,
    });
  });

  const platformSpec = PLATFORM_SPECS[editorConcept.platformId];
  const firstMaterial = editorConcept.materials[0];

  // Animated progress bar
  exportBar.style.width = "30%";
  const progressTimer = setInterval(() => {
    const w = parseFloat(exportBar.style.width);
    if (w < 85) exportBar.style.width = w + 3 + "%";
  }, 800);

  try {
    const res = await fetch("/api/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: firstMaterial.name,
        width: platformSpec.resolution.w,
        height: platformSpec.resolution.h,
        startTime: parseFloat(trimStart.value) || 0,
        endTime: parseFloat(trimEnd.value) || null,
        subtitles,
      }),
    });

    clearInterval(progressTimer);
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || "書き出しに失敗しました");
    }

    // Set download link to Cloudinary URL
    const fileName = `${editorConcept.platform.replace(/\s/g, "_")}_${Date.now()}.mp4`;
    btnDownload.href = data.url;
    btnDownload.download = fileName;
    downloadBlock.style.display = "block";
    exportBar.style.width = "100%";
    exportBar.classList.add("bar-done");

    const sizeMB = data.bytes ? (data.bytes / 1024 / 1024).toFixed(1) + " MB" : "";
    exportStatus.textContent = `完了！${sizeMB}`;
  } catch (err) {
    clearInterval(progressTimer);
    exportStatus.textContent = "エラー: " + (err.message || "書き出しに失敗しました");
    exportBar.style.background = "var(--red)";
    exportBar.style.width = "100%";
  } finally {
    btnExport.disabled = false;
  }
});

// ── Init ──
loadFileList();
