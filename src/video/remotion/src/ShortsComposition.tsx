import React from "react";
import {
  AbsoluteFill,
  Img,
  Sequence,
  Audio,
  staticFile,
  useCurrentFrame,
  interpolate,
} from "remotion";
import { Background } from "./components/Background";
import { SceneText } from "./components/SceneText";
import type { ShortsScriptData } from "./types";
import { GRADIENT_THEMES } from "./types";

const FPS = 30;

interface SceneImage {
  sceneId: number;
  imageFile: string; // filename in public/
}

interface ShortsCompositionProps {
  scriptData: ShortsScriptData;
  audioFile: string;
  sceneImages?: SceneImage[];
}

export const ShortsComposition: React.FC<ShortsCompositionProps> = ({
  scriptData,
  audioFile,
  sceneImages = [],
}) => {
  const emotion =
    (scriptData.metadata as any).emotionType ||
    scriptData.metadata.emotion_type;
  const colors =
    scriptData.background.colors.length > 0
      ? scriptData.background.colors
      : GRADIENT_THEMES[emotion] || GRADIENT_THEMES.relatable;

  const imageMap = new Map<number, string>();
  for (const si of sceneImages) {
    imageMap.set(si.sceneId, si.imageFile);
  }

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {/* Default gradient background (shows when no scene image) */}
      <Background colors={colors} />

      {scriptData.scenes.map((scene) => {
        const startFrame = Math.round(scene.timestamp * FPS);
        const durationFrames = Math.round(scene.duration * FPS);
        const imageFile = imageMap.get(scene.id);

        return (
          <Sequence
            key={scene.id}
            from={startFrame}
            durationInFrames={durationFrames}
          >
            {imageFile ? (
              <SceneWithImage imageFile={imageFile} scene={scene} />
            ) : (
              <SceneText scene={scene} />
            )}
          </Sequence>
        );
      })}

      {audioFile && <Audio src={staticFile(audioFile)} />}
    </AbsoluteFill>
  );
};

const SceneWithImage: React.FC<{
  imageFile: string;
  scene: any;
}> = ({ imageFile, scene }) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Subtle zoom effect on the background image
  const scale = interpolate(frame, [0, 150], [1.0, 1.05], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill>
      {/* Manga illustration background */}
      <AbsoluteFill style={{ opacity }}>
        <Img
          src={staticFile(imageFile)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: `scale(${scale})`,
          }}
        />
        {/* Dark overlay for text readability */}
        <AbsoluteFill
          style={{
            background:
              "linear-gradient(to bottom, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0.1) 40%, rgba(0,0,0,0.6) 100%)",
          }}
        />
      </AbsoluteFill>

      {/* Text on top of image */}
      <SceneText scene={scene} />
    </AbsoluteFill>
  );
};
