import React from "react";
import { AbsoluteFill, Sequence, Audio, staticFile } from "remotion";
import { Background } from "./components/Background";
import { SceneText } from "./components/SceneText";
import type { ShortsScriptData } from "./types";
import { GRADIENT_THEMES } from "./types";

const FPS = 30;

interface ShortsCompositionProps {
  scriptData: ShortsScriptData;
  audioFile: string;
}

export const ShortsComposition: React.FC<ShortsCompositionProps> = ({
  scriptData,
  audioFile,
}) => {
  const emotion = (scriptData.metadata as any).emotionType || scriptData.metadata.emotion_type;
  const colors =
    scriptData.background.colors.length > 0
      ? scriptData.background.colors
      : GRADIENT_THEMES[emotion] || GRADIENT_THEMES.relatable;

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <Background colors={colors} />

      {scriptData.scenes.map((scene) => {
        const startFrame = Math.round(scene.timestamp * FPS);
        const durationFrames = Math.round(scene.duration * FPS);

        return (
          <Sequence
            key={scene.id}
            from={startFrame}
            durationInFrames={durationFrames}
          >
            <SceneText scene={scene} />
          </Sequence>
        );
      })}

      {audioFile && <Audio src={staticFile(audioFile)} />}
    </AbsoluteFill>
  );
};
