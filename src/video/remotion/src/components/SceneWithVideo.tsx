import React from "react";
import {
  AbsoluteFill,
  OffthreadVideo,
  staticFile,
} from "remotion";
import { SceneText } from "./SceneText";

// Must match CELEBRITY_IMAGE_TOP / CELEBRITY_IMAGE_BOTTOM in ShortsComposition.tsx
const VIDEO_TOP_INSET    = 415;
const VIDEO_BOTTOM_INSET = 330;

interface SceneWithVideoProps {
  videoFile: string;
  scene: any;
  emotion: string;
  contained?: boolean;
  // 041: contained 모드에서 클립 위·아래 레터박스에 깔리는 캔버스 색.
  // 기본 검정 — V3.0 흰 캔버스(#F5F5F5)일 때만 넘겨받는다. 이 값을 안 주면
  // 기존 V2.1/V2.2 렌더와 완전히 동일하다.
  canvasColor?: string;
}

export const SceneWithVideo: React.FC<SceneWithVideoProps> = ({
  videoFile,
  scene,
  emotion,
  contained = false,
  canvasColor = "#000",
}) => {
  const topInset    = contained ? VIDEO_TOP_INSET    : 0;
  const bottomInset = contained ? VIDEO_BOTTOM_INSET : 0;
  const isDarkCanvas = canvasColor === "#000";

  return (
    <AbsoluteFill style={{ background: canvasColor }}>
      {/* News/AI video clip — when contained, insets top & bottom */}
      <div
        style={{
          position: "absolute",
          top: topInset,
          left: 0,
          right: 0,
          bottom: bottomInset,
          overflow: "hidden",
        }}
      >
        <OffthreadVideo
          src={staticFile(videoFile)}
          style={{
            width: "100%",
            height: "100%",
            // 2026-06-29 사용자 피드백: contained 모드의 contain(레터박스)는 16:9
            // 원본을 박스 안에 작게 띄워 가운데 너무 작게 보였음. cover로 전환해
            // 박스(insets로 정의된 영역)를 꽉 채움 — 인물이 크게 잡히고 좌우만 크롭.
            objectFit: "cover",
          }}
        />
        {/* Dark overlay for text readability — 자막이 영상 위에 얹히는 경우용.
            041: 밝은 캔버스에서는 이 오버레이가 클립 패딩까지 회색으로 만들어
            영상 위·아래에 띠가 생긴다. 자막도 캔버스 쪽(레터박스 밖)에 있어
            가독성 목적이 없으므로 생략한다. */}
        {isDarkCanvas && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              background:
                "linear-gradient(to bottom, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.1) 40%, rgba(0,0,0,0.5) 100%)",
            }}
          />
        )}
      </div>

      {/* Text overlay — always full canvas */}
      <SceneText scene={scene} emotion={emotion} />
    </AbsoluteFill>
  );
};
