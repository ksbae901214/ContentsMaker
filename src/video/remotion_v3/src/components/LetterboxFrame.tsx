/**
 * V3 LetterboxFrame — 하단 letterbox 영역 + 출처 라벨.
 *
 * FR-019: sourceLabel 표시 (검정 반투명 배경, 흰 글자 28px).
 * 자막 영역(하단 320px) 위에 얇은 띠 형태로 배치.
 */
import React from "react";

type LetterboxFrameProps = {
  sourceLabel?: string;
};

export const LetterboxFrame: React.FC<LetterboxFrameProps> = ({
  sourceLabel,
}) => {
  if (!sourceLabel) return null;

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 320, // 자막 박스 위
        height: 48,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(0, 0, 0, 0.65)",
        zIndex: 9,
      }}
    >
      <div
        style={{
          fontFamily: '"Noto Sans KR", sans-serif',
          fontWeight: 500,
          fontSize: 28,
          color: "#FFFFFF",
          letterSpacing: 0.5,
        }}
      >
        {sourceLabel}
      </div>
    </div>
  );
};
