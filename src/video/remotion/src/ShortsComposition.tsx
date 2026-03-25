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
const OUTRO_DURATION_FRAMES = FPS * 4; // 4-second outro

interface SceneImage {
  sceneId: number;
  imageFile: string; // filename in public/
}

interface ShortsCompositionProps {
  scriptData: ShortsScriptData;
  audioFile: string;
  sceneImages?: SceneImage[];
  bgmFile?: string;
}

export const ShortsComposition: React.FC<ShortsCompositionProps> = ({
  scriptData,
  audioFile,
  sceneImages = [],
  bgmFile = "",
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

  const title = scriptData.metadata.title;

  // Calculate content end frame for the fixed title bar duration
  const lastScene = scriptData.scenes[scriptData.scenes.length - 1];
  const contentEndFrame = lastScene
    ? Math.round((lastScene.timestamp + lastScene.duration) * FPS)
    : 0;

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
              <SceneWithImage imageFile={imageFile} scene={scene} emotion={emotion} />
            ) : (
              <SceneText scene={scene} emotion={emotion} />
            )}
          </Sequence>
        );
      })}

      {/* Fixed title bar at top — visible during all content scenes */}
      <Sequence from={0} durationInFrames={contentEndFrame}>
        <TitleBar title={title} />
      </Sequence>

      {/* Outro: Subscribe / Like / Bell */}
      <Sequence from={contentEndFrame} durationInFrames={OUTRO_DURATION_FRAMES}>
        <OutroScene />
      </Sequence>

      {audioFile && <Audio src={staticFile(audioFile)} />}
      {bgmFile && <Audio src={staticFile(bgmFile)} volume={0.15} loop />}
    </AbsoluteFill>
  );
};

const TitleBar: React.FC<{ title: string }> = ({ title }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-start",
        alignItems: "center",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          opacity,
          marginTop: 80,
          padding: "16px 40px",
          background: "rgba(0,0,0,0.6)",
          borderRadius: 12,
          maxWidth: "90%",
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: 75,
            fontWeight: 800,
            color: "#FFFFFF",
            fontFamily: "Noto Sans KR, sans-serif",
            textShadow: "2px 2px 6px rgba(0,0,0,0.8)",
            lineHeight: 1.3,
          }}
        >
          [블라인드]{"\n"}{title}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const OutroScene: React.FC = () => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {/* Background outro image (public/outro.png) */}
      <AbsoluteFill style={{ opacity }}>
        <Img
          src={staticFile("outro.png")}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      </AbsoluteFill>

      {/* Overlay text at bottom */}
      <AbsoluteFill
        style={{
          justifyContent: "flex-end",
          alignItems: "center",
          opacity,
        }}
      >
        <div
          style={{
            marginBottom: 200,
            padding: "16px 40px",
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontSize: 38,
              fontWeight: 700,
              color: "#FFFFFF",
              fontFamily: "Noto Sans KR, sans-serif",
              textShadow: "2px 2px 8px rgba(0,0,0,0.8)",
              lineHeight: 1.6,
            }}
          >
            구독과 좋아요를 눌러주시면{"\n"}더 많은 영상을 볼 수 있습니다
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const SceneWithImage: React.FC<{
  imageFile: string;
  scene: any;
  emotion: string;
}> = ({ imageFile, scene, emotion }) => {
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
      <SceneText scene={scene} emotion={emotion} />
    </AbsoluteFill>
  );
};
