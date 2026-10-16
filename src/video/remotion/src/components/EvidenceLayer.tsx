import React from "react";
import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
  interpolate,
} from "remotion";

/**
 * 043 V5.0 증거 삽입형 TTS 논평 — 화면 레이어.
 *
 * 벤치마크(@lkbhop 폴리버스, 현 포맷기 상위 10편) 레이아웃을 1080×1920 으로 옮긴 것:
 *   - 상단 검정 띠에 **2줄 투톤 헤드라인**(노랑/시안, 두꺼운 고딕 + 검정 외곽선).
 *     2줄은 미디어 상단에 걸쳐 겹친다.
 *   - 미디어 박스 1080×1280 (y 310~1590) — 씬 영상을 얼굴 중심으로 꽉 채우고 천천히 민다.
 *     하단 약 280px 은 회색으로 페이드. 그 아래는 검정 (틱톡 UI 안전영역).
 *   - **주황 중앙 자막**(진갈색 외곽선), **강조어 팝업**(초대형 노랑), **증거 카드**
 *     (캡처 + 빨간 원·밑줄), **반전 플래시**(흰 번쩍임, 효과음 없음).
 *
 * 시각 계산은 Python(scripts/evidence_v5_timeline.py)이 끝내 넘긴다. 이 컴포넌트는
 * 받은 ms 구간을 그대로 그린다 — 042 NewsCardLayer 와 같은 분업.
 */

const FPS = 30;
export const MEDIA_TOP = 310;
const MEDIA_HEIGHT = 1280;
// 하단 블러 띠 — 16:9 소스를 높이 맞춤으로 키우면 방송 번인 자막(16:9 하단 약 25%)이
// 박스 하단 300px 대에 크게 잘려 들어온다. 벤치마크의 하단 회색 블러 띠가 정확히 이걸
// 가린다 (043 파일럿 1호 프레임 실측: KBS 인용 카드·JTBC 자막이 잘린 채 노출).
const FADE_PX = 340;
const MEDIA_ZOOM = 0.06;
// cut_segment 결과물은 1080×1920 안에 16:9 화면(높이 607.5)을 검정 패딩으로 넣은 파일이다.
const CLIP_W = 1080;
const CLIP_H = 1920;
const CLIP_CONTENT_H = (CLIP_W * 9) / 16;
const CAPTION_TOP = 1090;
const POP_TOP = 620;
const CARD_TOP = 470;
const CARD_MAX_W = 960;
const CARD_MAX_H = 600;
const FLASH_FRAMES = 5;
const MARK_RED = "#FF2A2A";
const CAPTION_ORANGE = "#FF8A1F";
const HIGHLIGHT = "#FFE14D";
const POP_YELLOW = "#FFE600";

export interface EvidenceCaption {
  text: string;
  startMs: number;
  endMs: number;
  hl: string[];
}

export interface EvidencePop {
  text: string;
  startMs: number;
  endMs: number;
}

export interface EvidenceMark {
  kind: "circle" | "underline";
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface EvidenceCardData {
  file: string;
  startMs: number;
  endMs: number;
  marks: EvidenceMark[];
}

export interface EvidenceFraming {
  sceneId: number;
  zoom: number;
  focusX: number;
}

export interface EvidenceLayerData {
  headline: string[];
  headlineColors: string[];
  captions: EvidenceCaption[];
  pops: EvidencePop[];
  evidence: EvidenceCardData[];
  flashesMs: number[];
  framing?: EvidenceFraming[];
  channelLabel: string;
  sourceLabel: string;
  fontFamily: string;
}

const toFrame = (ms: number) => Math.round((ms / 1000) * FPS);
const fontStack = (family: string) => `${family || "Noto Sans KR"}, Noto Sans KR, sans-serif`;
const stroke = (px: number, color: string) => ({
  WebkitTextStroke: `${px}px ${color}`,
  paintOrder: "stroke fill" as const,
});
// 한 줄에 넣을 글자 수에 맞춰 축소 — 넘치면 줄이 접혀 미디어를 가린다.
const fitSize = (text: string, maxPx: number, minPx: number, boxPx = 1000) =>
  Math.max(minPx, Math.min(maxPx, Math.floor(boxPx / (Math.max(text.length, 1) * 0.95))));

/**
 * 씬 영상/이미지를 미디어 박스에만 깐다 (SceneText 없음 — 자막은 레이어가 그린다).
 *
 * 영상은 패딩을 걷어 내고 16:9 화면 높이를 박스 높이에 맞춘다(zoom 1.0) — 벤치마크처럼
 * 얼굴로 꽉 찬다. 좌우는 잘리므로 focusX 로 보여 줄 위치를 고른다.
 */
export const EvidenceMedia: React.FC<{
  videoFile?: string;
  imageFile?: string;
  durationFrames: number;
  zoom?: number;
  focusX?: number;
}> = ({ videoFile, imageFile, durationFrames, zoom = 1, focusX = 0.5 }) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, Math.max(durationFrames - 1, 1)], [1, 1 + MEDIA_ZOOM], {
    extrapolateRight: "clamp",
  });
  const mediaStyle: React.CSSProperties = {
    width: "100%",
    height: "100%",
    objectFit: "cover",
    transform: `scale(${scale})`,
  };
  const k = (MEDIA_HEIGHT / CLIP_CONTENT_H) * zoom * scale;
  const videoW = CLIP_W * k;
  const videoH = CLIP_H * k;
  const videoStyle: React.CSSProperties = {
    position: "absolute",
    width: videoW,
    height: videoH,
    left: -(videoW - CLIP_W) * focusX,
    top: MEDIA_HEIGHT / 2 - videoH / 2,
  };
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <div
        style={{
          position: "absolute",
          top: MEDIA_TOP,
          left: 0,
          right: 0,
          height: MEDIA_HEIGHT,
          overflow: "hidden",
          background: "#111",
        }}
      >
        {videoFile ? (
          <OffthreadVideo src={staticFile(videoFile)} style={videoStyle} />
        ) : imageFile ? (
          <Img src={staticFile(imageFile)} style={mediaStyle} />
        ) : null}
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 0,
            height: FADE_PX,
            backdropFilter: "blur(26px)",
            WebkitBackdropFilter: "blur(26px)",
            background: "rgba(80,80,80,0.55)",
            // 위 가장자리를 부드럽게 — 띠가 칼같이 잘려 보이지 않게
            maskImage: "linear-gradient(to bottom, transparent 0%, black 22%)",
            WebkitMaskImage: "linear-gradient(to bottom, transparent 0%, black 22%)",
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

const Headline: React.FC<{ lines: string[]; colors: string[]; family: string }> = ({
  lines,
  colors,
  family,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });
  // 1줄은 검정 띠 안, 2줄은 미디어 상단에 걸친다 (벤치마크 실측 중심 y≈218 / 368).
  const tops = [168, 318];
  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity }}>
      {lines.slice(0, 2).map((line, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            top: tops[i],
            left: 0,
            right: 0,
            textAlign: "center",
            whiteSpace: "nowrap",
            fontFamily: fontStack(family),
            fontSize: fitSize(line, 88, 60),
            lineHeight: 1.1,
            color: colors[i] || colors[0] || "#FFFFFF",
            ...stroke(10, "#000"),
            textShadow: "0 4px 10px rgba(0,0,0,0.6)",
          }}
        >
          {line}
        </div>
      ))}
    </AbsoluteFill>
  );
};

const CornerLabels: React.FC<{ channel: string; source: string; family: string }> = ({
  channel,
  source,
  family,
}) => (
  <AbsoluteFill style={{ pointerEvents: "none" }}>
    {channel && (
      <div
        style={{
          position: "absolute",
          top: MEDIA_TOP + 120,
          left: 36,
          fontFamily: fontStack(family),
          fontSize: 38,
          color: "#FFFFFF",
          ...stroke(6, "#2E7DD7"),
        }}
      >
        {channel}
      </div>
    )}
    {source && (
      <div
        style={{
          position: "absolute",
          top: MEDIA_TOP + 128,
          right: 30,
          maxWidth: 560,
          fontFamily: "Noto Sans KR, sans-serif",
          fontSize: 26,
          fontWeight: 700,
          color: "#FFFFFF",
          textShadow: "1px 1px 3px rgba(0,0,0,0.95)",
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
        }}
      >
        {source}
      </div>
    )}
  </AbsoluteFill>
);

const HighlightedText: React.FC<{ text: string; hl: string[]; base: string }> = ({
  text,
  hl,
  base,
}) => {
  if (!hl.length) return <>{text}</>;
  const escaped = hl.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const parts = text.split(new RegExp(`(${escaped.join("|")})`, "g"));
  return (
    <>
      {parts.map((part, i) => (
        <span key={i} style={{ color: hl.includes(part) ? HIGHLIGHT : base }}>
          {part}
        </span>
      ))}
    </>
  );
};

const Caption: React.FC<{ caption: EvidenceCaption; family: string }> = ({ caption, family }) => {
  const frame = useCurrentFrame();
  const pop = interpolate(frame, [0, 4], [0.92, 1], { extrapolateRight: "clamp" });
  const lines = caption.text.split("\n");
  const longest = lines.reduce((a, b) => (b.length > a.length ? b : a), "");
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          top: CAPTION_TOP,
          left: 0,
          right: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          transform: `scale(${pop})`,
        }}
      >
        {lines.map((line, i) => (
          <div
            key={i}
            style={{
              fontFamily: fontStack(family),
              fontSize: fitSize(longest, 96, 64, 980),
              lineHeight: 1.15,
              color: CAPTION_ORANGE,
              ...stroke(9, "#2B1300"),
              textShadow: "0 3px 8px rgba(0,0,0,0.55)",
              whiteSpace: "nowrap",
            }}
          >
            <HighlightedText text={line} hl={caption.hl} base={CAPTION_ORANGE} />
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

const Pop: React.FC<{ pop: EvidencePop; family: string }> = ({ pop, family }) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, 4, 7], [0.6, 1.08, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          top: POP_TOP,
          left: 0,
          right: 0,
          textAlign: "center",
          whiteSpace: "nowrap",
          fontFamily: fontStack(family),
          fontSize: fitSize(pop.text, 150, 90),
          lineHeight: 1.1,
          color: POP_YELLOW,
          ...stroke(12, "#000"),
          textShadow: "0 6px 14px rgba(0,0,0,0.6)",
          transform: `scale(${scale})`,
        }}
      >
        {pop.text}
      </div>
    </AbsoluteFill>
  );
};

const Mark: React.FC<{ mark: EvidenceMark }> = ({ mark }) => {
  const frame = useCurrentFrame();
  // 마커는 카드가 뜬 뒤 그어진다 — 원/밑줄이 그려지는 동작이 '짚는' 느낌을 준다.
  const draw = interpolate(frame, [6, 16], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const { x, y, w, h } = mark;
  if (mark.kind === "circle") {
    return (
      <ellipse
        cx={x + w / 2}
        cy={y + h / 2}
        rx={w / 2}
        ry={h / 2}
        fill="none"
        stroke={MARK_RED}
        strokeWidth={0.008}
        pathLength={1}
        strokeDasharray={1}
        strokeDashoffset={1 - draw}
      />
    );
  }
  const baseY = y + h;
  const waves = 8;
  const step = w / waves;
  let d = `M ${x} ${baseY}`;
  for (let i = 0; i < waves; i++) {
    const cx = x + step * (i + 0.5);
    const cy = baseY + (i % 2 === 0 ? -h / 2 : h / 2);
    d += ` Q ${cx} ${cy} ${x + step * (i + 1)} ${baseY}`;
  }
  return (
    <path
      d={d}
      fill="none"
      stroke={MARK_RED}
      strokeWidth={0.006}
      pathLength={1}
      strokeDasharray={1}
      strokeDashoffset={1 - draw}
    />
  );
};

const Card: React.FC<{ card: EvidenceCardData }> = ({ card }) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, 8], [0.86, 1], { extrapolateRight: "clamp" });
  const opacity = interpolate(frame, [0, 6], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          top: CARD_TOP,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          opacity,
          transform: `scale(${scale})`,
        }}
      >
        <div
          style={{
            background: "#FFFFFF",
            padding: 12,
            borderRadius: 18,
            boxShadow: "0 12px 36px rgba(0,0,0,0.55)",
          }}
        >
          <div style={{ position: "relative", display: "inline-block", lineHeight: 0 }}>
            <Img
              src={staticFile(card.file)}
              style={{
                display: "block",
                maxWidth: CARD_MAX_W,
                maxHeight: CARD_MAX_H,
                width: "auto",
                height: "auto",
              }}
            />
            {/* 좌표는 이미지 기준 0~1 정규화 — viewBox 를 1×1 로 늘려 그대로 쓴다 */}
            <svg
              viewBox="0 0 1 1"
              preserveAspectRatio="none"
              style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
            >
              {card.marks.map((m, i) => (
                <Mark key={i} mark={m} />
              ))}
            </svg>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Flash: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, FLASH_FRAMES], [0.85, 0], { extrapolateRight: "clamp" });
  return <AbsoluteFill style={{ background: "#FFFFFF", opacity, pointerEvents: "none" }} />;
};

const timed = <T extends { startMs: number; endMs: number }>(
  items: T[],
  key: string,
  render: (item: T) => React.ReactNode,
) =>
  items.map((item, i) => {
    const from = toFrame(item.startMs);
    return (
      <Sequence key={`${key}${i}`} from={from} durationInFrames={Math.max(toFrame(item.endMs) - from, 1)}>
        {render(item)}
      </Sequence>
    );
  });

export const EvidenceLayer: React.FC<{
  layer: EvidenceLayerData;
  contentEndFrame: number;
}> = ({ layer, contentEndFrame }) => (
  <>
    {timed(layer.evidence, "e", (c) => <Card card={c} />)}
    {timed(layer.pops, "p", (p) => <Pop pop={p} family={layer.fontFamily} />)}
    {timed(layer.captions, "c", (c) => <Caption caption={c} family={layer.fontFamily} />)}
    <Sequence from={0} durationInFrames={contentEndFrame}>
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: MEDIA_TOP, background: "#000" }} />
        <div
          style={{
            position: "absolute",
            top: MEDIA_TOP + MEDIA_HEIGHT,
            left: 0,
            right: 0,
            bottom: 0,
            background: "#000",
          }}
        />
      </AbsoluteFill>
      <Headline lines={layer.headline} colors={layer.headlineColors} family={layer.fontFamily} />
      <CornerLabels channel={layer.channelLabel} source={layer.sourceLabel} family={layer.fontFamily} />
    </Sequence>
    {layer.flashesMs.map((ms, i) => (
      <Sequence key={`f${i}`} from={toFrame(ms)} durationInFrames={FLASH_FRAMES + 1}>
        <Flash />
      </Sequence>
    ))}
  </>
);
