import React from "react";
import { Composition } from "remotion";
import { ShortsComposition } from "./ShortsComposition";
import { DemShortsComposition } from "./DemShortsComposition";
import type { ShortsScriptData } from "./types";
import { InfoShortsComposition } from "./info/InfoShortsComposition";
import type { InfoShortsProps } from "./info/InfoShortsComposition";

const FPS = 30;

const defaultInfoProps: InfoShortsProps = {
  titleLines: ["정보쇼츠 미리보기"],
  watermark: "made by 정보쇼츠",
  canvasColor: "#F6EFE1",
  images: [],
  captions: [{ lines: ["자막 미리보기입니다."], startMs: 0, endMs: 5000 }],
  durationMs: 5000,
  audioFile: "",
};

const defaultDemShortsPreset = {
  id: "default",
  fontFamily: "Pretendard, -apple-system, sans-serif",
  baseFontSize: 64,
  color: "#FFFFFF",
  highlightColor: "#FFC107",
  strokeColor: "#000000",
  strokeWidth: 3,
  background: "rgba(0,0,0,0.6)",
  textAlign: "center" as const,
  paddingPx: 20,
  position: "bottom" as const,
  maxLines: 2,
  lineHeight: 1.2,
  bold: true,
};

const defaultScript: ShortsScriptData = {
  metadata: {
    title: "샘플 쇼츠",
    emotion_type: "relatable",
    duration: 10,
    source_url: "",
  },
  scenes: [
    {
      id: 1,
      timestamp: 0,
      duration: 5,
      type: "title",
      text: "블라인드 쇼츠",
      voice_text: "블라인드 쇼츠",
      emphasis: "high",
    },
    {
      id: 2,
      timestamp: 5,
      duration: 5,
      type: "body",
      text: "테스트 본문입니다",
      voice_text: "테스트 본문입니다",
      emphasis: "medium",
    },
  ],
  audio: { tts_script: "", voice: "", rate: "", pitch: "" },
  background: { type: "gradient", colors: [] },
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="BlindShorts"
        component={ShortsComposition}
        durationInFrames={FPS * 120}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          scriptData: defaultScript,
          audioFile: "",
        }}
      />
      <Composition
        id="DemShorts"
        component={DemShortsComposition}
        durationInFrames={FPS * 60}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          videoFile: "",
          commentaryBlocks: [],
          subtitlePreset: defaultDemShortsPreset,
          ttsFile: undefined,
          bgmFile: undefined,
          sourceLabelText: "NATV 국회방송",
        }}
      />
      {/* 045 정보쇼츠 V1.0 — 길이는 props.durationMs 로 정하고 렌더러가 --frames 로 자른다 */}
      <Composition
        id="InfoShorts"
        component={InfoShortsComposition}
        durationInFrames={FPS * 200}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={defaultInfoProps}
      />
    </>
  );
};
