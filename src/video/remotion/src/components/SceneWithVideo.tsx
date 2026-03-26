import React from "react";
import {
  AbsoluteFill,
  OffthreadVideo,
  staticFile,
  useCurrentFrame,
  interpolate,
} from "remotion";
import { SceneText } from "./SceneText";

interface SceneWithVideoProps {
  videoFile: string;
  scene: any;
  emotion: string;
}

export const SceneWithVideo: React.FC<SceneWithVideoProps> = ({
  videoFile,
  scene,
  emotion,
}) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill>
      {/* AI video clip background */}
      <AbsoluteFill style={{ opacity }}>
        <OffthreadVideo
          src={staticFile(videoFile)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
        {/* Dark overlay for text readability */}
        <AbsoluteFill
          style={{
            background:
              "linear-gradient(to bottom, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.1) 40%, rgba(0,0,0,0.5) 100%)",
          }}
        />
      </AbsoluteFill>

      {/* Text overlay */}
      <SceneText scene={scene} emotion={emotion} />
    </AbsoluteFill>
  );
};
