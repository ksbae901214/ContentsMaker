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
import { Transition } from "./components/Transition";
import { SceneWithVideo } from "./components/SceneWithVideo";
import { SplitScreenScene } from "./components/SplitScreenScene";
import { Outro } from "./components/Outro";
import type { ShortsScriptData, TransitionType } from "./types";
import { GRADIENT_THEMES } from "./types";

const FPS = 30;
const OUTRO_DURATION_FRAMES = FPS * 4; // 4-second outro

interface SceneImage {
  sceneId: number;
  imageFile: string; // filename in public/
}

interface SceneVideo {
  sceneId: number;
  videoFile: string;
}

interface ShortsCompositionProps {
  scriptData: ShortsScriptData;
  audioFile: string;
  sceneImages?: SceneImage[];
  sceneVideos?: SceneVideo[];
  bgmFile?: string;
  // QW-07: hook 씬 동안만 재생되는 인트로 빌드업 BGM (선택).
  introBgmFile?: string;
  // Feature 009 political_pro: 화면 하단에 출처 표시 ("출처: youtube.com/...").
  // 비어있으면 표시 안 함.
  sourceLabel?: string;
}

export const ShortsComposition: React.FC<ShortsCompositionProps> = ({
  scriptData,
  audioFile,
  sceneImages = [],
  sceneVideos = [],
  bgmFile = "",
  introBgmFile = "",
  sourceLabel = "",
}) => {
  const emotion =
    (scriptData.metadata as any).emotionType ||
    scriptData.metadata.emotion_type;
  // Feature 009 political_pro: 모든 씬에 영상 클립이 깔리므로 배경 그라데이션 불필요.
  // 씬 사이가 깜빡일 때 빨강·주황 gradient(angry 테마)이 비치는 현상을 차단하기
  // 위해 검정 단색으로 강제 (2026-05-14 사용자 보고).
  const sourceType =
    (scriptData.metadata as any).sourceType ||
    (scriptData.metadata as any).source_type;
  const isPoliticalPro = sourceType === "political_pro";
  const colors = isPoliticalPro
    ? ["#000000", "#000000"]
    : scriptData.background.colors.length > 0
      ? scriptData.background.colors
      : GRADIENT_THEMES[emotion as keyof typeof GRADIENT_THEMES] || GRADIENT_THEMES.relatable;

  const imageMap = new Map<number, string>();
  for (const si of sceneImages) {
    imageMap.set(si.sceneId, si.imageFile);
  }

  const videoMap = new Map<number, string>();
  for (const sv of sceneVideos) {
    videoMap.set(sv.sceneId, sv.videoFile);
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
        const videoFile = videoMap.get(scene.id);
        const transition = scene.transition;
        const transitionType: TransitionType = (transition?.type as TransitionType) ?? "fade";
        const transitionDur = Math.round((transition?.duration ?? 0.5) * FPS);

        // Feature 011 V2 Phase B: visual_layout="split" → SplitScreenScene 사용.
        // secondary_clip_path가 있으면 그 클립을, 없으면 primary clip 한 번 더.
        const visualLayout = (scene as any).visualLayout || (scene as any).visual_layout;
        const secondaryClipPath = (scene as any).secondaryClipPath || (scene as any).secondary_clip_path;
        const isSplit = visualLayout === "split" && !!videoFile;

        const content = isSplit ? (
          <SplitScreenScene
            videoFile={videoFile!}
            secondaryVideoFile={secondaryClipPath || undefined}
            scene={scene}
            emotion={emotion}
          />
        ) : videoFile ? (
          <SceneWithVideo videoFile={videoFile} scene={scene} emotion={emotion} />
        ) : imageFile ? (
          <SceneWithImage imageFile={imageFile} scene={scene} emotion={emotion} />
        ) : (
          <SceneText scene={scene} emotion={emotion} />
        );

        return (
          <Sequence
            key={scene.id}
            from={startFrame}
            durationInFrames={durationFrames}
          >
            {transition ? (
              <Transition type={transitionType} durationFrames={transitionDur}>
                {content}
              </Transition>
            ) : (
              content
            )}
          </Sequence>
        );
      })}

      {/* Fixed title bar at top — visible during all content scenes */}
      <Sequence from={0} durationInFrames={contentEndFrame}>
        <TitleBar title={title} />
      </Sequence>

      {/* Feature 009: 화면 하단 출처 표시 (political_pro 모드 등에서 source URL 명시) */}
      {sourceLabel && (
        <Sequence from={0} durationInFrames={contentEndFrame}>
          <SourceAttribution label={sourceLabel} />
        </Sequence>
      )}

      {/* Outro: standardized CTA — see src/video/outro_template.py */}
      <Sequence from={contentEndFrame} durationInFrames={OUTRO_DURATION_FRAMES}>
        <Outro />
      </Sequence>

      {audioFile && <Audio src={staticFile(audioFile)} />}
      {bgmFile && <Audio src={staticFile(bgmFile)} volume={0.15} loop />}

      {/* QW-07: hook 씬 동안만 인트로 빌드업 BGM 재생 */}
      {introBgmFile && (() => {
        const hookScene = scriptData.scenes.find((s: any) => s.hook === true);
        if (!hookScene) return null;
        const startFrame = Math.round(hookScene.timestamp * FPS);
        const durationFrames = Math.round(hookScene.duration * FPS);
        return (
          <Sequence from={startFrame} durationInFrames={durationFrames}>
            <Audio
              src={staticFile("bgm/" + introBgmFile)}
              volume={0.35}
            />
          </Sequence>
        );
      })()}

      {/* Per-scene sound effects */}
      {scriptData.scenes.map((scene) => {
        const sfxList = scene.sfx || [];
        const sceneStart = Math.round(scene.timestamp * FPS);
        return sfxList.map((sfx, idx) => {
          const offsetFrames = Math.round((sfx.offset_ms || 0) / 1000 * FPS);
          return (
            <Sequence
              key={`sfx-${scene.id}-${idx}`}
              from={sceneStart + offsetFrames}
              durationInFrames={Math.round(scene.duration * FPS)}
            >
              <Audio
                src={staticFile(sfx.name + ".mp3")}
                volume={sfx.volume ?? 0.2}
              />
            </Sequence>
          );
        });
      })}
    </AbsoluteFill>
  );
};

const SourceAttribution: React.FC<{ label: string }> = ({ label }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 15], [0, 0.85], {
    extrapolateRight: "clamp",
  });
  // 위치 조정 히스토리:
  // 2026-05-13: paddingBottom: 80 (너무 아래, 자막과 겹침)
  // 2026-05-14: paddingBottom: 400 (자막 영역 위로 이동, 사용자 피드백 반영)
  // 2026-05-16: paddingBottom: 150 (사용자 요청 — 조금 더 아래로)
  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        pointerEvents: "none",
        paddingBottom: 150,
      }}
    >
      <div
        style={{
          opacity,
          padding: "10px 22px",
          background: "rgba(0,0,0,0.7)",
          borderRadius: 8,
          maxWidth: "92%",
        }}
      >
        <div
          style={{
            fontSize: 30,
            color: "#FFFFFF",
            fontFamily: "Noto Sans KR, sans-serif",
            textShadow: "1px 1px 3px rgba(0,0,0,0.85)",
            textAlign: "center",
            wordBreak: "keep-all",
            lineHeight: 1.3,
          }}
        >
          {label}
        </div>
      </div>
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
          marginTop: 180,
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
          {title}
        </div>
      </div>
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
