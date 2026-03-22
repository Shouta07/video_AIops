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

  if (!process.env.CLOUDINARY_CLOUD_NAME) {
    return response.status(500).json({
      error:
        "Cloudinary が未設定です。環境変数を設定してください",
    });
  }

  const {
    videoUrl,
    width = 1080,
    height = 1920,
    startTime = 0,
    endTime = null,
  } = request.body || {};

  if (!videoUrl) {
    return response.status(400).json({ error: "videoUrl is required" });
  }

  try {
    // Build transformation: trim + resize + no-audio
    const transformations = [];

    // Trim
    const trimOpts = {};
    if (startTime > 0) trimOpts.start_offset = String(startTime);
    if (endTime !== null && endTime > startTime) {
      trimOpts.end_offset = String(endTime);
    }
    if (Object.keys(trimOpts).length > 0) {
      transformations.push(trimOpts);
    }

    // Resize
    transformations.push({
      width,
      height,
      crop: "pad",
      background: "black",
      gravity: "center",
    });

    // Remove audio
    transformations.push({ flags: "no_audio" });

    // Output format
    transformations.push({ format: "mp4", video_codec: "h264" });

    const result = await cloudinary.uploader.upload(videoUrl, {
      resource_type: "video",
      type: "upload",
      eager: [{ transformation: transformations }],
      eager_async: false,
      folder: "video-ops",
      timeout: 120000,
    });

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
      bytes: result.eager?.[0]?.bytes || result.bytes,
    });
  } catch (error) {
    console.error("Render error:", error);
    return response
      .status(500)
      .json({ error: error.message || "動画の処理に失敗しました" });
  }
}
