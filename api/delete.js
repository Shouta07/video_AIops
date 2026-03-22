import { del } from "@vercel/blob";

export default async function handler(request, response) {
  if (request.method !== "POST") {
    return response.status(405).json({ error: "Method not allowed" });
  }

  // Origin check - only allow requests from our own domain
  const origin = request.headers.origin || "";
  const host = request.headers.host || "";
  if (origin && !origin.includes(host)) {
    return response.status(403).json({ error: "Forbidden" });
  }

  try {
    const { url } = request.body || {};
    if (!url || typeof url !== "string") {
      return response.status(400).json({ error: "URL is required" });
    }

    // Only allow deleting from our own blob store
    if (!url.includes(".public.blob.vercel-storage.com/")) {
      return response.status(400).json({ error: "Invalid blob URL" });
    }

    await del(url);
    return response.status(200).json({ deleted: true });
  } catch (error) {
    console.error("Delete error:", error);
    return response
      .status(500)
      .json({ error: error.message || "Failed to delete" });
  }
}
