import React from "react";

// 키워드 색 순환: 파랑 → 빨강 → 파랑 → ...
const KEYWORD_COLORS = ["#1d4ed8", "#dc2626"];

interface HookCardProps {
  question: string;
  keywords: string[];
}

/**
 * 상단 ~28% 영역 (height 536px = 1920 × 0.28) 흰 배경 박스.
 * 질문형 훅 텍스트, keywords 색 강조 (파랑/빨강 순환).
 * 폰트: Noto Sans KR Black (또는 시스템 고딕 볼드), 72px, 줄 간격 1.3.
 */
export const HookCard: React.FC<HookCardProps> = ({ question, keywords }) => {
  const words = question.split(" ");

  const keywordSet = new Set(keywords.map((k) => k.trim()));
  // 키워드 → 색 인덱스 맵 (등장 순서 기준)
  const keywordColorMap = new Map<string, string>();
  keywords.forEach((kw, idx) => {
    const trimmed = kw.trim();
    if (!keywordColorMap.has(trimmed)) {
      keywordColorMap.set(trimmed, KEYWORD_COLORS[idx % KEYWORD_COLORS.length]);
    }
  });

  const renderWord = (word: string, idx: number) => {
    // 단어에서 구두점 제거 후 키워드 매칭
    const bare = word.replace(/[!?.,·…]/g, "").trim();
    const color = keywordColorMap.get(bare) ?? keywordColorMap.get(word.trim());
    const isHighlighted = keywordSet.has(bare) || keywordSet.has(word.trim());

    return (
      <span
        key={idx}
        style={{ color: isHighlighted && color ? color : "#111" }}
      >
        {word}
        {idx < words.length - 1 ? " " : ""}
      </span>
    );
  };

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: 536, // 1920 × 0.28
        backgroundColor: "#ffffff",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "32px 40px",
        boxSizing: "border-box",
      }}
    >
      <p
        style={{
          fontFamily: "'Noto Sans KR', 'Apple SD Gothic Neo', '맑은 고딕', sans-serif",
          fontWeight: 900,
          fontSize: 72,
          lineHeight: 1.3,
          color: "#111",
          textAlign: "center",
          margin: 0,
          wordBreak: "keep-all",
        }}
      >
        {words.map(renderWord)}
      </p>
    </div>
  );
};
