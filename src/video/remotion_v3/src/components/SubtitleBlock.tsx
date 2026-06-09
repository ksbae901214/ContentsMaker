/**
 * V3 SubtitleBlock — 하단 자막 박스.
 *
 * 사양: contracts/remotion_v3.md "SubtitleBlock 시각 사양".
 * FR-018: 자막 4색 시스템 + emphasis 시 폰트 1.4x + 빨강 강제.
 * 락인: fade in/out 없음 (하드 컷, FR-035).
 */
import React from "react";
import {
  EMPHASIS_COLOR,
  SUBTITLE_COLOR_MAP,
  type SubtitleColor,
} from "../types";

type SubtitleBlockProps = {
  text: string;
  color: SubtitleColor;
  emphasis: boolean;
};

const BASE_FONT_SIZE = 56;
const EMPHASIS_MULTIPLIER = 1.4;

export const SubtitleBlock: React.FC<SubtitleBlockProps> = ({
  text,
  color,
  emphasis,
}) => {
  const finalColor = emphasis ? EMPHASIS_COLOR : SUBTITLE_COLOR_MAP[color];
  const fontSize = emphasis
    ? Math.round(BASE_FONT_SIZE * EMPHASIS_MULTIPLIER)
    : BASE_FONT_SIZE;

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 0,
        height: 320,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "0 60px",
        boxSizing: "border-box",
        zIndex: 8,
      }}
    >
      <div
        style={{
          background: "rgba(255, 255, 255, 0.95)",
          padding: "24px 36px",
          borderRadius: 16,
          maxWidth: "100%",
        }}
      >
        <div
          style={{
            fontFamily: '"Noto Sans KR", sans-serif',
            fontWeight: 700,
            fontSize,
            color: finalColor,
            textAlign: "center",
            lineHeight: 1.3,
            whiteSpace: "pre-wrap",
            wordBreak: "keep-all",
          }}
        >
          {text}
        </div>
      </div>
    </div>
  );
};
