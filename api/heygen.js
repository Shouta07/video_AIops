// HeyGen API 統合
// アバター動画を生成し、Remotion で合成するための動画URLを返す

export default async function handler(request, response) {
  if (request.method !== "POST") {
    return response.status(405).json({ error: "Method not allowed" });
  }

  const apiKey = process.env.HEYGEN_API_KEY;
  if (!apiKey) {
    return response.status(500).json({
      error: "HEYGEN_API_KEY が未設定です。環境変数に追加してください",
    });
  }

  const { action } = request.body || {};

  try {
    if (action === "list-avatars") {
      return await listAvatars(apiKey, response);
    } else if (action === "list-voices") {
      return await listVoices(apiKey, response);
    } else if (action === "generate") {
      return await generateVideo(apiKey, request.body, response);
    } else if (action === "status") {
      return await checkStatus(apiKey, request.body, response);
    } else {
      return response
        .status(400)
        .json({ error: "action は list-avatars / list-voices / generate / status のいずれかを指定してください" });
    }
  } catch (error) {
    console.error("HeyGen error:", error);
    return response
      .status(500)
      .json({ error: error.message || "HeyGen API エラー" });
  }
}

async function listAvatars(apiKey, response) {
  const res = await fetch("https://api.heygen.com/v2/avatars", {
    headers: { "X-Api-Key": apiKey },
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.message || "アバター一覧の取得に失敗");

  const avatars = (data.data?.avatars || []).map((a) => ({
    avatar_id: a.avatar_id,
    avatar_name: a.avatar_name,
    preview_image_url: a.preview_image_url,
    gender: a.gender,
  }));

  return response.status(200).json({ avatars });
}

async function listVoices(apiKey, response) {
  const res = await fetch("https://api.heygen.com/v2/voices", {
    headers: { "X-Api-Key": apiKey },
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.message || "音声一覧の取得に失敗");

  const voices = (data.data?.voices || [])
    .filter((v) => v.language === "Japanese" || v.language === "ja")
    .map((v) => ({
      voice_id: v.voice_id,
      name: v.name,
      language: v.language,
      gender: v.gender,
      preview_audio: v.preview_audio,
    }));

  return response.status(200).json({ voices });
}

async function generateVideo(apiKey, body, response) {
  const {
    script,
    avatar_id,
    voice_id,
    width = 1080,
    height = 1920,
  } = body;

  if (!script) {
    return response.status(400).json({ error: "script（台本）が必要です" });
  }

  const payload = {
    video_inputs: [
      {
        character: {
          type: "avatar",
          avatar_id: avatar_id || "default",
          avatar_style: "normal",
        },
        voice: {
          type: "text",
          input_text: script,
          voice_id: voice_id || "ja-JP-NanamiNeural",
        },
      },
    ],
    dimension: { width, height },
    test: false,
  };

  const res = await fetch("https://api.heygen.com/v2/video/generate", {
    method: "POST",
    headers: {
      "X-Api-Key": apiKey,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  if (!res.ok) throw new Error(data.message || "動画生成に失敗");

  return response.status(200).json({
    video_id: data.data?.video_id,
    status: "processing",
    message: "動画を生成中です。status アクションで進捗を確認してください",
  });
}

async function checkStatus(apiKey, body, response) {
  const { video_id } = body;
  if (!video_id) {
    return response.status(400).json({ error: "video_id が必要です" });
  }

  const res = await fetch(
    `https://api.heygen.com/v1/video_status.get?video_id=${video_id}`,
    { headers: { "X-Api-Key": apiKey } }
  );

  const data = await res.json();
  if (!res.ok) throw new Error(data.message || "ステータス取得に失敗");

  const status = data.data?.status;
  const videoUrl = data.data?.video_url;

  return response.status(200).json({
    video_id,
    status,
    video_url: videoUrl || null,
    thumbnail_url: data.data?.thumbnail_url || null,
  });
}
