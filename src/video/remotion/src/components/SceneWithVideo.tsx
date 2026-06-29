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
}

export const SceneWithVideo: React.FC<SceneWithVideoProps> = ({
  videoFile,
  scene,
  emotion,
  contained = false,
}) => {
  const topInset    = contained ? VIDEO_TOP_INSET    : 0;
  const bottomInset = contained ? VIDEO_BOTTOM_INSET : 0;

  return (
    <AbsoluteFill style={{ background: "#000" }}>
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
        {/* Dark overlay for text readability */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "linear-gradient(to bottom, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.1) 40%, rgba(0,0,0,0.5) 100%)",
          }}
        />
      </div>

      {/* Text overlay — always full canvas */}
      <SceneText scene={scene} emotion={emotion} />
    </AbsoluteFill>
  );
};
