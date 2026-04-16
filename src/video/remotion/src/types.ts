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
  | "wipe";

export interface SubtitleStyle {
  font_family: string;
  font_size: number;
  font_weight: string;
  color: string;
  shadow: string;
  position_y: number;
  bg_color: string | null;
  bg_opacity: number;
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
}

export const HIGHLIGHT_COLORS: Record<EmotionType, string> = {
  funny: "#FFD700",
  touching: "#FF69B4",
  angry: "#FF4444",
  relatable: "#87CEEB",
};

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
