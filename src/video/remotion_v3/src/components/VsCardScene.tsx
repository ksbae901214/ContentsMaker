/**
 * V3 VsCardScene — visualLayout = "vs_card".
 *
 * 좌(0~540px) / 우(540~1080px) 분할, 정당 컬러 배경.
 * 인물 사진 600×600 중앙 둥근. 없으면 회색 #888 실루엣.
 * 정당명 36px 흰색, 이름 96px 흰색 weight 900.
 *
 * 입장 애니메이션: 0.5s slide (한 번만, fade 아님 — 좌측 -100% → 0, 우측 +100% → 0).
 * 사양: contracts/remotion_v3.md "VsCardScene 시각 사양".
 */
import React from "react";
import {
  AbsoluteFill,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import type { PoliticianCardProps } from "../types";

type VsCardSceneProps = {
  comparisonCards: PoliticianCardProps[]; // 정확히 2개
};

const SLIDE_DURATION_FRAMES = 15; // 0.5초 (30fps)

type SideProps = {
  card: PoliticianCardProps;
  side: "left" | "right";
  slideOffset: number;
};

const Side: React.FC<SideProps> = ({ card, side, slideOffset }) => {
  const left = side === "left" ? 0 : 540;
  const translateX = side === "left" ? -slideOffset : slideOffset;

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        bottom: 0,
        left,
        width: 540,
        background: card.partyColor,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        transform: `translateX(${translateX}px)`,
      }}
    >
      {card.photoPath ? (
        <Img
          src={staticFile(card.photoPath)}
          style={{
            width: 480,
            height: 480,
            borderRadius: 36,
            objectFit: "cover",
            border: "6px solid rgba(255,255,255,0.85)",
            boxShadow: "0 12px 32px rgba(0,0,0,0.45)",
          }}
        />
      ) : (
        <div
          style={{
            width: 480,
            height: 480,
            borderRadius: 36,
            background: "#888",
            border: "6px solid rgba(255,255,255,0.85)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: '"Noto Sans KR", sans-serif',
            color: "#FFF",
            fontSize: 200,
            fontWeight: 900,
          }}
        >
          {card.name.charAt(0)}
        </div>
      )}
      <div
        style={{
          marginTop: 32,
          fontFamily: '"Noto Sans KR", sans-serif',
          fontWeight: 500,
          fontSize: 36,
          color: "#FFF",
          textShadow: "0 2px 6px rgba(0,0,0,0.5)",
        }}
      >
        {card.party}
      </div>
      <div
        style={{
          marginTop: 12,
          fontFamily: '"Noto Sans KR", sans-serif',
          fontWeight: 900,
          fontSize: 96,
          color: "#FFF",
          textShadow: "0 4px 12px rgba(0,0,0,0.55)",
        }}
      >
        {card.name}
      </div>
    </div>
  );
};

export const VsCardScene: React.FC<VsCardSceneProps> = ({
  comparisonCards,
}) => {
  const frame = useCurrentFrame();

  // 좌·우 slide-in: 540 → 0px (한 번만, 0.5s).
  const slideOffset = interpolate(
    frame,
    [0, SLIDE_DURATION_FRAMES],
    [540, 0],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    },
  );

  // 정확히 2개를 기대하지만 방어적으로 처리.
  const left = comparisonCards[0];
  const right = comparisonCards[1];

  return (
    <AbsoluteFill style={{ background: "#000" }}>
      {left && <Side card={left} side="left" slideOffset={slideOffset} />}
      {right && <Side card={right} side="right" slideOffset={slideOffset} />}
    </AbsoluteFill>
  );
};
