import React from "react";
import { Composition } from "remotion";
import { MainVideo } from "./MainVideo";
import { HeyGenVideo } from "./HeyGenVideo";

// Default props for Remotion Studio preview
const defaultSubtitles = [
  {
    id: 0,
    start: 0,
    end: 3,
    lines: ["テロップサンプル"],
    fontSize: 56,
    position: "bottom" as const,
  },
];

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* 通常の動画編集コンポジション */}
      <Composition
        id="MainVideo"
        component={MainVideo}
        durationInFrames={300}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          videoSrc: "",
          subtitles: defaultSubtitles,
          muted: true,
        }}
      />

      {/* 16:9 YouTube用 */}
      <Composition
        id="MainVideo-YouTube"
        component={MainVideo}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          videoSrc: "",
          subtitles: defaultSubtitles,
          muted: true,
        }}
      />

      {/* HeyGen アバター動画 */}
      <Composition
        id="HeyGenVideo"
        component={HeyGenVideo}
        durationInFrames={300}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          avatarVideoUrl: "",
          subtitles: defaultSubtitles,
          avatarLayout: "fullscreen" as const,
        }}
      />

      {/* HeyGen + 背景 PiP */}
      <Composition
        id="HeyGenVideo-PiP"
        component={HeyGenVideo}
        durationInFrames={300}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          avatarVideoUrl: "",
          subtitles: defaultSubtitles,
          avatarLayout: "pip-bottomright" as const,
        }}
      />
    </>
  );
};
