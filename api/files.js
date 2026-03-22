import { list } from "@vercel/blob";

export default async function handler(request, response) {
  if (request.method !== "GET") {
    return response.status(405).json({ error: "Method not allowed" });
  }

  try {
    const result = await list({ prefix: "videos/" });
    const files = result.blobs
      .filter((b) => b.size > 0)
      .map((b) => ({
        name: b.pathname.replace(/^videos\//, ""),
        url: b.url,
        size_mb: Math.round((b.size / (1024 * 1024)) * 10) / 10,
        uploaded: b.uploadedAt,
      }))
      .sort((a, b) => new Date(b.uploaded) - new Date(a.uploaded));

    return response.status(200).json({ files });
  } catch (error) {
    console.error("List error:", error);
    return response
      .status(500)
      .json({ error: error.message || "Failed to list files" });
  }
}
