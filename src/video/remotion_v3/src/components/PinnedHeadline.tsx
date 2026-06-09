/**
 * V3 PinnedHeadline — 영상 전체 동안 화면 상단에 고정되는 노란 헤드라인 박스.
 *
 * 사양: contracts/remotion_v3.md "PinnedHeadline 시각 사양".
 * FR-017: 영상 전체 동안 같은 텍스트 (애니메이션 없음, 하드 표시).
 */
import React from "react";

type PinnedHeadlineProps = {
  headline: string;
};

export const PinnedHeadline: React.FC<PinnedHeadlineProps> = ({ headline }) => {
  return (
    <div
      style={{
        position: "absolute",
        top: 80,
        left: 60,
        right: 60,
        height: 240,
        background: "#FFD700",
        border: "4px solid #000",
        borderRadius: 12,
        fontFamily: '"Noto Sans KR", sans-serif',
        fontWeight: 900,
        fontSize: 72,
        color: "#000",
        textAlign: "center",
        padding: "30px 20px",
        lineHeight: 1.2,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        wordBreak: "keep-all",
        boxSizing: "border-box",
        zIndex: 10,
      }}
    >
      {headline}
    </div>
  );
};
