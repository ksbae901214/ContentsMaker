"use client";
import { useMemo } from "react";
import { Player } from "@remotion/player";
import { ShortsComposition } from "../../src/video/remotion/src/ShortsComposition";
import type { ShortsScriptData } from "../../src/video/remotion/src/types";

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
  bgmFile?: string;
}

export function VideoPreview({
  title,
  emotionType,
  scenes,
  sceneImages,
  bgmFile = "",
}: Props) {
  const scriptData: ShortsScriptData = useMemo(() => {
    const lastScene = scenes[scenes.length - 1];
    const duration = lastScene
      ? lastScene.timestamp + lastScene.duration
      : 30;

    return {
      metadata: {
        title,
        emotion_type: emotionType as any,
        duration,
        source_url: "",
      },
      scenes: scenes.map((s) => ({
        id: s.id,
        timestamp: s.timestamp,
        duration: s.duration,
        type: s.type as any,
        text: s.text,
        voice_text: s.voice_text,
        emphasis: s.emphasis as any,
        highlightWords: s.highlight_words,
        subtitle_style: s.subtitle_style as any,
        transition: s.transition as any,
      })),
      audio: {
        tts_script: "",
        voice: "",
        rate: "",
        pitch: "",
      },
      background: {
        type: "gradient",
        colors: [],
      },
    };
  }, [title, emotionType, scenes]);

  const imageProps = useMemo(
    () =>
      sceneImages
        .filter((img) => img.image_path)
        .map((img) => ({
          sceneId: img.scene_id,
          imageFile: img.image_path,
        })),
    [sceneImages]
  );

  const lastScene = scenes[scenes.length - 1];
  const contentDur = lastScene
    ? lastScene.timestamp + lastScene.duration
    : 30;
  const totalDur = contentDur + 4; // + outro
  const durationFrames = Math.round(totalDur * FPS);

  return (
    <div className="bg-gray-900 rounded-lg overflow-hidden">
      <Player
        component={ShortsComposition}
        inputProps={{
          scriptData,
          audioFile: "",
          sceneImages: imageProps,
          bgmFile,
        }}
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
