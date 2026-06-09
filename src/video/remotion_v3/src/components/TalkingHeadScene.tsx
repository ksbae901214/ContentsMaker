/**
 * V3 TalkingHeadScene — visualLayout = "normal".
 *
 * clipPath 있으면 원본 클립 풀스크린 (<OffthreadVideo muted />).
 * 없으면 그라데이션 배경 폴백.
 *
 * 락인:
 *  - FR-034: muted 강제 (TTS와 충돌 방지).
 *  - FR-035: 엔트런스 페이드인 없음 (하드 컷).
 */
import React from "react";
import { AbsoluteFill, OffthreadVideo, staticFile } from "remotion";
import { Background } from "./Background";

type TalkingHeadSceneProps = {
  clipPath?: string;
  backgroundColors: [string, string];
};

export const TalkingHeadScene: React.FC<TalkingHeadSceneProps> = ({
  clipPath,
  backgroundColors,
}) => {
  if (!clipPath) {
    return <Background colors={backgroundColors} />;
  }

  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <OffthreadVideo
        src={staticFile(clipPath)}
        muted
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
        }}
      />
    </AbsoluteFill>
  );
};
