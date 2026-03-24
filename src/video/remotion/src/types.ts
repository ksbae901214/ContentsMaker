export type EmotionType = "funny" | "touching" | "angry" | "relatable";
export type SceneType = "title" | "body" | "comment";
export type Emphasis = "high" | "medium" | "low";

export interface SceneData {
  id: number;
  timestamp: number;
  duration: number;
  type: SceneType;
  text: string;
  voice_text: string;
  emphasis: Emphasis;
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
