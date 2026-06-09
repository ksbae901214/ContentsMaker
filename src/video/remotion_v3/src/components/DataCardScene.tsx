/**
 * V3 DataCardScene — visualLayout = "data_card".
 *
 * 단일 인물 + 큰 데이터 강조.
 * 인물 사진 720×720 상단 둥근, 이름 64px 검정, 데이터 레이블 40px 검정,
 * 데이터 값 144px weight 900 dataEmphasisColor.
 *
 * 데이터 값에 spring 애니메이션 (0.8s scale 0.7 → 1.0) — 내부 마이크로 애니메이션.
 * 사양: contracts/remotion_v3.md "DataCardScene 시각 사양".
 */
import React from "react";
import {
  AbsoluteFill,
  Img,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {
  DATA_EMPHASIS_COLOR_MAP,
  type DataEmphasisColor,
  type PoliticianCardProps,
} from "../types";

type DataCardSceneProps = {
  comparisonCards: PoliticianCardProps[]; // 정확히 1개, dataValue 필수
  dataEmphasisColor: DataEmphasisColor;
};

export const DataCardScene: React.FC<DataCardSceneProps> = ({
  comparisonCards,
  dataEmphasisColor,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const card = comparisonCards[0];
  const dataColor = DATA_EMPHASIS_COLOR_MAP[dataEmphasisColor];

  // Spring 애니메이션: 0.8s scale 0.7 → 1.0.
  const dataScale = spring({
    frame,
    fps,
    from: 0.7,
    to: 1.0,
    durationInFrames: Math.round(0.8 * fps),
    config: {
      damping: 12,
      stiffness: 120,
      mass: 0.6,
    },
  });

  if (!card) {
    return <AbsoluteFill style={{ background: "#1a1a2e" }} />;
  }

  return (
    <AbsoluteFill
      style={{
        background: "#FFFFFF",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "flex-start",
        paddingTop: 380, // PinnedHeadline(80 + 240 + 여백) 아래
        paddingBottom: 380, // SubtitleBlock(320) + 여백 위
      }}
    >
      {card.photoPath ? (
        <Img
          src={staticFile(card.photoPath)}
          style={{
            width: 720,
            height: 720,
            borderRadius: 48,
            objectFit: "cover",
            border: `8px solid ${card.partyColor}`,
            boxShadow: "0 12px 32px rgba(0,0,0,0.25)",
          }}
        />
      ) : (
        <div
          style={{
            width: 720,
            height: 720,
            borderRadius: 48,
            background: "#888",
            border: `8px solid ${card.partyColor}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: '"Noto Sans KR", sans-serif',
            color: "#FFF",
            fontSize: 280,
            fontWeight: 900,
          }}
        >
          {card.name.charAt(0)}
        </div>
      )}
      <div
        style={{
          marginTop: 28,
          fontFamily: '"Noto Sans KR", sans-serif',
          fontWeight: 700,
          fontSize: 64,
          color: "#000",
        }}
      >
        {card.name}
      </div>
      {card.dataLabel && (
        <div
          style={{
            marginTop: 16,
            fontFamily: '"Noto Sans KR", sans-serif',
            fontWeight: 500,
            fontSize: 40,
            color: "#000",
          }}
        >
          {card.dataLabel}
        </div>
      )}
      {card.dataValue && (
        <div
          style={{
            marginTop: 20,
            fontFamily: '"Noto Sans KR", sans-serif',
            fontWeight: 900,
            fontSize: 144,
            color: dataColor,
            transform: `scale(${dataScale})`,
            textShadow: "0 4px 12px rgba(0,0,0,0.2)",
          }}
        >
          {card.dataValue}
        </div>
      )}
    </AbsoluteFill>
  );
};
