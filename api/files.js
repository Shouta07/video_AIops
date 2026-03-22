import { list } from "@vercel/blob";

export default async function handler(req, res) {
  if (req.method !== "GET") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  try {
    const { blobs } = await list({ prefix: "videos/" });
    const files = blobs.map((b) => ({
      name: b.pathname.replace("videos/", ""),
      url: b.url,
      size_mb: Math.round((b.size / (1024 * 1024)) * 10) / 10,
      uploaded: b.uploadedAt,
    }));
    return res.status(200).json({ files });
  } catch (error) {
    return res.status(500).json({ error: error.message });
  }
}
