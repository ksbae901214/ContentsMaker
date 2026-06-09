/**
 * V3 ComparisonGridScene — visualLayout = "grid_2x2".
 *
 * 2×2 그리드, 각 셀 540×960px (4셀로 1080×1920 채움).
 * 인물 사진 400×400 둥근, 이름 48px 검정, 데이터 84px Bold dataEmphasisColor.
 * 데이터 페이드 인: frame 15→24 (0.5s 지연, 0.3s fade) — 락인 가드(전환 효과 아님, 내부 데이터 강조 애니메이션만).
 *
 * 사양: contracts/remotion_v3.md "ComparisonGridScene 시각 사양".
 */
import React from "react";
import {
  AbsoluteFill,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { DATA_EMPHASIS_COLOR_MAP, type DataEmphasisColor, type PoliticianCardProps } from "../types";

type ComparisonGridSceneProps = {
  comparisonCards: PoliticianCardProps[]; // 3~4개
  dataEmphasisColor: DataEmphasisColor;
};

type CellProps = {
  card: PoliticianCardProps;
  row: number;
  col: number;
  dataColor: string;
  dataOpacity: number;
};

const Cell: React.FC<CellProps> = ({
  card,
  row,
  col,
  dataColor,
  dataOpacity,
}) => {
  const top = row * 960;
  const left = col * 540;

  return (
    <div
      style={{
        position: "absolute",
        top,
        left,
        width: 540,
        height: 960,
        background: "rgba(255,255,255,0.92)",
        border: "2px solid rgba(0,0,0,0.08)",
        boxSizing: "border-box",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: 20,
      }}
    >
      {card.photoPath ? (
        <Img
          src={staticFile(card.photoPath)}
          style={{
            width: 400,
            height: 400,
            borderRadius: 28,
            objectFit: "cover",
            border: `6px solid ${card.partyColor}`,
          }}
        />
      ) : (
        <div
          style={{
            width: 400,
            height: 400,
            borderRadius: 28,
            background: "#888",
            border: `6px solid ${card.partyColor}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: '"Noto Sans KR", sans-serif',
            color: "#FFF",
            fontSize: 160,
            fontWeight: 900,
          }}
        >
          {card.name.charAt(0)}
        </div>
      )}
      <div
        style={{
          marginTop: 20,
          fontFamily: '"Noto Sans KR", sans-serif',
          fontWeight: 700,
          fontSize: 48,
          color: "#000",
          textAlign: "center",
        }}
      >
        {card.name}
      </div>
      {card.dataLabel && (
        <div
          style={{
            marginTop: 8,
            fontFamily: '"Noto Sans KR", sans-serif',
            fontWeight: 500,
            fontSize: 28,
            color: "#333",
          }}
        >
          {card.dataLabel}
        </div>
      )}
      {card.dataValue && (
        <div
          style={{
            marginTop: 12,
            fontFamily: '"Noto Sans KR", sans-serif',
            fontWeight: 900,
            fontSize: 84,
            color: dataColor,
            opacity: dataOpacity,
            textAlign: "center",
          }}
        >
          {card.dataValue}
        </div>
      )}
    </div>
  );
};

export const ComparisonGridScene: React.FC<ComparisonGridSceneProps> = ({
  comparisonCards,
  dataEmphasisColor,
}) => {
  const frame = useCurrentFrame();
  const dataColor = DATA_EMPHASIS_COLOR_MAP[dataEmphasisColor];

  // 데이터 페이드 인: 0.5s 지연 (15 frames), 0.3s fade (9 frames).
  const dataOpacity = interpolate(frame, [15, 24], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ background: "#1a1a2e" }}>
      {comparisonCards.slice(0, 4).map((card, idx) => {
        const row = Math.floor(idx / 2);
        const col = idx % 2;
        return (
          <Cell
            key={`${card.name}-${idx}`}
            card={card}
            row={row}
            col={col}
            dataColor={dataColor}
            dataOpacity={dataOpacity}
          />
        );
      })}
    </AbsoluteFill>
  );
};
