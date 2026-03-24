import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
} from "remotion";

/** Uniform font size for all scenes (consistent throughout video). */
const UNIFORM_FONT_SIZE = 80;

/** Vertical offset: 10% below center (10% of 1920px = 192px). */
const VERTICAL_OFFSET = 192;

interface SceneData {
  id: number;
  timestamp: number;
  duration: number;
  type: string;
  text: string;
  voice_text?: string;
  voiceText?: string;
  emphasis: string;
}

interface SceneTextProps {
  scene: SceneData;
}

export const SceneText: React.FC<SceneTextProps> = ({ scene }) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });
  const animateY = interpolate(frame, [0, 15], [40, 0], {
    extrapolateRight: "clamp",
  });

  const isComment = scene.type === "comment";

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        padding: "0 60px",
      }}
    >
      <div
        style={{
          opacity,
          transform: `translateY(${animateY + VERTICAL_OFFSET}px)`,
          textAlign: "center",
          maxWidth: "90%",
        }}
      >
        {isComment && (
          <div
            style={{
              fontSize: 28,
              color: "rgba(255,255,255,0.7)",
              marginBottom: 16,
              fontFamily: "Noto Sans KR, sans-serif",
            }}
          >
            Best Comment
          </div>
        )}
        <div
          style={{
            fontSize: UNIFORM_FONT_SIZE,
            fontWeight: 700,
            color: "#FFFFFF",
            fontFamily: "Noto Sans KR, sans-serif",
            lineHeight: 1.5,
            textShadow: "3px 3px 8px rgba(0,0,0,0.7)",
            whiteSpace: "pre-wrap",
            wordBreak: "keep-all",
          }}
        >
          {scene.text}
        </div>
      </div>
    </AbsoluteFill>
  );
};
