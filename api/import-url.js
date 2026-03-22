import { put } from "@vercel/blob";

export const config = {
  api: { bodyParser: { sizeLimit: "1mb" } },
};

const VIDEO_EXTENSIONS = [".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"];
const MAX_SIZE = 500 * 1024 * 1024; // 500MB

export default async function handler(request, response) {
  if (request.method !== "POST") {
    return response.status(405).json({ error: "Method not allowed" });
  }

  const { url } = request.body || {};
  if (!url || typeof url !== "string") {
    return response
      .status(400)
      .json({ error: "URLを入力してください" });
  }

  // Validate URL format
  let parsedUrl;
  try {
    parsedUrl = new URL(url);
  } catch {
    return response
      .status(400)
      .json({ error: "無効なURLです" });
  }

  if (!["http:", "https:"].includes(parsedUrl.protocol)) {
    return response
      .status(400)
      .json({ error: "HTTP/HTTPS URLのみ対応しています" });
  }

  try {
    // Fetch the file from URL (streaming)
    const fetchRes = await fetch(url, {
      headers: {
        "User-Agent": "VideoOps/1.0",
      },
      redirect: "follow",
    });

    if (!fetchRes.ok) {
      return response.status(400).json({
        error: `ファイルの取得に失敗しました (${fetchRes.status})。URLが公開設定になっているか確認してください`,
      });
    }

    // Determine filename from URL or Content-Disposition
    let filename = guessFilename(fetchRes, parsedUrl);

    // Check content length if available
    const contentLength = fetchRes.headers.get("content-length");
    if (contentLength && parseInt(contentLength) > MAX_SIZE) {
      return response
        .status(400)
        .json({ error: "ファイルサイズが500MBを超えています" });
    }

    // Determine content type
    let contentType =
      fetchRes.headers.get("content-type") || "video/mp4";
    // Some servers return generic types for video files
    if (
      contentType.includes("octet-stream") ||
      contentType.includes("text/html")
    ) {
      contentType = guessContentType(filename);
    }

    // Stream directly to Vercel Blob
    const blob = await put("videos/" + filename, fetchRes.body, {
      access: "public",
      contentType,
    });

    return response.status(200).json({
      success: true,
      name: filename,
      url: blob.url,
      size_mb:
        contentLength
          ? Math.round((parseInt(contentLength) / (1024 * 1024)) * 10) / 10
          : null,
    });
  } catch (error) {
    console.error("Import error:", error);
    return response.status(500).json({
      error: error.message || "インポートに失敗しました",
    });
  }
}

function guessFilename(fetchRes, parsedUrl) {
  // Try Content-Disposition header first
  const disposition = fetchRes.headers.get("content-disposition");
  if (disposition) {
    const match = disposition.match(/filename[^;=\n]*=["']?([^"';\n]+)/i);
    if (match && match[1]) {
      return sanitizeFilename(match[1]);
    }
  }

  // Use URL pathname
  const pathname = parsedUrl.pathname;
  const segments = pathname.split("/").filter(Boolean);
  if (segments.length > 0) {
    const last = decodeURIComponent(segments[segments.length - 1]);
    const ext = last.substring(last.lastIndexOf(".")).toLowerCase();
    if (VIDEO_EXTENSIONS.includes(ext)) {
      return sanitizeFilename(last);
    }
  }

  // Fallback: generate name with timestamp
  return `import_${Date.now()}.mp4`;
}

function sanitizeFilename(name) {
  return name
    .replace(/[/\\:*?"<>|]/g, "_")
    .replace(/\s+/g, "_")
    .substring(0, 200);
}

function guessContentType(filename) {
  const ext = filename.substring(filename.lastIndexOf(".")).toLowerCase();
  const types = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
    ".m4v": "video/x-m4v",
  };
  return types[ext] || "video/mp4";
}
