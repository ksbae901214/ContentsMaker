export type EmotionType = "funny" | "touching" | "angry" | "relatable";
export type SceneType = "title" | "body" | "comment" | "clip" | "commentary";
export type Emphasis = "high" | "medium" | "low";
export type VisualType = "image" | "video" | "none";
export type TransitionType =
  | "fade"
  | "slide-left"
  | "slide-up"
  | "zoom"
  | "dissolve"
  | "wipe"
  | "punch-zoom";

export interface SubtitleStyle {
  font_family: string;
  font_size: number;
  font_weight: string;
  color: string;
  shadow: string;
  position_y: number;
  bg_color: string | null;
  bg_opacity: number;
  // QW-03: 외곽선 색/두께. 누락 시 검정 6px 기본값.
  stroke_color?: string;
  stroke_width?: number;
}

export interface TransitionConfig {
  type: TransitionType;
  duration: number;
}

export interface SfxConfig {
  name: string;
  category: string;
  offset_ms: number;
  volume: number;
}

export interface SceneData {
  id: number;
  timestamp: number;
  duration: number;
  type: SceneType;
  text: string;
  voice_text: string;
  emphasis: Emphasis;
  highlightWords?: string[];
  visual_type?: VisualType;
  motion_prompt?: string;
  subtitle_style?: SubtitleStyle;
  transition?: TransitionConfig;
  sfx?: SfxConfig[];
  // QW-01: 첫 1.5~2.5초 후킹 씬. true 시 1.4x 폰트 + 중앙 + 펀치 줌.
  hook?: boolean;
  // QW-02: 강조 키워드 색 카테고리 — fact(노랑)/criticism(빨강)/neutral(emotion 색).
  highlight_category?: string;
  highlightCategory?: string;
}

export const HIGHLIGHT_COLORS: Record<EmotionType, string> = {
  funny: "#FFD700",
  touching: "#FF69B4",
  angry: "#FF4444",
  relatable: "#87CEEB",
};

// QW-02: 카테고리별 강조 색 — emotion 색보다 우선. 정치 유튜브 §2.3 패턴.
export const CATEGORY_HIGHLIGHT_COLORS: Record<string, string> = {
  fact: "#FFD54F",
  criticism: "#F44336",
};

/** QW-02: 카테고리가 있으면 그 색, 아니면 emotion 색으로 폴백. */
export function resolveHighlightColor(
  category: string | undefined,
  emotion: EmotionType,
): string {
  if (category && CATEGORY_HIGHLIGHT_COLORS[category]) {
    return CATEGORY_HIGHLIGHT_COLORS[category];
  }
  return HIGHLIGHT_COLORS[emotion] ?? HIGHLIGHT_COLORS.relatable;
}

export interface ShortsScriptData {
  metadata: {
    title: string;
    emotion_type: EmotionType;
    duration: number;
    source_url: string;
  };
  scenes: SceneData[];
  audio: {
    tts_script: string;
    voice: string;
    rate: string;
    pitch: string;
  };
  background: {
    type: string;
    colors: string[];
  };
}

export const GRADIENT_THEMES: Record<EmotionType, string[]> = {
  funny: ["#FF6B6B", "#FFA500", "#FFD93D"],
  touching: ["#6A5ACD", "#9370DB", "#DDA0DD"],
  angry: ["#DC143C", "#8B0000", "#B22222"],
  relatable: ["#4169E1", "#1E90FF", "#87CEEB"],
};
