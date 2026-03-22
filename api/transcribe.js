import OpenAI from "openai";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

export const config = {
  api: { bodyParser: { sizeLimit: "1mb" } },
};

export default async function handler(request, response) {
  if (request.method !== "POST") {
    return response.status(405).json({ error: "Method not allowed" });
  }

  if (!process.env.OPENAI_API_KEY) {
    return response.status(500).json({
      error: "OPENAI_API_KEY が未設定です。Vercel の環境変数に追加してください",
    });
  }

  const { videoUrl } = request.body || {};
  if (!videoUrl) {
    return response.status(400).json({ error: "videoUrl is required" });
  }

  try {
    // Fetch video file from Blob URL
    const videoRes = await fetch(videoUrl);
    if (!videoRes.ok) {
      return response
        .status(400)
        .json({ error: "動画の取得に失敗しました" });
    }

    // Convert to File-like object for OpenAI API
    const buffer = await videoRes.arrayBuffer();
    const file = new File([buffer], "video.mp4", { type: "video/mp4" });

    // Call Whisper API with word-level timestamps
    const transcription = await openai.audio.transcriptions.create({
      file,
      model: "whisper-1",
      language: "ja",
      response_format: "verbose_json",
      timestamp_granularities: ["word", "segment"],
    });

    // Return segments with word-level timestamps
    return response.status(200).json({
      text: transcription.text,
      segments: (transcription.segments || []).map((seg) => ({
        id: seg.id,
        start: seg.start,
        end: seg.end,
        text: seg.text,
      })),
      words: (transcription.words || []).map((w) => ({
        word: w.word,
        start: w.start,
        end: w.end,
      })),
      duration: transcription.duration,
    });
  } catch (error) {
    console.error("Transcribe error:", error);

    if (error.status === 413 || error.message?.includes("too large")) {
      return response.status(400).json({
        error: "動画ファイルが大きすぎます。25MB以下の動画を使用してください",
      });
    }

    return response.status(500).json({
      error: error.message || "文字起こしに失敗しました",
    });
  }
}
