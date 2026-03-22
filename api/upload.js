import { handleUpload } from "@vercel/blob/client";

export const config = {
  api: { bodyParser: { sizeLimit: "10mb" } },
};

export default async function handler(request, response) {
  if (request.method !== "POST") {
    return response.status(405).json({ error: "Method not allowed" });
  }

  try {
    const body = await handleUpload({
      body: request.body,
      request,
      onBeforeGenerateToken: async (pathname) => {
        return {
          allowedContentTypes: [
            "video/mp4",
            "video/quicktime",
            "video/x-msvideo",
            "video/x-matroska",
            "video/webm",
            "video/x-m4v",
          ],
          maximumSizeInBytes: 500 * 1024 * 1024,
        };
      },
      onUploadCompleted: async ({ blob }) => {
        console.log("Upload completed:", blob.pathname, blob.url);
      },
    });

    return response.status(200).json(body);
  } catch (error) {
    console.error("Upload error:", error);
    return response
      .status(400)
      .json({ error: error.message || "Upload failed" });
  }
}
