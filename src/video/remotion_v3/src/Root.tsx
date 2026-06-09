/**
 * V3 Root — Composition 등록.
 *
 * 1080x1920 (9:16), 30fps.
 * defaultProps는 미리보기/테스트용 — 실제 렌더 시 Python이 --props로 주입.
 */
import React from "react";
import { Composition } from "remotion";
import { JpoliticsComposition } from "./JpoliticsComposition";
import type { JpoliticsCompositionProps } from "./types";

const defaultPropsTalkingHead: JpoliticsCompositionProps = {
  metadata: {
    title: "샘플 영상",
    sourceType: "jpolitics_youtube",
    sourceUrl: "https://www.youtube.com/watch?v=sample",
    sourceLabel: "출처: MBC 라디오",
    durationSec: 30,
    createdAt: "2026-06-05T00:00:00Z",
  },
  scenes: [
    {
      id: 0,
      timestamp: 0,
      duration: 3,
      type: "title",
      text: "이게 말이 되나요",
      voiceText: "이게 말이 되는 상황입니까?",
      visualLayout: "normal",
      subtitleColor: "yellow",
      subtitleEmphasis: true,
      dataEmphasisColor: "red",
    },
    {
      id: 1,
      timestamp: 3,
      duration: 4,
      type: "body",
      text: "오늘은 이 사건을 살펴봅니다",
      voiceText: "오늘은 이 사건을 살펴보겠습니다.",
      visualLayout: "normal",
      subtitleColor: "white",
      subtitleEmphasis: false,
      dataEmphasisColor: "red",
    },
  ],
  audio: {
    ttsVoice: "ko-KR-InJoonNeural",
    ttsRate: "+22%",
    ttsScript: "이게 말이 되는 상황입니까? 오늘은 이 사건을 살펴보겠습니다.",
    audioPath: "audio.mp3",
    sceneTimings: [
      { sceneId: 0, startMs: 0, endMs: 3000 },
      { sceneId: 1, startMs: 3000, endMs: 7000 },
    ],
  },
  background: {
    type: "gradient",
    colors: ["#1a1a2e", "#16213e"],
  },
  headlinePin: "충격! 정치 비리",
};

// 30 fps × 30 sec = 900 frames (기본). 실제 렌더 시 calculateMetadata로 동적 결정 가능.
const DEFAULT_DURATION_FRAMES = 900;

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="JpoliticsShorts"
        component={JpoliticsComposition}
        durationInFrames={DEFAULT_DURATION_FRAMES}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={defaultPropsTalkingHead}
        calculateMetadata={({ props }) => {
          const durationSec = props.metadata?.durationSec ?? 30;
          return {
            durationInFrames: Math.max(1, Math.floor(durationSec * 30)),
          };
        }}
      />
    </>
  );
};
