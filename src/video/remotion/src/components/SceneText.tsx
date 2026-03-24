import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
} from "remotion";
import { HIGHLIGHT_COLORS } from "../types";
import type { EmotionType } from "../types";

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
  highlightWords?: string[];
}

interface SceneTextProps {
  scene: SceneData;
  emotion?: string;
}

/**
 * Render text with highlighted keywords in emotion color.
 * Splits text by highlight words and wraps matches in colored spans.
 */
const HighlightedText: React.FC<{
  text: string;
  highlights: string[];
  color: string;
}> = ({ text, highlights, color }) => {
  if (!highlights.length) {
    return <>{text}</>;
  }

  // Build regex from highlight words (escape special chars)
  const escaped = highlights.map((w) =>
    w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  );
  const regex = new RegExp(`(${escaped.join("|")})`, "g");
  const parts = text.split(regex);

  return (
    <>
      {parts.map((part, i) => {
        const isHighlight = highlights.some(
          (h) => h.toLowerCase() === part.toLowerCase()
        );
        return isHighlight ? (
          <span key={i} style={{ color }}>{part}</span>
        ) : (
          <React.Fragment key={i}>{part}</React.Fragment>
        );
      })}
    </>
  );
};

export const SceneText: React.FC<SceneTextProps> = ({ scene, emotion }) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });
  const animateY = interpolate(frame, [0, 15], [40, 0], {
    extrapolateRight: "clamp",
  });

  const isComment = scene.type === "comment";
  const highlightWords = scene.highlightWords || [];
  const highlightColor =
    HIGHLIGHT_COLORS[(emotion || "relatable") as EmotionType] ||
    HIGHLIGHT_COLORS.relatable;

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
          <HighlightedText
            text={scene.text}
            highlights={highlightWords}
            color={highlightColor}
          />
        </div>
      </div>
    </AbsoluteFill>
  );
};
