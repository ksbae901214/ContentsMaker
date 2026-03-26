"use client";
import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
} from "remotion";

const FPS = 30;

type EmotionType = "funny" | "touching" | "angry" | "relatable";

const GRADIENT_THEMES: Record<EmotionType, string[]> = {
  funny: ["#FF6B6B", "#FFA500", "#FFD93D"],
  touching: ["#6A5ACD", "#9370DB", "#DDA0DD"],
  angry: ["#DC143C", "#8B0000", "#B22222"],
  relatable: ["#4169E1", "#1E90FF", "#87CEEB"],
};

const HIGHLIGHT_COLORS: Record<EmotionType, string> = {
  funny: "#FFD700",
  touching: "#FF69B4",
  angry: "#FF4444",
  relatable: "#87CEEB",
};

interface SceneData {
  id: number;
  timestamp: number;
  duration: number;
  type: string;
  text: string;
  emphasis: string;
  highlightWords?: string[];
  subtitleStyle?: {
    font_size?: number;
    font_weight?: string;
    color?: string;
    shadow?: string;
    position_y?: number;
    bg_color?: string | null;
    bg_opacity?: number;
  };
  transition?: {
    type?: string;
    duration?: number;
  };
}

interface ScriptData {
  metadata: {
    title: string;
    emotion_type: string;
    duration: number;
  };
  scenes: SceneData[];
  background: {
    colors: string[];
  };
}

interface PreviewProps {
  scriptData: ScriptData;
  audioUrl?: string;
}

/** Lightweight composition for @remotion/player — uses URL-based audio. */
export const PreviewComposition: React.FC<PreviewProps> = ({ scriptData, audioUrl }) => {
  const emotion = (scriptData.metadata.emotion_type || "relatable") as EmotionType;
  const colors =
    scriptData.background.colors.length > 0
      ? scriptData.background.colors
      : GRADIENT_THEMES[emotion] || GRADIENT_THEMES.relatable;

  const title = scriptData.metadata.title;
  const lastScene = scriptData.scenes[scriptData.scenes.length - 1];
  const contentEndFrame = lastScene
    ? Math.round((lastScene.timestamp + lastScene.duration) * FPS)
    : 0;

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {/* Gradient background */}
      <GradientBg colors={colors} />

      {/* Scene sequences */}
      {scriptData.scenes.map((scene) => {
        const startFrame = Math.round(scene.timestamp * FPS);
        const durationFrames = Math.round(scene.duration * FPS);
        const transition = scene.transition;
        const transitionDur = Math.round((transition?.duration ?? 0.5) * FPS);

        return (
          <Sequence key={scene.id} from={startFrame} durationInFrames={durationFrames}>
            <TransitionWrap type={transition?.type} durationFrames={transitionDur}>
              <PreviewSceneText scene={scene} emotion={emotion} />
            </TransitionWrap>
          </Sequence>
        );
      })}

      {/* Title bar */}
      <Sequence from={0} durationInFrames={contentEndFrame}>
        <PreviewTitleBar title={title} />
      </Sequence>

      {/* Outro */}
      <Sequence from={contentEndFrame} durationInFrames={FPS * 4}>
        <AbsoluteFill
          style={{
            backgroundColor: "#000",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <div
            style={{
              fontSize: 38,
              fontWeight: 700,
              color: "#FFF",
              fontFamily: "Noto Sans KR, sans-serif",
              textAlign: "center",
              lineHeight: 1.6,
            }}
          >
            {"구독과 좋아요를 눌러주시면\n더 많은 영상을 볼 수 있습니다"}
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* TTS voice audio */}
      {audioUrl && <Audio src={audioUrl} />}
    </AbsoluteFill>
  );
};

const GradientBg: React.FC<{ colors: string[] }> = ({ colors }) => {
  const frame = useCurrentFrame();
  const angle = interpolate(frame, [0, 300], [135, 225], {
    extrapolateRight: "clamp",
  });
  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(${angle}deg, ${colors.join(", ")})`,
        opacity,
      }}
    />
  );
};

const PreviewTitleBar: React.FC<{ title: string }> = ({ title }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "center", pointerEvents: "none" }}>
      <div
        style={{
          opacity,
          marginTop: 80,
          padding: "16px 40px",
          background: "rgba(0,0,0,0.6)",
          borderRadius: 12,
          maxWidth: "90%",
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: 75,
            fontWeight: 800,
            color: "#FFF",
            fontFamily: "Noto Sans KR, sans-serif",
            textShadow: "2px 2px 6px rgba(0,0,0,0.8)",
            lineHeight: 1.3,
          }}
        >
          {title}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const PreviewSceneText: React.FC<{ scene: SceneData; emotion: EmotionType }> = ({
  scene,
  emotion,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const animateY = interpolate(frame, [0, 15], [40, 0], { extrapolateRight: "clamp" });

  const style = scene.subtitleStyle;
  const fontSize = style?.font_size ?? 80;
  const fontWeight = style?.font_weight ?? "700";
  const textColor = style?.color ?? "#FFFFFF";
  const textShadow = style?.shadow ?? "3px 3px 8px rgba(0,0,0,0.7)";
  const positionY = style?.position_y ?? 0.6;
  const bgColor = style?.bg_color ?? null;
  const bgOpacity = style?.bg_opacity ?? 0;
  const verticalOffset = (positionY - 0.5) * 1920;

  const highlightWords = scene.highlightWords || [];
  const highlightColor = HIGHLIGHT_COLORS[emotion] || HIGHLIGHT_COLORS.relatable;
  const isComment = scene.type === "comment";

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: "0 60px" }}>
      <div
        style={{
          opacity,
          transform: `translateY(${animateY + verticalOffset}px)`,
          textAlign: "center",
          maxWidth: "90%",
          position: "relative",
        }}
      >
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
            fontFamily: "Noto Sans KR, sans-serif",
            lineHeight: 1.5,
            textShadow,
            whiteSpace: "pre-wrap",
            wordBreak: "keep-all",
          }}
        >
          <HighlightedText text={scene.text} highlights={highlightWords} color={highlightColor} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

const HighlightedText: React.FC<{
  text: string;
  highlights: string[];
  color: string;
}> = ({ text, highlights, color }) => {
  if (!highlights.length) return <>{text}</>;
  const escaped = highlights.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const regex = new RegExp(`(${escaped.join("|")})`, "g");
  const parts = text.split(regex);
  return (
    <>
      {parts.map((part, i) => {
        const isHL = highlights.some((h) => h.toLowerCase() === part.toLowerCase());
        return isHL ? (
          <span key={i} style={{ color }}>{part}</span>
        ) : (
          <React.Fragment key={i}>{part}</React.Fragment>
        );
      })}
    </>
  );
};

const TransitionWrap: React.FC<{
  type?: string;
  durationFrames: number;
  children: React.ReactNode;
}> = ({ type, durationFrames, children }) => {
  const frame = useCurrentFrame();

  if (!type || type === "fade") {
    const opacity = interpolate(frame, [0, durationFrames], [0, 1], {
      extrapolateRight: "clamp",
    });
    return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>;
  }

  if (type === "slide-left") {
    const x = interpolate(frame, [0, durationFrames], [100, 0], { extrapolateRight: "clamp" });
    return <AbsoluteFill style={{ transform: `translateX(${x}%)` }}>{children}</AbsoluteFill>;
  }

  if (type === "slide-up") {
    const y = interpolate(frame, [0, durationFrames], [100, 0], { extrapolateRight: "clamp" });
    return <AbsoluteFill style={{ transform: `translateY(${y}%)` }}>{children}</AbsoluteFill>;
  }

  if (type === "zoom") {
    const opacity = interpolate(frame, [0, durationFrames * 0.5], [0, 1], { extrapolateRight: "clamp" });
    const scale = interpolate(frame, [0, durationFrames], [1.5, 1], { extrapolateRight: "clamp" });
    return <AbsoluteFill style={{ opacity, transform: `scale(${scale})` }}>{children}</AbsoluteFill>;
  }

  if (type === "dissolve") {
    const opacity = interpolate(frame, [0, durationFrames], [0, 1], { extrapolateRight: "clamp" });
    const blur = interpolate(frame, [0, durationFrames], [8, 0], { extrapolateRight: "clamp" });
    return <AbsoluteFill style={{ opacity, filter: `blur(${blur}px)` }}>{children}</AbsoluteFill>;
  }

  if (type === "wipe") {
    const clip = interpolate(frame, [0, durationFrames], [100, 0], { extrapolateRight: "clamp" });
    return <AbsoluteFill style={{ clipPath: `inset(0 ${clip}% 0 0)` }}>{children}</AbsoluteFill>;
  }

  // Default fade
  const opacity = interpolate(frame, [0, durationFrames], [0, 1], { extrapolateRight: "clamp" });
  return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>;
};
