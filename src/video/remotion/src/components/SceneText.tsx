import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
} from "remotion";
import { FONT_SIZES } from "../types";

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
  const translateY = interpolate(frame, [0, 15], [40, 0], {
    extrapolateRight: "clamp",
  });

  const fontSize = FONT_SIZES[scene.emphasis] || 42;

  const isComment = scene.type === "comment";
  const isTitle = scene.type === "title";

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
          transform: `translateY(${translateY}px)`,
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
            fontSize: isTitle ? 58 : fontSize,
            fontWeight: isTitle || scene.emphasis === "high" ? 800 : 600,
            color: "#FFFFFF",
            fontFamily: "Noto Sans KR, sans-serif",
            lineHeight: 1.5,
            textShadow: "3px 3px 8px rgba(0,0,0,0.7)",
            letterSpacing: isTitle ? 2 : 0,
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
