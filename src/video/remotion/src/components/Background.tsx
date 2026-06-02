import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
} from "remotion";

interface BackgroundProps {
  colors: string[];
}

export const Background: React.FC<BackgroundProps> = ({ colors }) => {
  const frame = useCurrentFrame();

  const gradientAngle = interpolate(frame, [0, 300], [135, 225], {
    extrapolateRight: "wrap",
  });

  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(${gradientAngle}deg, ${colors.join(", ")})`,
        opacity,
      }}
    />
  );
};
