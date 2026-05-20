import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  Easing,
} from "remotion";
import { resolveHighlightColor } from "../types";
import type { EmotionType, SubtitleStyle } from "../types";
import { buildSubtitleTextShadow } from "./SubtitleBlock";

/** Default values when no SubtitleStyle is provided. */
// 2026-05-18 사용자 피드백: 폰트가 너무 커서 30자 자막도 2줄 초과해
// CSS WebkitLineClamp:2가 "…"를 부착. 80→56으로 줄여 2줄에 더 넉넉히.
const DEFAULT_FONT_SIZE = 56;
const DEFAULT_POSITION_Y = 192; // 10% below center of 1920px
// QW-03 (B안): 시그니처 색 정보가 없는 SceneText는 검정 6px 기본 외곽선.
const DEFAULT_STROKE_COLOR = "#000000";
const DEFAULT_STROKE_WIDTH = 6;
const DEFAULT_DROP_SHADOW = "3px 3px 8px rgba(0,0,0,0.7)";

interface SceneData {
  id: number;
  timestamp: number;
  duration: number;
  type: string;
  text: string;
  voice_text?: string;
  voiceText?: string;
  emphasis: string;
  highlightWords?: string[];
  subtitleStyle?: SubtitleStyle;
  subtitle_style?: SubtitleStyle;
  translatedText?: string;
  translated_text?: string;
  // QW-01: 첫 1.5~2.5초 후킹 씬. true 시 1.4x 폰트 + 중앙 + 펀치 줌.
  hook?: boolean;
  // QW-02: 강조 키워드 색 카테고리.
  highlight_category?: string;
  highlightCategory?: string;
  // Feature 011 V2 Phase B: 정치 모드 자막 색·강조
  subtitle_color?: string;
  subtitleColor?: string;
  subtitle_emphasis?: boolean;
  subtitleEmphasis?: boolean;
  // Phase 3 (2026-05-20): 자막 그룹 — 같은 원본 문장의 분할 자식 씬 식별.
  // group_first=false면 fade-in 생략 → 텍스트만 즉시 교체(끊김 제거).
  subtitle_group_id?: number | null;
  subtitleGroupId?: number | null;
  subtitle_group_first?: boolean;
  subtitleGroupFirst?: boolean;
}

// V2 Phase B: 자막 색 keyword → hex (subtitle_color_map.py와 동일 매핑)
const V2_SUBTITLE_COLOR_HEX: Record<string, string> = {
  white: "#FFFFFF",
  red: "#FF4444",
  yellow: "#FFD93D",
  blue: "#5DADE2",
};

interface SceneTextProps {
  scene: SceneData;
  emotion?: string;
}

/**
 * Render text with highlighted keywords in emotion color.
 * Splits text by highlight words and wraps matches in colored spans.
 */
const HighlightedText: React.FC<{
  text: string;
  highlights: string[];
  color: string;
}> = ({ text, highlights, color }) => {
  if (!highlights.length) {
    return <>{text}</>;
  }

  const escaped = highlights.map((w) =>
    w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  );
  const regex = new RegExp(`(${escaped.join("|")})`, "g");
  const parts = text.split(regex);

  return (
    <>
      {parts.map((part, i) => {
        const isHighlight = highlights.some(
          (h) => h.toLowerCase() === part.toLowerCase()
        );
        return isHighlight ? (
          <span key={i} style={{ color }}>{part}</span>
        ) : (
          <React.Fragment key={i}>{part}</React.Fragment>
        );
      })}
    </>
  );
};

export const SceneText: React.FC<SceneTextProps> = ({ scene, emotion }) => {
  const frame = useCurrentFrame();
  const isHook = scene.hook === true;
  // Phase 3 (2026-05-20): 분할 자식 씬(같은 그룹의 2번째 이후) 식별.
  // groupId가 set이고 group_first=false면 fade-in 생략(텍스트만 교체).
  const groupId = scene.subtitleGroupId ?? scene.subtitle_group_id ?? null;
  const groupFirstRaw = scene.subtitleGroupFirst ?? scene.subtitle_group_first;
  const isGroupContinuation = groupId !== null && groupFirstRaw === false;

  // Phase 4 (2026-05-20): 애니메이션 톤다운.
  // - hook 줌: 0.88→1.08→1.0 (overshoot 20%) → 0.96→1.02→1.0 (overshoot 2%) 정치 톤에 신뢰감
  // - 일반 fade: 15프레임 linear → 9프레임 easeOutQuad (300ms, 부드럽고 빠르게)
  // - slide-up: 40px → 16px (작은 움직임이 안정감)
  // - emphasis는 폰트 1.25x + 색으로 충분 → 펀치줌 제거 (isHook에만)
  const punchScale = interpolate(
    frame,
    [0, 3, 9],
    [0.96, 1.02, 1.0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const opacity = isGroupContinuation
    ? 1
    : interpolate(
        frame,
        isHook ? [0, 3] : [0, 9],
        [0, 1],
        {
          easing: isHook ? Easing.linear : Easing.out(Easing.quad),
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        },
      );
  const animateY = (isHook || isGroupContinuation)
    ? 0
    : interpolate(
        frame,
        [0, 9],
        [16, 0],
        {
          easing: Easing.out(Easing.quad),
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        },
      );

  // Support both camelCase and snake_case from props
  const style: SubtitleStyle | undefined =
    scene.subtitleStyle || scene.subtitle_style;

  // Feature 011 V2 Phase B: scene.subtitle_color/emphasis 우선 적용
  const v2Color = (scene.subtitleColor || scene.subtitle_color || "").toLowerCase().trim();
  const v2Emphasis = scene.subtitleEmphasis || scene.subtitle_emphasis || false;

  const baseFontSize = style?.font_size ?? DEFAULT_FONT_SIZE;
  // QW-01: hook 씬은 1.25x 폰트 (이전 1.4x → 너무 커서 2줄 넘김 → 1.25x).
  // V2: subtitle_emphasis도 동일.
  const fontSize = (isHook || v2Emphasis) ? Math.round(baseFontSize * 1.25) : baseFontSize;
  const fontWeight = (isHook || v2Emphasis) ? "900" : (style?.font_weight ?? "700");
  const fontFamily = style?.font_family ?? "Noto Sans KR, sans-serif";
  // V2 색이 white가 아닌 경우 우선 적용. white이거나 비어있으면 기존 textColor.
  const v2HexColor = v2Color && v2Color !== "white" ? V2_SUBTITLE_COLOR_HEX[v2Color] : undefined;
  const textColor = v2HexColor || style?.color || "#FFFFFF";
  // QW-03: 기존 `style.shadow`는 drop shadow로 흡수. 외곽선은 별도 합성.
  const dropShadow = style?.shadow ?? DEFAULT_DROP_SHADOW;
  const strokeColor = style?.stroke_color ?? DEFAULT_STROKE_COLOR;
  const strokeWidth = style?.stroke_width ?? DEFAULT_STROKE_WIDTH;
  const textShadow = buildSubtitleTextShadow(
    strokeWidth,
    strokeColor,
    dropShadow,
  );
  // QW-01: hook 씬은 화면 중앙 강제 (positionY 0.5)
  const positionY = isHook ? 0.5 : (style?.position_y ?? 0.652);
  const bgColor = style?.bg_color ?? null;
  const bgOpacity = style?.bg_opacity ?? 0;

  // Convert position_y (0-1) to pixel offset from center
  // 0.5 = center, 0 = top, 1 = bottom
  const verticalOffset = (positionY - 0.5) * 1920;

  const isComment = scene.type === "comment";
  const highlightWords = scene.highlightWords || [];
  // QW-02: highlight_category가 있으면 카테고리 색, 없으면 emotion 색.
  const highlightCategory = scene.highlightCategory || scene.highlight_category;
  const highlightColor = resolveHighlightColor(
    highlightCategory,
    (emotion || "relatable") as EmotionType,
  );

  const translatedText = scene.translatedText || scene.translated_text;

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        padding: "0 60px",
      }}
    >
      <div
        style={{
          opacity,
          // Phase 4: 펀치줌은 isHook 전용 (emphasis는 펀치줌 없이 폰트만 키움).
          // 연속 자막(group_first=false)은 animateY도 0 → 즉시 교체.
          transform: isHook
            ? `translateY(${verticalOffset}px) scale(${punchScale})`
            : `translateY(${animateY + verticalOffset}px)`,
          textAlign: "center",
          maxWidth: "90%",
          position: "relative",
        }}
      >
        {/* Background overlay for subtitle */}
        {bgColor && bgOpacity > 0 && (
          <div
            style={{
              position: "absolute",
              inset: -16,
              backgroundColor: bgColor,
              opacity: bgOpacity,
              borderRadius: 12,
            }}
          />
        )}

        {isComment && (
          <div
            style={{
              position: "relative",
              fontSize: 28,
              color: "rgba(255,255,255,0.7)",
              marginBottom: 16,
              fontFamily: "Noto Sans KR, sans-serif",
            }}
          >
            Best Comment
          </div>
        )}
        <div
          style={{
            position: "relative",
            fontSize,
            fontWeight: fontWeight as any,
            color: textColor,
            fontFamily,
            lineHeight: 1.4,
            textShadow,
            whiteSpace: "pre-wrap",
            wordBreak: "keep-all",
            // 2026-05-16 사용자 피드백: 자막 최대 2줄. 3줄 이상 노출 금지.
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
            maxHeight: `${Math.round(fontSize * 1.4 * 2)}px`,
          }}
        >
          <HighlightedText
            text={scene.text}
            highlights={highlightWords}
            color={highlightColor}
          />
        </div>

        {/* Dual subtitle (translated text) */}
        {translatedText && (
          <div
            style={{
              position: "relative",
              fontSize: Math.round(fontSize * 0.55),
              fontWeight: "400",
              color: "rgba(255,255,255,0.8)",
              fontFamily,
              lineHeight: 1.4,
              textShadow: "2px 2px 6px rgba(0,0,0,0.7)",
              whiteSpace: "pre-wrap",
              marginTop: 12,
            }}
          >
            {translatedText}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
