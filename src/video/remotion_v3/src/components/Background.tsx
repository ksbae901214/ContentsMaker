/**
 * V3 Background — 풀스크린 그라데이션 배경.
 *
 * 락인: 엔트런스 페이드인 없음 (FR-035 하드 컷).
 */
import React from "react";
import { AbsoluteFill } from "remotion";

type BackgroundProps = {
  colors: [string, string];
};

export const Background: React.FC<BackgroundProps> = ({ colors }) => {
  const [c1, c2] = colors;
  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, ${c1}, ${c2})`,
      }}
    />
  );
};
