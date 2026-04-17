import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
} from "remotion";
import { resolveHighlightColor } from "../types";
import type { EmotionType, SubtitleStyle } from "../types";
import { buildSubtitleTextShadow } from "./SubtitleBlock";

/** Default values when no SubtitleStyle is provided. */
const DEFAULT_FONT_SIZE = 80;
const DEFAULT_POSITION_Y = 192; // 10% below center of 1920px
// QW-03 (B안): 시그니처 색 정보가 없는 SceneText는 검정 6px 기본 외곽선.
const DEFAULT_STROKE_COLOR = "#000000";
const DEFAULT_STROKE_WIDTH = 6;
const DEFAULT_DROP_SHADOW = "3px 3px 8px rgba(0,0,0,0.7)";

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
  subtitleStyle?: SubtitleStyle;
  subtitle_style?: SubtitleStyle;
  translatedText?: string;
  translated_text?: string;
  // QW-01: 첫 1.5~2.5초 후킹 씬. true 시 1.4x 폰트 + 중앙 + 펀치 줌.
  hook?: boolean;
  // QW-02: 강조 키워드 색 카테고리.
  highlight_category?: string;
  highlightCategory?: string;
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
  const isHook = scene.hook === true;

  // QW-01: hook 씬은 펀치 줌으로 등장. 일반 씬은 기존 fade+up 진입.
  // 30fps 기준 frame 0/3/9 — 0.88 → 1.08 (overshoot) → 1.0 (settle).
  const punchScale = interpolate(
    frame,
    [0, 3, 9],
    [0.88, 1.08, 1.0],
    { extrapolateRight: "clamp" },
  );
  const opacity = interpolate(
    frame,
    isHook ? [0, 3] : [0, 15],
    [0, 1],
    { extrapolateRight: "clamp" },
  );
  const animateY = isHook
    ? 0
    : interpolate(frame, [0, 15], [40, 0], { extrapolateRight: "clamp" });

  // Support both camelCase and snake_case from props
  const style: SubtitleStyle | undefined =
    scene.subtitleStyle || scene.subtitle_style;

  const baseFontSize = style?.font_size ?? DEFAULT_FONT_SIZE;
  // QW-01: hook 씬은 1.4x 폰트로 임팩트 강화
  const fontSize = isHook ? Math.round(baseFontSize * 1.4) : baseFontSize;
  const fontWeight = style?.font_weight ?? "700";
  const fontFamily = style?.font_family ?? "Noto Sans KR, sans-serif";
  const textColor = style?.color ?? "#FFFFFF";
  // QW-03: 기존 `style.shadow`는 drop shadow로 흡수. 외곽선은 별도 합성.
  const dropShadow = style?.shadow ?? DEFAULT_DROP_SHADOW;
  const strokeColor = style?.stroke_color ?? DEFAULT_STROKE_COLOR;
  const strokeWidth = style?.stroke_width ?? DEFAULT_STROKE_WIDTH;
  const textShadow = buildSubtitleTextShadow(
    strokeWidth,
    strokeColor,
    dropShadow,
  );
  // QW-01: hook 씬은 화면 중앙 강제 (positionY 0.5)
  const positionY = isHook ? 0.5 : (style?.position_y ?? 0.652);
  const bgColor = style?.bg_color ?? null;
  const bgOpacity = style?.bg_opacity ?? 0;

  // Convert position_y (0-1) to pixel offset from center
  // 0.5 = center, 0 = top, 1 = bottom
  const verticalOffset = (positionY - 0.5) * 1920;

  const isComment = scene.type === "comment";
  const highlightWords = scene.highlightWords || [];
  // QW-02: highlight_category가 있으면 카테고리 색, 없으면 emotion 색.
  const highlightCategory = scene.highlightCategory || scene.highlight_category;
  const highlightColor = resolveHighlightColor(
    highlightCategory,
    (emotion || "relatable") as EmotionType,
  );

  const translatedText = scene.translatedText || scene.translated_text;

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
          transform: isHook
            ? `translateY(${verticalOffset}px) scale(${punchScale})`
            : `translateY(${animateY + verticalOffset}px)`,
          textAlign: "center",
          maxWidth: "90%",
          position: "relative",
        }}
      >
        {/* Background overlay for subtitle */}
        {bgColor && bgOpacity > 0 && (
          <div
            style={{
              position: "absolute",
              inset: -16,
              backgroundColor: bgColor,
              opacity: bgOpacity,
              borderRadius: 12,
            }}
          />
        )}

        {isComment && (
          <div
            style={{
              position: "relative",
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
            position: "relative",
            fontSize,
            fontWeight: fontWeight as any,
            color: textColor,
            fontFamily,
            lineHeight: 1.5,
            textShadow,
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

        {/* Dual subtitle (translated text) */}
        {translatedText && (
          <div
            style={{
              position: "relative",
              fontSize: Math.round(fontSize * 0.55),
              fontWeight: "400",
              color: "rgba(255,255,255,0.8)",
              fontFamily,
              lineHeight: 1.4,
              textShadow: "2px 2px 6px rgba(0,0,0,0.7)",
              whiteSpace: "pre-wrap",
              marginTop: 12,
            }}
          >
            {translatedText}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
