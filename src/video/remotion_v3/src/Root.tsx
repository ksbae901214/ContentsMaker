import React from "react";
import { Composition } from "remotion";
import { MomentComposition } from "./MomentComposition";
import type { MomentShortsProps } from "./types";

const FPS = 30;

const defaultProps: MomentShortsProps = {
  clipFileName: "clip.mp4",
  hookQuestion: "이 순간 무슨 일이 있었을까?",
  hookKeywords: ["무슨"],
  captions: [],
  sourceLabel: "출처: 테스트 (2026.06.11)",
  durationSec: 30,
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="MomentShorts"
      component={MomentComposition}
      durationInFrames={FPS * 60}
      fps={FPS}
      width={1080}
      height={1920}
      defaultProps={defaultProps}
    />
  );
};
