import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";

/**
 * 인물 배지 (041 V3.0 인물 프로필) — 우측 상단 반투명 블랙 박스에 실명+직책.
 *
 * V3.0은 원본을 음소거한 B-roll을 교차 편집하므로 "지금 화면의 이 사람이 누구인가"를
 * 화면이 스스로 말해주지 않는다. 배지가 그 자리를 대신한다.
 *
 * 본문 자막(SceneText)은 037 판단에 따라 박스 배경을 쓰지 않지만, **이 배지는
 * 예외적으로 박스를 유지한다** — 클립마다 배경이 바뀌는 자리라 아웃라인만으로는
 * 대비가 안 잡힌다.
 */
export const PersonBadge: React.FC<{
  label: string;
  // 041: 밝은 캔버스에서는 반투명 검정이 회색 박스로 보여 박스를 끈다
  // (사용자 지시 2026-09-14). 아래 "박스를 유지한다"는 어두운 캔버스 한정이다.
  boxed?: boolean;
  color?: string;
  // 042 V4.0: 불투명 검정 — 흰 캔버스에서 반투명 검정은 회색으로 보인다.
  solid?: boolean;
  // 042 V4.0: 사진 박스 안쪽에 걸리도록 세로 위치를 옮긴다. 미지정이면 412.
  top?: number;
}> = ({ label, boxed = true, color = "", solid = false, top = 412 }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 12], [0, 0.92], {
    extrapolateRight: "clamp",
  });

  if (!label) return null;

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-start",
        alignItems: "flex-end",
        pointerEvents: "none",
        // TitleBar 아래로 내린다 — marginTop 180 + paddingTop 16 + 2줄×(100×0.95=95)
        // + paddingBottom 16 = 402 → +10px 여유.
        // **헤드라인이 3줄로 밀리면 겹친다.** config validate 단계에서 1열/2열
        // 길이를 경고로 잡는다 (render_profile_v3.headline_warnings).
        paddingTop: top,
        paddingRight: 36,
      }}
    >
      <div
        style={{
          opacity,
          padding: "10px 24px",
          background: boxed ? (solid ? "#111111" : "rgba(0,0,0,0.62)") : "transparent",
          borderRadius: 10,
          maxWidth: "72%",
        }}
      >
        <div
          style={{
            fontSize: 40,
            fontWeight: 800,
            color: color || "#FFFFFF",
            fontFamily: "Pretendard, Noto Sans KR, sans-serif",
            // 박스가 없으면 밝은 캔버스 위 어두운 글자라 그림자가 지저분하다.
            textShadow: boxed ? "1px 1px 4px rgba(0,0,0,0.85)" : "none",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {label}
        </div>
      </div>
    </AbsoluteFill>
  );
};
