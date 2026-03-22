import { upload } from "@vercel/blob/client";
import "./style.css";

// ── DOM Elements ──
const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const progressList = document.getElementById("progressList");
const fileGrid = document.getElementById("fileGrid");
const fileCountBadge = document.getElementById("fileCount");
const setupBanner = document.getElementById("setupBanner");

// ── SVG Icons ──
const icons = {
  film: `<svg viewBox="0 0 24 24"><rect x="2" y="2" width="20" height="20" rx="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="2" y1="17" x2="7" y2="17"/><line x1="17" y1="17" x2="22" y2="17"/><line x1="17" y1="7" x2="22" y2="7"/></svg>`,
  upload: `<svg viewBox="0 0 24 24"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>`,
  download: `<svg viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>`,
  trash: `<svg viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>`,
  link: `<svg viewBox="0 0 24 24"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>`,
};

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

// ── Upload ──
async function uploadFile(file) {
  const id = "upload-" + Date.now() + Math.random().toString(36).slice(2, 6);
  const sizeMB = (file.size / 1024 / 1024).toFixed(1);

  const item = document.createElement("div");
  item.className = "progress-item";
  item.id = id;
  item.innerHTML = `
    <div class="progress-top">
      <div class="file-icon">${icons.film}</div>
      <div class="info">
        <span class="name">${escapeHtml(file.name)}</span>
        <span class="meta">${sizeMB} MB</span>
      </div>
      <span class="status status-uploading">アップロード中...</span>
    </div>
    <div class="bar-wrap"><div class="bar"></div></div>
  `;
  progressList.prepend(item);

  const bar = item.querySelector(".bar");
  const status = item.querySelector(".status");

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
    item.querySelector(".meta").textContent = sizeMB + " MB - " + msg;

    // Show setup hint if it looks like a config issue
    if (
      msg.includes("token") ||
      msg.includes("401") ||
      msg.includes("403") ||
      msg.includes("BLOB")
    ) {
      setupBanner.style.display = "block";
    }
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

    fileGrid.innerHTML = data.files
      .map(
        (f) => `
      <div class="file-card" data-url="${escapeHtml(f.url)}">
        <div class="file-icon">${icons.film}</div>
        <div class="file-info">
          <div class="file-name">${escapeHtml(f.name)}</div>
          <div class="file-size">${f.size_mb} MB</div>
        </div>
        <div class="file-actions">
          <button class="btn-icon" title="開く" onclick="window.open('${escapeHtml(f.url)}','_blank')">${icons.link}</button>
          <a class="btn-icon" title="ダウンロード" href="${escapeHtml(f.url)}" download="${escapeHtml(f.name)}">${icons.download}</a>
          <button class="btn-icon delete" title="削除" data-delete-url="${escapeHtml(f.url)}">${icons.trash}</button>
        </div>
      </div>
    `
      )
      .join("");

    // Delete handlers
    fileGrid.querySelectorAll("[data-delete-url]").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const url = btn.dataset.deleteUrl;
        if (!confirm("この動画を削除しますか？")) return;
        btn.disabled = true;
        try {
          const res = await fetch("/api/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url }),
          });
          if (res.ok) loadFileList();
          else alert("削除に失敗しました");
        } catch {
          alert("削除に失敗しました");
        }
      });
    });
  } catch {
    fileGrid.innerHTML =
      '<div class="empty-state">まだ動画がアップロードされていません</div>';
    fileCountBadge.style.display = "none";
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ── Init ──
loadFileList();
