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
              <SceneWithImage imageFile={imageFile} scene={scene} />
            ) : (
              <SceneText scene={scene} />
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
        }}
      >
        <span
          style={{
            fontSize: 42,
            fontWeight: 800,
            color: "#FFFFFF",
            fontFamily: "Noto Sans KR, sans-serif",
            textShadow: "2px 2px 6px rgba(0,0,0,0.8)",
          }}
        >
          [블라인드] {title}
        </span>
      </div>
    </AbsoluteFill>
  );
};

const OutroScene: React.FC = () => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });
  const scale = interpolate(frame, [0, 20], [0.8, 1], {
    extrapolateRight: "clamp",
  });

  // Pulsing animation for the icons
  const pulse = interpolate(frame, [30, 45, 60, 75, 90, 105, 120], [1, 1.15, 1, 1.15, 1, 1.15, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        background: "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
        opacity,
      }}
    >
      <div
        style={{
          transform: `scale(${scale})`,
          textAlign: "center",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 40,
        }}
      >
        {/* Icons row */}
        <div
          style={{
            display: "flex",
            gap: 60,
            transform: `scale(${pulse})`,
          }}
        >
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 80 }}>👍</div>
            <div style={{ fontSize: 28, color: "#fff", fontFamily: "Noto Sans KR, sans-serif", marginTop: 8 }}>좋아요</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 80 }}>🔔</div>
            <div style={{ fontSize: 28, color: "#fff", fontFamily: "Noto Sans KR, sans-serif", marginTop: 8 }}>알림설정</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 80 }}>💬</div>
            <div style={{ fontSize: 28, color: "#fff", fontFamily: "Noto Sans KR, sans-serif", marginTop: 8 }}>댓글</div>
          </div>
        </div>

        {/* Subscribe button */}
        <div
          style={{
            background: "#FF0000",
            borderRadius: 16,
            padding: "20px 60px",
            display: "flex",
            alignItems: "center",
            gap: 12,
          }}
        >
          <div style={{ fontSize: 52, fontWeight: 800, color: "#fff", fontFamily: "Noto Sans KR, sans-serif" }}>
            구독
          </div>
        </div>

        {/* Bottom text */}
        <div
          style={{
            fontSize: 36,
            color: "rgba(255,255,255,0.7)",
            fontFamily: "Noto Sans KR, sans-serif",
            marginTop: 20,
          }}
        >
          구독과 좋아요는 큰 힘이 됩니다
        </div>
      </div>
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
