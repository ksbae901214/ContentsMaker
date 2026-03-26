import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
} from "remotion";
import type { TransitionType } from "../types";

interface TransitionProps {
  type: TransitionType;
  durationFrames: number;
  children: React.ReactNode;
}

/**
 * Wraps scene content with an entrance transition effect.
 * The transition plays during the first `durationFrames` frames of the scene.
 */
export const Transition: React.FC<TransitionProps> = ({
  type,
  durationFrames,
  children,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = Math.min(frame / Math.max(durationFrames, 1), 1);

  const springProgress = spring({
    frame,
    fps,
    config: { damping: 20, stiffness: 100 },
    durationInFrames: durationFrames,
  });

  const style = getTransitionStyle(type, progress, springProgress, frame, durationFrames);

  return (
    <AbsoluteFill style={style}>
      {children}
    </AbsoluteFill>
  );
};

function getTransitionStyle(
  type: TransitionType,
  progress: number,
  springProgress: number,
  frame: number,
  durationFrames: number,
): React.CSSProperties {
  switch (type) {
    case "fade":
      return {
        opacity: interpolate(frame, [0, durationFrames], [0, 1], {
          extrapolateRight: "clamp",
        }),
      };

    case "slide-left":
      return {
        transform: `translateX(${interpolate(
          frame,
          [0, durationFrames],
          [100, 0],
          { extrapolateRight: "clamp" }
        )}%)`,
      };

    case "slide-up":
      return {
        transform: `translateY(${interpolate(
          frame,
          [0, durationFrames],
          [100, 0],
          { extrapolateRight: "clamp" }
        )}%)`,
      };

    case "zoom":
      return {
        opacity: interpolate(frame, [0, durationFrames * 0.5], [0, 1], {
          extrapolateRight: "clamp",
        }),
        transform: `scale(${interpolate(
          frame,
          [0, durationFrames],
          [1.5, 1],
          { extrapolateRight: "clamp" }
        )})`,
      };

    case "dissolve":
      return {
        opacity: interpolate(frame, [0, durationFrames], [0, 1], {
          extrapolateRight: "clamp",
        }),
        filter: `blur(${interpolate(
          frame,
          [0, durationFrames],
          [8, 0],
          { extrapolateRight: "clamp" }
        )}px)`,
      };

    case "wipe":
      return {
        clipPath: `inset(0 ${interpolate(
          frame,
          [0, durationFrames],
          [100, 0],
          { extrapolateRight: "clamp" }
        )}% 0 0)`,
      };

    default:
      return {
        opacity: interpolate(frame, [0, durationFrames], [0, 1], {
          extrapolateRight: "clamp",
        }),
      };
  }
}
