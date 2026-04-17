// T068: 프리셋별 스타일로 자막 렌더링
import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { CATEGORY_HIGHLIGHT_COLORS } from "../types";

export interface SubtitlePresetData {
  id: string;
  fontFamily: string;
  baseFontSize: number;
  color: string;
  highlightColor: string;
  strokeColor: string;
  strokeWidth: number;
  background: string;
  textAlign: "left" | "center" | "right";
  paddingPx: number;
  position: "bottom" | "center" | "top";
  maxLines: number;
  lineHeight: number;
  bold: boolean;
  // QW-03: 외곽선과 함께 합성되는 부드러운 drop shadow.
  // 누락 시 "3px 3px 8px rgba(0,0,0,0.7)" (Q3=약) 기본값 사용.
  dropShadow?: string;
}

interface SubtitleBlockProps {
  text: string;
  preset: SubtitlePresetData;
  style?: "high" | "medium" | "low";
  highlightWords?: string[];
  // QW-01: 후킹 씬일 때 1.4x 폰트 + 중앙 + 펀치 줌 적용
  isHook?: boolean;
  // QW-02: 강조 키워드 색 카테고리 — 있으면 preset.highlightColor 대신 적용
  highlightCategory?: string;
}

const STYLE_SCALE: Record<string, number> = {
  high: 1.1,
  medium: 1.0,
  low: 0.9,
};

/**
 * QW-03: 8방향 stroke + drop shadow 합성.
 * strokeWidth가 0이면 drop shadow만 적용. 아무것도 없으면 "none".
 */
export function buildSubtitleTextShadow(
  strokeWidth: number,
  strokeColor: string,
  dropShadow?: string,
): string {
  const parts: string[] = [];
  if (strokeWidth > 0) {
    const w = strokeWidth;
    parts.push(
      `-${w}px -${w}px 0 ${strokeColor}`,
      `${w}px -${w}px 0 ${strokeColor}`,
      `-${w}px ${w}px 0 ${strokeColor}`,
      `${w}px ${w}px 0 ${strokeColor}`,
      `-${w}px 0 0 ${strokeColor}`,
      `${w}px 0 0 ${strokeColor}`,
      `0 -${w}px 0 ${strokeColor}`,
      `0 ${w}px 0 ${strokeColor}`,
    );
  }
  if (dropShadow && dropShadow !== "none") {
    parts.push(dropShadow);
  }
  return parts.length > 0 ? parts.join(", ") : "none";
}

function renderWithHighlights(
  text: string,
  highlightWords: string[],
  highlightColor: string,
): React.ReactNode {
  if (highlightWords.length === 0) return text;
  // Escape regex chars + build alternation
  const escaped = highlightWords
    .filter(Boolean)
    .map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  if (escaped.length === 0) return text;
  const re = new RegExp(`(${escaped.join("|")})`, "g");
  const parts = text.split(re);
  return parts.map((p, i) => {
    if (highlightWords.includes(p)) {
      return (
        <span key={i} style={{ color: highlightColor }}>
          {p}
        </span>
      );
    }
    return <React.Fragment key={i}>{p}</React.Fragment>;
  });
}

export const SubtitleBlock: React.FC<SubtitleBlockProps> = ({
  text,
  preset,
  style = "medium",
  highlightWords = [],
  isHook = false,
  highlightCategory,
}) => {
  const frame = useCurrentFrame();
  const scale = STYLE_SCALE[style] ?? 1.0;
  // QW-01: hook 씬은 1.4x 폰트로 임팩트 강화
  const hookMultiplier = isHook ? 1.4 : 1.0;
  const fontSize = Math.round(preset.baseFontSize * scale * hookMultiplier);

  // QW-01: hook 씬은 위치를 화면 중앙으로 강제
  // "top" is positioned at 20% to stay below the YouTube Shorts navigation bar
  // (~8–10% from top on a phone screen). "bottom" sits in the lower letterbox
  // black bar when the source clip is 16:9 letterboxed inside the 9:16 frame.
  const posStyle: React.CSSProperties = isHook
    ? { top: "40%", alignItems: "center" }
    : preset.position === "top"
    ? { top: "20%", alignItems: "flex-start" }
    : preset.position === "center"
    ? { top: "40%", alignItems: "center" }
    : { bottom: "5%", alignItems: "flex-end" };

  // QW-01: hook 씬은 펀치 줌 — 30fps 기준 frame 0/3/9 → 0.88/1.08/1.0
  const punchScale = isHook
    ? interpolate(frame, [0, 3, 9], [0.88, 1.08, 1.0], {
        extrapolateRight: "clamp",
      })
    : 1.0;

  const dropShadow = preset.dropShadow ?? "3px 3px 8px rgba(0,0,0,0.7)";
  const textShadow = buildSubtitleTextShadow(
    preset.strokeWidth,
    preset.strokeColor,
    dropShadow,
  );

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        padding: "0 80px",
        ...posStyle,
      }}
    >
      <div
        style={{
          background: preset.background,
          padding: `${preset.paddingPx}px ${preset.paddingPx * 1.5}px`,
          borderRadius: 12,
          maxWidth: "90%",
          transform: isHook ? `scale(${punchScale})` : undefined,
        }}
      >
        <div
          style={{
            fontFamily: preset.fontFamily,
            fontSize,
            fontWeight: preset.bold ? 800 : 500,
            color: preset.color,
            textAlign: preset.textAlign,
            lineHeight: preset.lineHeight,
            textShadow,
            whiteSpace: "pre-wrap",
            wordBreak: "keep-all",
          }}
        >
          {renderWithHighlights(
            text,
            highlightWords,
            (highlightCategory && CATEGORY_HIGHLIGHT_COLORS[highlightCategory]) ||
              preset.highlightColor,
          )}
        </div>
      </div>
    </div>
  );
};
