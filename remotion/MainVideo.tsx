import React from "react";
import {
  AbsoluteFill,
  Sequence,
  OffthreadVideo,
  Audio,
  staticFile,
  useVideoConfig,
} from "remotion";
import { Subtitle } from "./Subtitle";

interface SubtitleData {
  id: number;
  start: number;
  end: number;
  lines: string[];
  fontSize: number;
  position?: "top" | "center" | "bottom";
}

interface MainVideoProps {
  videoSrc: string;
  audioSrc?: string;
  subtitles: SubtitleData[];
  muted?: boolean;
}

export const MainVideo: React.FC<MainVideoProps> = ({
  videoSrc,
  audioSrc,
  subtitles,
  muted = true,
}) => {
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {/* Audio track (separate for better sync) */}
      {audioSrc && <Audio src={audioSrc} volume={1} />}

      {/* Video (muted by default per CLAUDE.md: BGMは音声なしで書き出す) */}
      <OffthreadVideo
        src={videoSrc}
        style={{ width: "100%", height: "100%", objectFit: "contain" }}
        muted={muted}
      />

      {/* Subtitles overlay */}
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
