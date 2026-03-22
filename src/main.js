import { upload } from "@vercel/blob/client";
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

function createFileCard(f) {
  const card = document.createElement("div");
  card.className = "file-card";

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
        body: JSON.stringify({ url: f.url }),
      });
      if (res.ok) loadFileList();
      else alert("削除に失敗しました");
    } catch {
      alert("削除に失敗しました");
    }
  });

  actionsDiv.appendChild(openBtn);
  actionsDiv.appendChild(dlLink);
  actionsDiv.appendChild(delBtn);

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

// ── Init ──
loadFileList();
