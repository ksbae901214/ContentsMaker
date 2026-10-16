import React from "react";
import {
  AbsoluteFill,
  Img,
  Sequence,
  staticFile,
  useCurrentFrame,
  interpolate,
} from "remotion";

/**
 * 042 V4.0 사진 슬라이드 뉴스 카드 — 사진 트랙 + 호흡 단위 자막 + 출처 줄.
 *
 * 벤치마크(@gokorea012, 29.3초) 레이아웃을 1080×1920 으로 옮긴 것:
 *   - 제목(TitleBar) 아래 **정사각 1080 박스**에 사진. 컷마다 느린 줌인(켄 번즈)
 *   - 박스 하단에 겹친 **검정 박스 흰 자막**, 강조어만 노랑
 *   - 하단 회색 **출처 한 줄** (박스 없음)
 *
 * **사진과 자막은 서로 다른 시계로 돈다** — 사진은 3.4초 고정 타이머, 자막은
 * 나레이션 호흡. 시각 계산은 Python(scripts/news_v4_timeline.py)이 끝내 넘긴다.
 * 이 컴포넌트는 받은 ms 구간을 그대로 그린다.
 */

const FPS = 30;
// 제목(도현체 1.12 × 2줄 + 여백)이 y≈436 까지 내려온다 — 그 아래에서 시작한다
// (still 실측). 배지는 ShortsComposition 이 이 값 + 8px 에 띄워 벤치마크처럼
// 사진 박스 안쪽 우상단에 걸리게 한다.
export const NEWS_BOX_TOP = 440;
const BOX_SIZE = 1080;
// 벤치마크: 자막 박스 중심이 사진 박스 하단에서 약 9% 위.
const CAPTION_BOTTOM_GAP = 60;
// 벤치마크: 출처 줄 y≈1715/1920.
const CREDIT_BOTTOM = 190;
const ZOOM_COVER = 0.12;
// 캡처는 글자가 가장자리까지 차 있어 조금만 민다 — 잘리면 원문이 안 읽힌다.
const ZOOM_CONTAIN = 0.04;

const CAPTION_COLORS: Record<string, string> = {
  white: "#FFFFFF",
  yellow: "#FFE14D",
  red: "#FF3B3B",
  blue: "#5DADE2",
};
const HIGHLIGHT = "#FFE14D";

export interface NewsPhoto {
  file: string;
  fit: "cover" | "contain";
  startMs: number;
  endMs: number;
}

export interface NewsCaption {
  text: string;
  startMs: number;
  endMs: number;
  hl: string[];
  color: string;
}

export interface NewsCardData {
  photos: NewsPhoto[];
  captions: NewsCaption[];
  creditLine: string;
  fontFamily: string;
}

const toFrame = (ms: number) => Math.round((ms / 1000) * FPS);

const PhotoCut: React.FC<{ photo: NewsPhoto; frames: number; canvas: string }> = ({
  photo,
  frames,
  canvas,
}) => {
  const frame = useCurrentFrame();
  const amount = photo.fit === "contain" ? ZOOM_CONTAIN : ZOOM_COVER;
  const scale = interpolate(frame, [0, Math.max(frames - 1, 1)], [1, 1 + amount], {
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        position: "absolute",
        top: NEWS_BOX_TOP,
        left: 0,
        width: BOX_SIZE,
        height: BOX_SIZE,
        overflow: "hidden",
        background: canvas,
      }}
    >
      <Img
        src={staticFile(photo.file)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: photo.fit,
          transform: `scale(${scale})`,
        }}
      />
    </div>
  );
};

const CaptionText: React.FC<{ caption: NewsCaption }> = ({ caption }) => {
  const base = CAPTION_COLORS[caption.color] || CAPTION_COLORS.white;
  if (!caption.hl.length) return <>{caption.text}</>;
  const escaped = caption.hl.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const parts = caption.text.split(new RegExp(`(${escaped.join("|")})`, "g"));
  return (
    <>
      {parts.map((part, i) => (
        <span key={i} style={caption.hl.includes(part) ? { color: HIGHLIGHT } : { color: base }}>
          {part}
        </span>
      ))}
    </>
  );
};

const Caption: React.FC<{ caption: NewsCaption; fontFamily: string }> = ({
  caption,
  fontFamily,
}) => {
  const lines = caption.text.split("\n");
  // CTA(2줄 'A / VS B')는 벤치마크에서 본문 자막보다 크다.
  const fontSize = lines.length > 1 ? 72 : 60;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 1920 - (NEWS_BOX_TOP + BOX_SIZE) + CAPTION_BOTTOM_GAP,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 4,
        }}
      >
        {lines.map((line, i) => (
          <div
            key={i}
            style={{
              background: "rgba(0,0,0,0.88)",
              padding: "6px 22px",
              fontSize,
              fontFamily: `${fontFamily || "Noto Sans KR"}, Noto Sans KR, sans-serif`,
              fontWeight: 800,
              lineHeight: 1.25,
              color: CAPTION_COLORS[caption.color] || CAPTION_COLORS.white,
              whiteSpace: "nowrap",
              maxWidth: "94%",
            }}
          >
            <CaptionText caption={{ ...caption, text: line }} />
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

const CreditLine: React.FC<{ label: string }> = ({ label }) => (
  <AbsoluteFill
    style={{
      justifyContent: "flex-end",
      alignItems: "center",
      paddingBottom: CREDIT_BOTTOM,
      pointerEvents: "none",
    }}
  >
    <div
      style={{
        fontSize: 30,
        color: "#555555",
        fontFamily: "Noto Sans KR, sans-serif",
        fontWeight: 700,
        whiteSpace: "nowrap",
        maxWidth: "94%",
        overflow: "hidden",
        textOverflow: "ellipsis",
      }}
    >
      {label}
    </div>
  </AbsoluteFill>
);

export const NewsCardLayer: React.FC<{
  card: NewsCardData;
  canvasColor: string;
  contentEndFrame: number;
}> = ({ card, canvasColor, contentEndFrame }) => (
  <>
    {card.photos.map((p, i) => {
      const from = toFrame(p.startMs);
      const frames = Math.max(toFrame(p.endMs) - from, 1);
      return (
        <Sequence key={`p${i}`} from={from} durationInFrames={frames}>
          <PhotoCut photo={p} frames={frames} canvas={canvasColor} />
        </Sequence>
      );
    })}
    {card.captions.map((c, i) => {
      const from = toFrame(c.startMs);
      const frames = Math.max(toFrame(c.endMs) - from, 1);
      return (
        <Sequence key={`c${i}`} from={from} durationInFrames={frames}>
          <Caption caption={c} fontFamily={card.fontFamily} />
        </Sequence>
      );
    })}
    {card.creditLine && (
      <Sequence from={0} durationInFrames={contentEndFrame}>
        <CreditLine label={card.creditLine} />
      </Sequence>
    )}
  </>
);
