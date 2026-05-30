import "./style.css";

// ── Navigation ──
const navItems = document.querySelectorAll(".nav-item");
const pages = document.querySelectorAll(".page");

function switchPage(pageId) {
  navItems.forEach((n) => n.classList.remove("active"));
  pages.forEach((p) => p.classList.remove("active"));
  const nav = document.querySelector(`[data-page="${pageId}"]`);
  const page = document.getElementById(`page-${pageId}`);
  if (nav) nav.classList.add("active");
  if (page) page.classList.add("active");
}
window.switchPage = switchPage;

navItems.forEach((item) => {
  item.addEventListener("click", () => switchPage(item.dataset.page));
});

// ── Upload ──
const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const uploadProgress = document.getElementById("uploadProgress");

if (dropZone) {
  dropZone.addEventListener("click", () => fileInput.click());
  dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("dragover"); });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    for (const file of e.dataTransfer.files) uploadFile(file);
  });
  fileInput.addEventListener("change", () => {
    for (const file of fileInput.files) uploadFile(file);
    fileInput.value = "";
  });
}

async function uploadFile(file) {
  const item = document.createElement("div");
  item.className = "progress-item";
  item.innerHTML = `
    <div class="progress-top">
      <span class="name">${esc(file.name)}</span>
      <span class="status status-uploading">アップロード中...</span>
    </div>
    <div class="bar-wrap"><div class="bar"></div></div>
  `;
  uploadProgress.prepend(item);
  const bar = item.querySelector(".bar");
  const status = item.querySelector(".status");

  try {
    const fd = new FormData();
    fd.append("files", file);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/upload");
    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) bar.style.width = Math.round((e.loaded / e.total) * 100) + "%";
    });
    await new Promise((resolve, reject) => {
      xhr.onload = () => xhr.status < 300 ? resolve() : reject(new Error("Upload failed"));
      xhr.onerror = () => reject(new Error("Network error"));
      xhr.send(fd);
    });
    status.textContent = "完了";
    status.className = "status status-done";
    bar.style.width = "100%";
    bar.classList.add("bar-done");
    loadFiles();
  } catch (err) {
    status.textContent = "エラー";
    status.className = "status status-error";
  }
}

// ── File List ──
async function loadFiles() {
  try {
    const res = await fetch("/api/files");
    const data = await res.json();
    const files = data.files || [];

    document.getElementById("stat-materials").textContent = files.length;

    const fileList = document.getElementById("fileList");
    const recentFiles = document.getElementById("recent-files");

    if (!files.length) {
      if (fileList) fileList.innerHTML = '<p style="color:var(--muted);font-size:0.85rem">まだファイルがありません</p>';
      if (recentFiles) recentFiles.innerHTML = '<p style="color:var(--muted);font-size:0.85rem">まだファイルがありません</p>';
      return;
    }

    const html = files.map((f) => `
      <div class="file-item">
        <span class="file-name">${esc(f.name)}</span>
        <span class="file-size">${f.size_mb} MB</span>
      </div>
    `).join("");

    if (fileList) fileList.innerHTML = html;
    if (recentFiles) recentFiles.innerHTML = files.slice(0, 5).map((f) => `
      <div class="file-item">
        <span class="file-name">${esc(f.name)}</span>
        <span class="file-size">${f.size_mb} MB</span>
      </div>
    `).join("");
  } catch {
    // API unavailable
  }
}

// ── Outputs (完成動画) ──
async function loadOutputs() {
  try {
    const res = await fetch("/api/outputs");
    const data = await res.json();
    const el = document.getElementById("stat-outputs");
    if (el) el.textContent = (data.files || []).length;
  } catch {
    // API unavailable
  }
}

// ── Clients ──
const GENRE_LABELS = {
  beauty: "美容・コスメ", food: "料理・グルメ", travel: "旅行・Vlog",
  fitness: "筋トレ", business: "ビジネス", lifestyle: "ライフスタイル",
  education: "教育・解説", product: "商品紹介",
};

async function loadClients() {
  try {
    const res = await fetch("/api/clients");
    const data = await res.json();
    const clients = data.clients || [];

    const stat = document.getElementById("stat-clients");
    if (stat) stat.textContent = clients.length;

    const list = document.getElementById("clientList");
    if (!list) return;
    if (!clients.length) {
      list.innerHTML = '<p style="color:var(--muted);font-size:0.85rem">クライアントが登録されていません。<br>CLI: <code>python scripts/client.py create</code></p>';
      return;
    }
    list.innerHTML = `
      <table class="data-table">
        <thead><tr><th>ID</th><th>名前</th><th>ジャンル</th><th>素材</th></tr></thead>
        <tbody>
          ${clients.map((c) => `
            <tr>
              <td>${esc(c.id)}</td>
              <td><strong>${esc(c.name)}</strong></td>
              <td>${esc(GENRE_LABELS[c.genre] || c.genre || "—")}</td>
              <td>${c.video_count}本</td>
            </tr>
          `).join("")}
        </tbody>
      </table>`;
  } catch {
    const list = document.getElementById("clientList");
    if (list) list.innerHTML = '<p style="color:var(--muted);font-size:0.85rem">読み込みに失敗しました</p>';
  }
}

// ── Hypothesis Board ──
const hypotheses = [
  { id: "hygiene", name: "清潔感", insight: "清潔感は顔じゃなくて手入れで決まる", keywords: "清潔感, 手入れ, 身だしなみ" },
  { id: "aging_anxiety", name: "加齢不安", insight: "30代で肌が変わる。気づいた時がスタート", keywords: "老化, 肌, 30代" },
  { id: "confidence", name: "自信", insight: "自信は整えた先にある", keywords: "自信, 自己肯定, 変わりたい" },
  { id: "presence", name: "第一印象", insight: "印象は3秒で決まる。整え方で変わる", keywords: "第一印象, 見た目, 3秒" },
  { id: "recovery_story", name: "回復体験", insight: "過去の自分と向き合った記録", keywords: "体験談, 回復, 変化" },
  { id: "loneliness", name: "孤独", insight: "誰にも言えない悩みがある。それでいい", keywords: "孤独, 悩み, 一人" },
  { id: "self_investment", name: "自己投資", insight: "毎朝5分の投資が、1年後の自分を変える", keywords: "自己投資, 習慣, ルーティン" },
  { id: "conditioning", name: "コンディション", insight: "整えるのは見た目じゃなくて、体調から", keywords: "体調, 睡眠, 疲労" },
];

function renderHypotheses() {
  const body = document.getElementById("hypothesisBody");
  if (!body) return;
  body.innerHTML = hypotheses.map((h, i) => `
    <tr>
      <td>${i + 1}</td>
      <td><strong>${h.name}</strong></td>
      <td>${h.insight}</td>
      <td style="color:var(--dim);font-size:0.78rem">${h.keywords}</td>
    </tr>
  `).join("");
}

// ── Script Generator ──
const btnScript = document.getElementById("btnGenerateScript");
if (btnScript) {
  btnScript.addEventListener("click", async () => {
    const theme = document.getElementById("scriptTheme").value.trim();
    const style = document.getElementById("scriptStyle").value;
    if (!theme) return;

    btnScript.disabled = true;
    btnScript.textContent = "生成中...";
    const result = document.getElementById("scriptResult");
    result.innerHTML = '<div class="result-block">台本を生成中...</div>';

    try {
      const res = await fetch("/api/script", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ theme, style }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      const parts = (data.parts || []).map((p) =>
        `[${p.time}] ${p.part_name}\n  セリフ: 「${p.serif}」\n  テロップ: 【${p.telop || "—"}】\n  カメラ: ${p.camera}`
      ).join("\n\n");

      result.innerHTML = `<div class="result-block success">
台本: ${data.title || theme}
尺: ${data.total_duration || "?"}秒

${parts}

投稿キャプション:
${data.post_caption || ""}

ハッシュタグ:
${(data.hashtags || []).join(" ")}
</div>`;
    } catch (err) {
      result.innerHTML = `<div class="result-block error">${err.message}</div>`;
    } finally {
      btnScript.disabled = false;
      btnScript.textContent = "台本を生成";
    }
  });
}

// ── Reel Generator ──
const btnReel = document.getElementById("btnGenerateReel");
if (btnReel) {
  btnReel.addEventListener("click", async () => {
    const hypothesis = document.getElementById("reelHypothesis").value;
    const type = document.getElementById("reelType").value;

    btnReel.disabled = true;
    btnReel.textContent = "生成中...";
    const result = document.getElementById("reelResult");
    result.innerHTML = '<div class="result-block">スクリプト→リール生成中...</div>';

    try {
      const res = await fetch("/api/reel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hypothesis, type }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      result.innerHTML = `<div class="result-block success">
リール生成完了!

型: ${data.type || type}
仮説: ${hypothesis}

${data.text ? `テキスト: 「${data.text}」` : ""}
${data.texts ? data.texts.map((t, i) => `  [${i + 1}] ${t}`).join("\n") : ""}

BGM: ${data.mood || "—"}
ビジュアル: ${data.visual_note || "—"}

${data.output ? `出力: ${data.output}` : ""}
${data.render_note ? `※ ${data.render_note}` : ""}
</div>`;
    } catch (err) {
      result.innerHTML = `<div class="result-block error">${err.message}</div>`;
    } finally {
      btnReel.disabled = false;
      btnReel.textContent = "スクリプト→リール生成";
    }
  });
}

// ── Helpers ──
function esc(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ── Init ──
loadFiles();
loadOutputs();
loadClients();
renderHypotheses();
