import React from "react";
import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
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
import { PersonBadge } from "./components/PersonBadge";
import { NewsCardLayer, NEWS_BOX_TOP } from "./components/NewsCardLayer";
import type { NewsCardData } from "./components/NewsCardLayer";
import { EvidenceLayer, EvidenceMedia } from "./components/EvidenceLayer";
import type { EvidenceLayerData } from "./components/EvidenceLayer";
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
  // 2026-06-01 사용자 피드백: 씬별 클립을 끊지 않고 단일 연속 영상을
  // 콘텐츠 전체 구간에 깔고 그 위에 텍스트 자막만 씬별로 오버레이.
  // 비어있으면 기존 동작(씬별 sceneVideos / 그라데이션).
  backgroundVideoFile?: string;
  // 041 V3.0 인물 프로필 옵트인. 전부 비어 있으면 037 규격(Noto Sans KR 100px,
  // 배지 없음)이 그대로 유지된다 — V2.1/V2.2 렌더 경로는 무변경.
  headlineFont?: string;
  headlineLetterSpacing?: number;
  personBadge?: string;
  // political_pro/celebrity 의 배경 검정 강제를 푸는 옵트인. 기본 false 라
  // bg_colors 를 적어 둔 기존 config 의 동작은 그대로다.
  respectBackgroundColors?: boolean;
  // 헤드라인 1열 + 인물 배지 글자색. "" 면 기존 흰색(037 규격).
  headlineColor?: string;
  // 제목·인물 배지의 반투명 검정 박스. 밝은 캔버스에서는 회색으로 보인다.
  overlayBoxes?: boolean;
  // 042 V4.0 옵트인. 커스텀 서체 헤드라인의 외곽선·그림자를 끈다 (궁서 전용 보강).
  headlinePlain?: boolean;
  // 배지 박스를 제목 박스와 따로 정한다. null/undefined 면 overlayBoxes 를 따른다.
  badgeBoxed?: boolean | null;
  // 사진 슬라이드 뉴스 카드. 지정 시 씬별 비주얼 대신 NewsCardLayer 가 그린다.
  newsCard?: NewsCardData;
  // 043 V5.0 증거 삽입형. 지정 시 씬 영상은 미디어 박스에만 깔리고 헤드라인·자막·
  // 증거 카드는 EvidenceLayer 가 그린다. 미지정이면 기존 경로와 완전히 동일.
  evidenceLayer?: EvidenceLayerData;
}

export const ShortsComposition: React.FC<ShortsCompositionProps> = ({
  scriptData,
  audioFile,
  sceneImages = [],
  sceneVideos = [],
  bgmFile = "",
  introBgmFile = "",
  sourceLabel = "",
  backgroundVideoFile = "",
  headlineFont = "",
  headlineLetterSpacing = 0,
  personBadge = "",
  respectBackgroundColors = false,
  headlineColor = "",
  overlayBoxes = true,
  headlinePlain = false,
  badgeBoxed = null,
  newsCard,
  evidenceLayer,
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
  const isCelebrity = sourceType === "celebrity";
  // 041: respectBackgroundColors 는 이 강제를 푸는 옵트인 (V3.0 흰 배경).
  const colors = (isPoliticalPro || isCelebrity) && !respectBackgroundColors
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

  // 단일 연속 배경 영상이 설정되면 씬별 video는 무시하고 텍스트만 오버레이.
  const useContinuousVideo = !!backgroundVideoFile;

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {/* Default gradient background (shows when no scene image) */}
      <Background colors={colors} />

      {/* Continuous background video — single OffthreadVideo for entire content. */}
      {useContinuousVideo && (
        <Sequence from={0} durationInFrames={contentEndFrame}>
          <AbsoluteFill style={{ background: "#000" }}>
            <OffthreadVideo
              src={staticFile(backgroundVideoFile)}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
              }}
            />
            {/* Dark overlay for subtitle readability — same gradient as SceneWithVideo. */}
            <AbsoluteFill
              style={{
                background:
                  "linear-gradient(to bottom, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.1) 40%, rgba(0,0,0,0.5) 100%)",
              }}
            />
          </AbsoluteFill>
        </Sequence>
      )}

      {/* 042: 뉴스 카드는 사진·자막을 씬과 다른 시계로 그린다 — 씬 비주얼 생략 */}
      {!newsCard && scriptData.scenes.map((scene) => {
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

        // 연속 배경 영상이 깔린 경우 씬별 영상/이미지는 건너뛰고 자막만 오버레이.
        const content = evidenceLayer ? (
          <EvidenceMedia
            videoFile={videoFile}
            imageFile={imageFile}
            durationFrames={durationFrames}
            zoom={evidenceLayer.framing?.find((f) => f.sceneId === scene.id)?.zoom}
            focusX={evidenceLayer.framing?.find((f) => f.sceneId === scene.id)?.focusX}
          />
        ) : useContinuousVideo ? (
          <SceneText scene={scene} emotion={emotion} />
        ) : isSplit ? (
          <SplitScreenScene
            videoFile={videoFile!}
            secondaryVideoFile={secondaryClipPath || undefined}
            scene={scene}
            emotion={emotion}
          />
        ) : videoFile ? (
          <SceneWithVideo
            videoFile={videoFile}
            scene={scene}
            emotion={emotion}
            contained={true}
            // 041: SceneWithVideo 는 캔버스를 자기 배경색으로 덮는다 — 흰 캔버스를
            // 쓰는 포맷에서는 그 색을 넘겨야 레터박스가 흰색으로 남는다.
            canvasColor={respectBackgroundColors ? colors[0] : undefined}
          />
        ) : imageFile ? (
          <SceneWithImage imageFile={imageFile} scene={scene} emotion={emotion} contained={isCelebrity} />
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

      {newsCard && (
        <NewsCardLayer
          card={newsCard}
          canvasColor={colors[0]}
          contentEndFrame={contentEndFrame}
        />
      )}

      {evidenceLayer && (
        <EvidenceLayer layer={evidenceLayer} contentEndFrame={contentEndFrame} />
      )}

      {/* Fixed title bar at top — visible during all content scenes.
          043: EvidenceLayer 는 자기 2줄 투톤 헤드라인을 그린다. */}
      {!evidenceLayer && (
        <Sequence from={0} durationInFrames={contentEndFrame}>
          <TitleBar
            title={title}
            fontFamily={headlineFont}
            letterSpacing={headlineLetterSpacing}
            primaryColor={headlineColor}
            boxed={overlayBoxes}
            plain={headlinePlain}
          />
        </Sequence>
      )}

      {/* 041 V3.0: 인물 배지 — 엔딩 아웃트로 전까지 유지 */}
      {personBadge && (
        <Sequence from={0} durationInFrames={contentEndFrame}>
          <PersonBadge
            label={personBadge}
            boxed={badgeBoxed ?? overlayBoxes}
            solid={badgeBoxed === true}
            top={newsCard ? NEWS_BOX_TOP + 8 : undefined}
            // 042: 박스를 따로 켜면 검정 박스 위 흰 글자 — 제목의 차콜색을 물려받지 않는다.
            color={badgeBoxed === true ? "" : headlineColor}
          />
        </Sequence>
      )}

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
      {/* BGM 볼륨: celebrity 모드는 내레이션 위주라 BGM 존재감 강화 (0.15 → 0.28).
          다른 모드는 대사·발언이 핵심이라 0.15 유지. */}
      {bgmFile && (
        <Audio
          src={staticFile(bgmFile)}
          volume={isCelebrity ? 0.28 : 0.15}
          loop
        />
      )}

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

      {/* Per-scene sound effects — globally disabled (2026-06-12).
          renderer.py가 모든 씬의 sfx를 빈 튜플로 치환하지만 Remotion 측에도
          이중 안전망으로 재생 블록을 제거. SfxConfig 타입·data/sfx/ 에셋은
          재활성화를 위해 보존됨. */}
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

const TitleBar: React.FC<{
  title: string;
  fontFamily?: string;
  letterSpacing?: number;
  primaryColor?: string;
  boxed?: boolean;
  plain?: boolean;
}> = ({
  title,
  fontFamily = "",
  letterSpacing = 0,
  primaryColor = "",
  boxed = true,
  plain = false,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  // 041: 서체 미지정이면 037 규격(Noto Sans KR 100px, 단색 1덩어리) 그대로.
  // macOS 의 GungSeo 는 Regular 단일 웨이트라 fontWeight 만으로는 굵어지지 않는다
  // — 합성 볼드 대신 검은 외곽선(stroke)으로 피드에서의 가독성을 확보한다.
  const isCustomFont = !!fontFamily;
  const fontStack = isCustomFont
    ? `${fontFamily}, Noto Sans KR, serif`
    : "Noto Sans KR, sans-serif";

  // V3.0 2줄 투톤 헤드라인 — 1열은 지금 화제인 이유(사실), 2열은 이력·배경에
  // 대한 질문형 훅. 지침 원문은 딥 차콜/비비드 레드 투톤이지만 그건 #F5F5F5
  // 캔버스 기준이다. 이 레포는 클립 위 반투명 검정 박스라 차콜이 안 보이므로
  // 1열 흰색 + 2열 비비드 레드로 옮긴다.
  const lines = isCustomFont ? title.split("\n") : [title];
  const accent = "#E50914";
  // 지침 §3-1 의 "125px 초밀착 줄간격"(135pt 기준 0.93) 을 100px 로 환산.
  // 042: plain(도현체)은 글자 키가 커서 0.95 면 1·2열이 맞닿는다 (still 실측).
  const lineHeight = isCustomFont ? (plain ? 1.12 : 0.95) : 1.3;

  // 2줄 규격을 **물리적으로** 보장한다. 궁서는 자폭이 넓어 100px 로는 10자만
  // 넘어도 줄이 접히는데, 3줄이 되면 인물 배지를 덮어버린다(2026-09-14 실측).
  // nowrap 으로 접힘을 막고, 대신 줄 길이에 맞춰 자동 축소한다 — 037 의
  // "제목 100px 고정"은 V2 규격이고 V3.0 은 별도 규격이라 축소해도 무방하다.
  const HEADLINE_BOX_PX = 980;
  const maxLineChars = Math.max(...lines.map((l) => l.length), 1);
  // V2 기본 경로도 2줄을 넘기지 않게 축소한다 (사용자 승인 2026-09-22). 037 의
  // "제목 100px 고정"은 8자 안팎의 짧은 배너를 전제한 값이라, 25자 넘는 제목이
  // 들어오면 3줄로 접혀 클립 인물의 얼굴을 덮었다. 축소는 **넘칠 때만** 걸리고
  // 짧은 제목은 그대로 100px 이라 기존 편의 렌더 결과는 바뀌지 않는다.
  // 여기는 nowrap 이 아니라 자동 줄바꿈이므로 한 줄 글자수가 아니라 `전체
  // 글자수 ÷ 허용 줄수` 로 폭을 잡는다. 0.95 는 줄바꿈 여유분.
  const V2_MAX_LINES = 2;
  const v2Fitted = Math.floor(
    (HEADLINE_BOX_PX * V2_MAX_LINES * 0.95) / Math.max(title.length, 1),
  );
  const headlineSize = isCustomFont
    ? Math.max(72, Math.min(100, Math.floor(HEADLINE_BOX_PX / (maxLineChars * 0.96))))
    : Math.max(64, Math.min(100, v2Fitted));

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
          // 041: 밝은 캔버스에서는 반투명 검정이 회색 박스로 보인다 (사용자 지시
          // 2026-09-14). 박스를 빼고 글자색·외곽선만으로 대비를 만든다.
          background: boxed ? "rgba(0,0,0,0.6)" : "transparent",
          borderRadius: 12,
          maxWidth: "90%",
          textAlign: "center",
        }}
      >
        <div
          style={{
            // 제목 크기 — 사용자 지정 2026-08-25 (75 → 100px). 서체는 기본 유지.
            fontSize: headlineSize,
            fontWeight: 800,
            // 1열 색 — 미지정이면 037 규격(흰색). 밝은 캔버스에서는 딥 차콜.
            color: primaryColor || "#FFFFFF",
            fontFamily: fontStack,
            letterSpacing: letterSpacing ? `${letterSpacing}px` : undefined,
            // 042: plain = 벤치마크처럼 밝은 캔버스 위 순수 글자 (그림자·외곽선 없음).
            textShadow: plain ? "none" : "2px 2px 6px rgba(0,0,0,0.8)",
            ...(isCustomFont && !plain
              ? {
                  WebkitTextStroke: "3px rgba(0,0,0,0.9)",
                  paintOrder: "stroke fill",
                }
              : {}),
            lineHeight,
            wordBreak: "keep-all",
          }}
        >
          {lines.map((line, i) => (
            <div
              key={i}
              style={{
                ...(i > 0 ? { color: accent } : {}),
                ...(isCustomFont ? { whiteSpace: "nowrap" as const } : {}),
              }}
            >
              {line}
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// Top offset: just below the 2-line TitleBar.
// marginTop:180 + paddingTop:16 + 2×(75×1.3) + paddingBottom:16 = 407 → +8px gap = 415.
const CELEBRITY_IMAGE_TOP = 415;
// Bottom offset: symmetric safe zone (matches visual weight of top bar area).
const CELEBRITY_IMAGE_BOTTOM = 330;

const SceneWithImage: React.FC<{
  imageFile: string;
  scene: any;
  emotion: string;
  contained?: boolean;
}> = ({ imageFile, scene, emotion, contained = false }) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Subtle zoom effect on the background image
  const scale = interpolate(frame, [0, 150], [1.0, 1.05], {
    extrapolateRight: "clamp",
  });

  const topInset    = contained ? CELEBRITY_IMAGE_TOP    : 0;
  const bottomInset = contained ? CELEBRITY_IMAGE_BOTTOM : 0;

  return (
    <AbsoluteFill>
      {/* Photo / illustration — celebrity mode insets top & bottom */}
      <div
        style={{
          position: "absolute",
          top: topInset,
          left: 0,
          right: 0,
          bottom: bottomInset,
          opacity,
          overflow: "hidden",
        }}
      >
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
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "linear-gradient(to bottom, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0.1) 40%, rgba(0,0,0,0.6) 100%)",
          }}
        />
      </div>

      {/* Text on top of image */}
      <SceneText scene={scene} emotion={emotion} />
    </AbsoluteFill>
  );
};
