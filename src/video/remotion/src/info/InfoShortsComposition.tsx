import React, { useEffect, useState } from "react";
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  continueRender,
  delayRender,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

/**
 * 045 정보쇼츠 V1.0 — 판화 일러스트 지식 스토리텔링.
 *
 * 벤치마크(인스타 @hamster.743606, 720×1280 실측 ×1.5):
 *   - 크림 단색 캔버스, 상단 Black Han Sans 제목 고정
 *   - 993×930 이미지 박스, 챕터 경계에서 하드컷, 장마다 3.5초 줌 1회 후 정지
 *   - 하단 Pretendard SemiBold 자막(박스·외곽선 없음), 첫 줄 상단 y≈1338 고정
 *   - 우하단 "made by" 워터마크, BGM 없음
 *
 * 시각 계산은 Python(scripts/info_v1_timeline.py)이 끝내 넘긴다.
 * 이 컴포넌트는 받은 ms 구간을 그대로 그린다.
 */

export type InfoImage = {
  file: string;
  startMs: number;
  endMs: number;
  zoomStartMs: number | null;
};

export type InfoCaption = { lines: string[]; startMs: number; endMs: number };

export type InfoShortsProps = {
  titleLines: string[];
  watermark: string;
  canvasColor: string;
  images: InfoImage[];
  captions: InfoCaption[];
  durationMs: number;
  audioFile: string;
};

const INK = "#120E0A";
const TITLE_FONT = "InfoBlackHanSans";
const BODY_FONT = "InfoPretendard";
const FONT_FILES: [string, string][] = [
  [TITLE_FONT, "fonts/BlackHanSans-Regular.ttf"],
  [BODY_FONT, "fonts/Pretendard-SemiBold.otf"],
];

const BOX = { left: 42, top: 366, width: 993, height: 930 };
const ZOOM_MS = 3500;
const ZOOM_SCALE = 1.12;
const CAPTION_TOP = 1338;
const CAPTION_LINE_PX = 68;

const useFonts = () => {
  const [handle] = useState(() => delayRender("InfoShorts fonts"));
  useEffect(() => {
    Promise.all(
      FONT_FILES.map(([family, file]) =>
        new FontFace(family, `url(${staticFile(file)})`).load().then((f) => {
          document.fonts.add(f);
        }),
      ),
    )
      .catch((err) => console.error("InfoShorts 폰트 로드 실패", err))
      .finally(() => continueRender(handle));
  }, [handle]);
};

const Title: React.FC<{ lines: string[] }> = ({ lines }) => (
  <div
    style={{
      position: "absolute",
      top: lines.length > 1 ? 168 : 200,
      left: 90,
      width: 900,
      textAlign: "center",
      fontFamily: `${TITLE_FONT}, sans-serif`,
      fontSize: 84,
      lineHeight: 1.05,
      color: "#111111",
    }}
  >
    {lines.map((l) => (
      <div key={l} style={{ whiteSpace: "nowrap" }}>
        {l}
      </div>
    ))}
  </div>
);

const zoomScale = (nowMs: number, zoomStartMs: number | null): number => {
  if (zoomStartMs === null) return 1;
  return interpolate(nowMs, [zoomStartMs, zoomStartMs + ZOOM_MS], [1, ZOOM_SCALE], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.ease),
  });
};

const ImageBox: React.FC<{ image: InfoImage | undefined; nowMs: number }> = ({
  image,
  nowMs,
}) => (
  <div style={{ position: "absolute", ...BOX, overflow: "hidden" }}>
    {image && (
      <Img
        src={staticFile(image.file)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${zoomScale(nowMs, image.zoomStartMs)})`,
        }}
      />
    )}
  </div>
);

const Caption: React.FC<{ caption: InfoCaption | undefined }> = ({ caption }) =>
  caption ? (
    <div
      style={{
        position: "absolute",
        top: CAPTION_TOP,
        left: 90,
        width: 900,
        textAlign: "center",
        fontFamily: `${BODY_FONT}, sans-serif`,
        fontSize: 57,
        lineHeight: `${CAPTION_LINE_PX}px`,
        color: INK,
      }}
    >
      {caption.lines.map((l, i) => (
        <div key={i} style={{ whiteSpace: "nowrap" }}>
          {l}
        </div>
      ))}
    </div>
  ) : null;

const Watermark: React.FC<{ text: string }> = ({ text }) => (
  <div
    style={{
      position: "absolute",
      right: 39,
      top: 1852,
      fontFamily: `${BODY_FONT}, sans-serif`,
      fontSize: 30,
      color: "#3A2E22",
    }}
  >
    {text}
  </div>
);

const activeAt = <T extends { startMs: number; endMs: number }>(items: T[], ms: number) =>
  items.find((it) => ms >= it.startMs && ms < it.endMs);

export const InfoShortsComposition: React.FC<InfoShortsProps> = ({
  titleLines,
  watermark,
  canvasColor,
  images,
  captions,
  audioFile,
}) => {
  useFonts();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const nowMs = (frame / fps) * 1000;
  // 마지막 여운 구간은 마지막 일러스트를 유지한다 (빈 박스 금지)
  const image = activeAt(images, nowMs) ?? images[images.length - 1];

  return (
    <AbsoluteFill style={{ backgroundColor: canvasColor }}>
      <Title lines={titleLines} />
      <ImageBox image={image} nowMs={nowMs} />
      <Caption caption={activeAt(captions, nowMs)} />
      <Watermark text={watermark} />
      {audioFile ? <Audio src={staticFile(audioFile)} /> : null}
    </AbsoluteFill>
  );
};
