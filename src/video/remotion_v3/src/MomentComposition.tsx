import React from "react";
import { AbsoluteFill, OffthreadVideo, staticFile, useCurrentFrame } from "remotion";
import { HookCard } from "./components/HookCard";
import { LiveCaption } from "./components/LiveCaption";
import { SourceLabel } from "./components/SourceLabel";
import type { MomentShortsProps } from "./types";

const FPS = 30;
const HOOK_DURATION_FRAMES = FPS * 2; // 2초 하드 컷, fade 없음

export const MomentComposition: React.FC<MomentShortsProps> = ({
  clipFileName,
  hookQuestion,
  hookKeywords,
  captions,
  sourceLabel,
}) => {
  const frame = useCurrentFrame();
  const showHook = frame < HOOK_DURATION_FRAMES;

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {/* 풀블리드 원본 클립 — 항상 재생, 오디오는 클립 원본 트랙 1개만 */}
      <OffthreadVideo
        src={staticFile(clipFileName)}
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
      />

      {/* 훅 카드 (0~2초) — 하드 컷, 전환 효과 0 */}
      {showHook && (
        <HookCard question={hookQuestion} keywords={hookKeywords} />
      )}

      {/* 실시간 자막 — cue 없는 구간 비표시 */}
      <LiveCaption captions={captions} frame={frame} fps={FPS} />

      {/* 출처 라벨 — 최하단 고정 */}
      <SourceLabel label={sourceLabel} />
    </AbsoluteFill>
  );
};
