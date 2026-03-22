import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { loadFont } from "@remotion/google-fonts/NotoSansJP";

const { fontFamily } = loadFont();

interface SubtitleProps {
  lines: string[];
  fontSize: number;
  position?: "top" | "center" | "bottom";
  color?: string;
}

export const Subtitle: React.FC<SubtitleProps> = ({
  lines,
  fontSize,
  position = "bottom",
  color = "#FFFFFF",
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 3], [0, 1], {
    extrapolateRight: "clamp",
  });

  const positionStyle: React.CSSProperties =
    position === "top"
      ? { top: 40 }
      : position === "center"
        ? { top: "50%", transform: "translateY(-50%)" }
        : { bottom: 40 };

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        pointerEvents: "none",
        opacity,
        ...positionStyle,
      }}
    >
      {lines.map((line, i) => (
        <div
          key={i}
          style={{
            color,
            fontSize,
            fontWeight: 900,
            fontFamily,
            textShadow: [
              "3px 0 0 #6B21A8",
              "-3px 0 0 #6B21A8",
              "0 3px 0 #6B21A8",
              "0 -3px 0 #6B21A8",
              "3px 3px 0 #6B21A8",
              "-3px -3px 0 #6B21A8",
              "3px -3px 0 #6B21A8",
              "-3px 3px 0 #6B21A8",
              "2px 2px 4px rgba(0,0,0,0.8)",
            ].join(", "),
            lineHeight: 1.4,
            whiteSpace: "nowrap",
            textAlign: "center",
          }}
        >
          {line}
        </div>
      ))}
    </div>
  );
};
