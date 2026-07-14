import React from "react";

interface CaptionCue {
  startSec: number;
  endSec: number;
  text: string;
}

interface LiveCaptionProps {
  captions: CaptionCue[];
  frame: number;
  fps: number;
}

/**
 * 하단 ~22% 위치 (top 1497px = 1920 × 0.78) 실시간 자막.
 * 현재 frame/fps 기준 시간으로 cue 매칭. 미매칭 구간은 비표시.
 * 배경 박스 없음 — 흰 글자 + 검은 텍스트쉐도우 (겸손은힘들다 스타일).
 */
export const LiveCaption: React.FC<LiveCaptionProps> = ({
  captions,
  frame,
  fps,
}) => {
  const currentSec = frame / fps;

  const activeCue = captions.find(
    (cue) => currentSec >= cue.startSec && currentSec < cue.endSec
  );

  if (!activeCue) {
    return null;
  }

  return (
    <div
      style={{
        position: "absolute",
        top: 1497, // 1920 × 0.78
        left: 0,
        width: "100%",
        padding: "0 48px",
        boxSizing: "border-box",
        textAlign: "center",
      }}
    >
      <span
        style={{
          fontFamily: "'Noto Sans KR', 'Apple SD Gothic Neo', '맑은 고딕', sans-serif",
          fontWeight: 700,
          fontSize: 52,
          color: "#ffffff",
          textShadow:
            "-3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000, 3px 3px 0 #000",
          lineHeight: 1.35,
          wordBreak: "keep-all",
        }}
      >
        {activeCue.text}
      </span>
    </div>
  );
};
