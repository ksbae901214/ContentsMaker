/**
 * V3 Outro — 마지막 1.5초 CTA 화면.
 *
 * 검정 배경 + 흰 글자.
 * 락인: fade-in 없음 (FR-035 하드 컷). 정적 표시만.
 */
import React from "react";
import { AbsoluteFill } from "remotion";

type OutroProps = {
  ctaText: string;
};

export const Outro: React.FC<OutroProps> = ({ ctaText }) => {
  return (
    <AbsoluteFill
      style={{
        background: "#000",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "0 80px",
      }}
    >
      <div
        style={{
          fontFamily: '"Noto Sans KR", sans-serif',
          fontWeight: 900,
          fontSize: 80,
          color: "#FFFFFF",
          textAlign: "center",
          lineHeight: 1.3,
          wordBreak: "keep-all",
          whiteSpace: "pre-wrap",
        }}
      >
        {ctaText}
      </div>
    </AbsoluteFill>
  );
};
