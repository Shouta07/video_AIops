import { del } from "@vercel/blob";

export default async function handler(request, response) {
  if (request.method !== "POST") {
    return response.status(405).json({ error: "Method not allowed" });
  }

  try {
    const { url } = request.body;
    if (!url) {
      return response.status(400).json({ error: "URL is required" });
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
