import React from "react";
import {
  AbsoluteFill,
  OffthreadVideo,
  staticFile,
} from "remotion";
import { SceneText } from "./SceneText";

interface SceneWithVideoProps {
  videoFile: string;
  scene: any;
  emotion: string;
}

export const SceneWithVideo: React.FC<SceneWithVideoProps> = ({
  videoFile,
  scene,
  emotion,
}) => {
  // 2026-05-14: 씬 시작 시 15프레임 fade-in을 제거.
  // 페이드인 동안 배경 gradient(angry=빨강·주황 등)이 비쳐서 씬 사이가 깜빡이는
  // 현상이 사용자 보고됨. 즉시 풀 opacity로 표시 → 컷 전환에 가까운 매끄러운 흐름.
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      {/* AI video clip background */}
      <AbsoluteFill>
        <OffthreadVideo
          src={staticFile(videoFile)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
        {/* Dark overlay for text readability */}
        <AbsoluteFill
          style={{
            background:
              "linear-gradient(to bottom, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.1) 40%, rgba(0,0,0,0.5) 100%)",
          }}
        />
      </AbsoluteFill>

      {/* Text overlay */}
      <SceneText scene={scene} emotion={emotion} />
    </AbsoluteFill>
  );
};
