"use client";
import { useMemo } from "react";
import { Player } from "@remotion/player";
import { PreviewComposition } from "./PreviewComposition";

const FPS = 30;

interface SceneData {
  id: number;
  timestamp: number;
  duration: number;
  type: string;
  text: string;
  voice_text: string;
  emphasis: string;
  highlight_words?: string[];
  subtitle_style?: Record<string, unknown>;
  transition?: Record<string, unknown>;
}

interface SceneImage {
  scene_id: number;
  image_path: string;
  prompt: string;
}

interface Props {
  title: string;
  emotionType: string;
  scenes: SceneData[];
  sceneImages: SceneImage[];
  audioPath?: string;
  bgmFile?: string;
}

export function VideoPreview({
  title,
  emotionType,
  scenes,
  sceneImages,
  audioPath,
  bgmFile = "",
}: Props) {
  // Build audio URL via /api/download route
  const audioUrl = audioPath
    ? `/api/download?path=${encodeURIComponent(audioPath)}`
    : undefined;

  const scriptData = useMemo(
    () => ({
      metadata: {
        title,
        emotion_type: emotionType,
        duration: scenes.reduce((sum, s) => sum + s.duration, 0),
      },
      scenes: scenes.map((s) => ({
        id: s.id,
        timestamp: s.timestamp,
        duration: s.duration,
        type: s.type,
        text: s.text,
        emphasis: s.emphasis,
        highlightWords: s.highlight_words,
        subtitleStyle: s.subtitle_style as any,
        transition: s.transition as any,
      })),
      background: {
        colors: [] as string[],
      },
    }),
    [title, emotionType, scenes]
  );

  const lastScene = scenes[scenes.length - 1];
  const contentDur = lastScene ? lastScene.timestamp + lastScene.duration : 30;
  const totalDur = contentDur + 4;
  const durationFrames = Math.max(Math.round(totalDur * FPS), 1);

  return (
    <div className="bg-gray-900 rounded-lg overflow-hidden">
      <Player
        component={PreviewComposition}
        inputProps={{ scriptData, audioUrl }}
        durationInFrames={durationFrames}
        fps={FPS}
        compositionWidth={1080}
        compositionHeight={1920}
        style={{
          width: "100%",
          aspectRatio: "9/16",
          maxHeight: 480,
        }}
        controls
        autoPlay={false}
        loop
      />
    </div>
  );
}
