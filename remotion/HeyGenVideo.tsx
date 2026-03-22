import React from "react";
import {
  AbsoluteFill,
  Sequence,
  Img,
  OffthreadVideo,
  useVideoConfig,
} from "remotion";
import { Subtitle } from "./Subtitle";

interface HeyGenVideoProps {
  /** HeyGen で生成されたアバター動画の URL */
  avatarVideoUrl: string;
  /** 背景画像/動画 URL (optional) */
  backgroundUrl?: string;
  /** テロップデータ */
  subtitles: Array<{
    id: number;
    start: number;
    end: number;
    lines: string[];
    fontSize: number;
    position?: "top" | "center" | "bottom";
  }>;
  /** アバターのレイアウト */
  avatarLayout?: "fullscreen" | "pip-bottomright" | "pip-bottomleft";
}

export const HeyGenVideo: React.FC<HeyGenVideoProps> = ({
  avatarVideoUrl,
  backgroundUrl,
  subtitles,
  avatarLayout = "fullscreen",
}) => {
  const { fps, width, height } = useVideoConfig();

  const isFullscreen = avatarLayout === "fullscreen";
  const pipSize = { width: Math.round(width * 0.3), height: Math.round(height * 0.3) };
  const pipPosition =
    avatarLayout === "pip-bottomleft"
      ? { left: 20, bottom: 120 }
      : { right: 20, bottom: 120 };

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {/* Background (image or video) */}
      {backgroundUrl && !isFullscreen && (
        backgroundUrl.match(/\.(mp4|mov|webm)$/i) ? (
          <OffthreadVideo
            src={backgroundUrl}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
            muted
          />
        ) : (
          <Img
            src={backgroundUrl}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        )
      )}

      {/* Avatar video */}
      <div
        style={
          isFullscreen
            ? { width: "100%", height: "100%" }
            : {
                position: "absolute",
                ...pipPosition,
                width: pipSize.width,
                height: pipSize.height,
                borderRadius: 16,
                overflow: "hidden",
                boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
              }
        }
      >
        <OffthreadVideo
          src={avatarVideoUrl}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </div>

      {/* Subtitles */}
      {subtitles.map((sub) => {
        const from = Math.round(sub.start * fps);
        const dur = Math.max(1, Math.round((sub.end - sub.start) * fps));
        return (
          <Sequence key={sub.id} from={from} durationInFrames={dur}>
            <Subtitle
              lines={sub.lines}
              fontSize={sub.fontSize}
              position={sub.position}
            />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
