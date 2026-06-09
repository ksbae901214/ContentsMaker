/**
 * V3 메인 Composition.
 *
 * 구성:
 *  1. Background (그라데이션, 풀스크린)
 *  2. 씬별 <Sequence> 직접 연결 (전환 효과 없음 — FR-035)
 *     - visualLayout 분기:
 *       - "normal"   → TalkingHeadScene
 *       - "vs_card"  → VsCardScene
 *       - "grid_2x2" → ComparisonGridScene
 *       - "data_card"→ DataCardScene
 *     - 씬 내부에 SubtitleBlock 오버레이
 *  3. 영상 전체 PinnedHeadline (FR-017 상단 노란 박스 고정)
 *  4. 영상 전체 LetterboxFrame (FR-019 출처 라벨)
 *  5. 마지막 Outro (검정 + CTA, 하드 컷)
 *  6. <Audio> TTS 단일 트랙 (FR-034 효과음 0)
 *
 * 락인 가드:
 *  - <Audio>는 정확히 1개 (TTS audio.mp3)
 *  - <OffthreadVideo muted /> 강제 (원본 클립 native audio 차단)
 *  - 씬 entrance opacity interpolation 금지
 *  - 그라데이션 인터스티셜 컴포넌트 금지
 */
import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  staticFile,
  useVideoConfig,
} from "remotion";
import { Background } from "./components/Background";
import { ComparisonGridScene } from "./components/ComparisonGridScene";
import { DataCardScene } from "./components/DataCardScene";
import { LetterboxFrame } from "./components/LetterboxFrame";
import { Outro } from "./components/Outro";
import { PinnedHeadline } from "./components/PinnedHeadline";
import { SubtitleBlock } from "./components/SubtitleBlock";
import { TalkingHeadScene } from "./components/TalkingHeadScene";
import { VsCardScene } from "./components/VsCardScene";
import { loadFonts } from "./loadFonts";
import type {
  JpoliticsCompositionProps,
  JpoliticsSceneProps,
} from "./types";

const OUTRO_DURATION_SEC = 1.5;

type SceneVisualProps = {
  scene: JpoliticsSceneProps;
  backgroundColors: [string, string];
};

/**
 * visualLayout 라우터. 씬 시각 컨텐츠만 렌더(자막은 상위에서 별도 오버레이).
 */
const SceneVisual: React.FC<SceneVisualProps> = ({
  scene,
  backgroundColors,
}) => {
  switch (scene.visualLayout) {
    case "vs_card":
      return (
        <VsCardScene comparisonCards={scene.comparisonCards ?? []} />
      );
    case "grid_2x2":
      return (
        <ComparisonGridScene
          comparisonCards={scene.comparisonCards ?? []}
          dataEmphasisColor={scene.dataEmphasisColor}
        />
      );
    case "data_card":
      return (
        <DataCardScene
          comparisonCards={scene.comparisonCards ?? []}
          dataEmphasisColor={scene.dataEmphasisColor}
        />
      );
    case "normal":
    default:
      return (
        <TalkingHeadScene
          clipPath={scene.clipPath}
          backgroundColors={backgroundColors}
        />
      );
  }
};

export const JpoliticsComposition: React.FC<JpoliticsCompositionProps> = ({
  metadata,
  scenes,
  audio,
  background,
  headlinePin,
}) => {
  const { fps } = useVideoConfig();

  // 폰트 로딩 (헤드라인/자막 표시 전).
  React.useEffect(() => {
    loadFonts().catch(() => {
      /* 폰트 실패해도 시스템 폴백 사용 */
    });
  }, []);

  const outroFrames = Math.round(OUTRO_DURATION_SEC * fps);

  // 마지막 씬 종료 프레임 = 모든 씬 누적.
  const scenesTotalFrames = scenes.reduce(
    (acc, s) => acc + Math.round(s.duration * fps),
    0,
  );

  return (
    <AbsoluteFill style={{ background: "#000" }}>
      {/* 1. 배경 그라데이션 (영상 전체) */}
      <Background colors={background.colors} />

      {/* 2. 씬별 시각 콘텐츠 + 자막 — 하드 컷, 전환 효과 없음 */}
      {scenes.map((scene) => {
        const startFrame = Math.round(scene.timestamp * fps);
        const durationFrames = Math.max(1, Math.round(scene.duration * fps));
        return (
          <Sequence
            key={scene.id}
            from={startFrame}
            durationInFrames={durationFrames}
            name={`scene-${scene.id}-${scene.visualLayout}`}
          >
            <SceneVisual
              scene={scene}
              backgroundColors={background.colors}
            />
            <SubtitleBlock
              text={scene.text}
              color={scene.subtitleColor}
              emphasis={scene.subtitleEmphasis}
            />
          </Sequence>
        );
      })}

      {/* 3. 영상 전체 PinnedHeadline 고정 (FR-017) */}
      <PinnedHeadline headline={headlinePin} />

      {/* 4. 영상 전체 LetterboxFrame 출처 라벨 (FR-019) */}
      <LetterboxFrame sourceLabel={metadata.sourceLabel} />

      {/* 5. Outro — 마지막 씬 종료 직후 컷 등장 (FR-035) */}
      <Sequence
        from={scenesTotalFrames}
        durationInFrames={outroFrames}
        name="outro"
      >
        <Outro ctaText="구독·좋아요·알림 설정 부탁드립니다" />
      </Sequence>

      {/* 6. TTS 단일 오디오 트랙 (FR-034 효과음 0 락인) */}
      <Audio src={staticFile(audio.audioPath)} />
    </AbsoluteFill>
  );
};
