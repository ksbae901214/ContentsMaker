import React from "react";
import {
  AbsoluteFill,
  Img,
  staticFile,
  useCurrentFrame,
  interpolate,
} from "remotion";

// QW-05: Standardized CTA outro. Lines come from src/video/outro_template.py
// (OUTRO_CTA_LINES) so the spoken voice and visible captions stay in sync.
// Default mirrors the Python constant — kept here as a fallback only.
const DEFAULT_CTA_LINES: readonly string[] = [
  "구독과 좋아요 부탁드립니다",
  "알림 설정도 잊지 마세요",
  "다음 영상에서 만나요!",
];

interface OutroProps {
  ctaLines?: readonly string[];
  showOutroImage?: boolean;
}

export const Outro: React.FC<OutroProps> = ({
  ctaLines = DEFAULT_CTA_LINES,
  showOutroImage = true,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {showOutroImage && (
        <AbsoluteFill style={{ opacity }}>
          <Img
            src={staticFile("outro.png")}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </AbsoluteFill>
      )}

      <AbsoluteFill
        style={{
          justifyContent: "flex-end",
          alignItems: "center",
          opacity,
        }}
      >
        <div
          style={{
            marginBottom: 200,
            padding: "16px 40px",
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontSize: 38,
              fontWeight: 700,
              color: "#FFFFFF",
              fontFamily: "Noto Sans KR, sans-serif",
              textShadow: "2px 2px 8px rgba(0,0,0,0.85)",
              lineHeight: 1.6,
              WebkitTextStroke: "2px rgba(0,0,0,0.7)",
            }}
          >
            {ctaLines.map((line, idx) => (
              <div key={idx}>{line}</div>
            ))}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
