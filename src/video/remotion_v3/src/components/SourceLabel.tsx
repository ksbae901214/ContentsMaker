import React from "react";

interface SourceLabelProps {
  label: string;
}

/**
 * 최하단 고정 출처 라벨.
 * "출처: YTN (2016.12.15)" 형식, 회색(#aaa) 24px, 가운데 정렬.
 */
export const SourceLabel: React.FC<SourceLabelProps> = ({ label }) => {
  return (
    <div
      style={{
        position: "absolute",
        bottom: 24,
        left: 0,
        width: "100%",
        textAlign: "center",
        padding: "0 32px",
        boxSizing: "border-box",
      }}
    >
      <span
        style={{
          fontFamily: "'Noto Sans KR', 'Apple SD Gothic Neo', '맑은 고딕', sans-serif",
          fontWeight: 400,
          fontSize: 24,
          color: "#aaaaaa",
        }}
      >
        {label}
      </span>
    </div>
  );
};
