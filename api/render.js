import { v2 as cloudinary } from "cloudinary";

cloudinary.config({
  cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
  api_key: process.env.CLOUDINARY_API_KEY,
  api_secret: process.env.CLOUDINARY_API_SECRET,
});

export default async function handler(request, response) {
  if (request.method !== "POST") {
    return response.status(405).json({ error: "Method not allowed" });
  }

  // Check Cloudinary config
  if (!process.env.CLOUDINARY_CLOUD_NAME) {
    return response.status(500).json({
      error: "Cloudinary が未設定です。環境変数 CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET を設定してください",
    });
  }

  const {
    videoUrl,
    width = 1080,
    height = 1920,
    startTime = 0,
    endTime = null,
    subtitles = [],
  } = request.body || {};

  if (!videoUrl) {
    return response.status(400).json({ error: "videoUrl is required" });
  }

  try {
    // Build transformation chain
    const transformations = [];

    // 1. Trim
    const trimOpts = {};
    if (startTime > 0) trimOpts.start_offset = String(startTime);
    if (endTime !== null && endTime > startTime) {
      trimOpts.end_offset = String(endTime);
    }
    if (Object.keys(trimOpts).length > 0) {
      transformations.push(trimOpts);
    }

    // 2. Resize to platform specs (fill with padding)
    transformations.push({
      width,
      height,
      crop: "pad",
      background: "black",
      gravity: "center",
    });

    // 3. Remove audio
    transformations.push({ flags: "no_audio" });

    // 4. Add text overlays (subtitles)
    for (const sub of subtitles) {
      if (!sub.text || !sub.text.trim()) continue;

      const gravity = sub.position === "top" ? "north"
        : sub.position === "center" ? "center"
        : "south";

      const yOffset = sub.position === "center" ? 0 : 60;

      const overlay = {
        overlay: {
          font_family: "Noto Sans JP",
          font_size: 42,
          font_weight: "bold",
          text: sub.text.trim(),
        },
        gravity,
        y: yOffset,
        color: "white",
        effect: "outline:3:black",
      };

      // Time-based visibility
      if (sub.startTime !== undefined && sub.endTime !== undefined) {
        overlay.start_offset = String(sub.startTime);
        overlay.end_offset = String(sub.endTime);
      }

      transformations.push(overlay);
    }

    // 5. Output format
    transformations.push({ format: "mp4", video_codec: "h264" });

    // Upload remote video with eager transformation
    const result = await cloudinary.uploader.upload(videoUrl, {
      resource_type: "video",
      type: "upload",
      eager: [{ transformation: transformations }],
      eager_async: false,
      folder: "video-ops",
      timeout: 120000,
    });

    // Get the transformed video URL
    const outputUrl =
      result.eager && result.eager[0]
        ? result.eager[0].secure_url
        : result.secure_url;

    return response.status(200).json({
      success: true,
      url: outputUrl,
      duration: result.duration,
      width: result.width,
      height: result.height,
      format: result.format,
      bytes: result.eager?.[0]?.bytes || result.bytes,
    });
  } catch (error) {
    console.error("Render error:", error);

    const msg = error.message || "動画の処理に失敗しました";
    // Provide helpful error messages
    if (msg.includes("Invalid") || msg.includes("401")) {
      return response.status(500).json({
        error: "Cloudinary の認証に失敗しました。API キーを確認してください",
      });
    }

    return response.status(500).json({ error: msg });
  }
}
