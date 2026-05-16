import React from "react";
import {
  AbsoluteFill,
  OffthreadVideo,
  staticFile,
} from "remotion";
import { SceneText } from "./SceneText";

interface SplitScreenSceneProps {
  /** Primary clip — top half (1080x960). */
  videoFile: string;
  /** Optional secondary clip — bottom half. If omitted, the primary clip is
   * shown both halves (used as a fallback for split-layout scenes that don't
   * have a separate secondary source). */
  secondaryVideoFile?: string;
  scene: any;
  emotion: string;
}

/**
 * Feature 011 V2 Phase B — 좌·우(과거/현재) 또는 상·하 분할 스크린 씬.
 *
 * 9:16 세로(1080x1920) 캔버스를 위·아래 반반으로 나눠 두 클립을 동시 재생.
 * 정치 모드의 "대조 연출" — 인물의 모순이나 상황 변화를 직관적으로 비교.
 *
 * 좌·우 분할 대신 상·하 분할인 이유: 9:16 세로 비율에서 좌·우는 각 클립이
 * 540x1920(매우 좁음)이 되어 인물·자막 가독성이 크게 떨어짐. 상·하 분할은
 * 각 클립이 1080x960으로 자연스러운 가로 비율을 유지.
 */
export const SplitScreenScene: React.FC<SplitScreenSceneProps> = ({
  videoFile,
  secondaryVideoFile,
  scene,
  emotion,
}) => {
  const secondary = secondaryVideoFile || videoFile;
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      {/* Top half — primary clip */}
      <div style={{
        position: "absolute",
        top: 0, left: 0,
        width: "100%", height: "50%",
        overflow: "hidden",
        borderBottom: "2px solid rgba(255,255,255,0.3)",
      }}>
        <OffthreadVideo
          src={staticFile(videoFile)}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
          muted
        />
      </div>

      {/* Bottom half — secondary clip */}
      <div style={{
        position: "absolute",
        bottom: 0, left: 0,
        width: "100%", height: "50%",
        overflow: "hidden",
      }}>
        <OffthreadVideo
          src={staticFile(secondary)}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
          muted
        />
      </div>

      {/* Dim overlay for text readability */}
      <AbsoluteFill style={{
        background: "linear-gradient(to bottom, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0.4) 50%, rgba(0,0,0,0.3) 100%)",
      }} />

      {/* Text overlay (uses V2 subtitle_color/emphasis from scene props) */}
      <SceneText scene={scene} emotion={emotion} />
    </AbsoluteFill>
  );
};
