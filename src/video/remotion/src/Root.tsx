import React from "react";
import { Composition } from "remotion";
import { ShortsComposition } from "./ShortsComposition";
import type { ShortsScriptData } from "./types";

const FPS = 30;

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
        durationInFrames={FPS * 60}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          scriptData: defaultScript,
          audioFile: "",
        }}
      />
    </>
  );
};
