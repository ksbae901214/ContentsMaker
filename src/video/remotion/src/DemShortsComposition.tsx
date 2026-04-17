// T067: Dem-Shorts 전용 Remotion composition (R-14)
// 기존 BlindShorts composition은 미변경. 신규 composition으로 격리.
//
// Props:
// - videoFile: 자른 NATV 영상 (9:16 변환된)
// - commentaryBlocks: [{start, end, text, style}]
// - subtitlePreset: 5종 프리셋 중 1
// - ttsFile: 선택적 TTS 오디오
// - bgmFile: 선택적 BGM (bgm_manifest 등록된 것만)
import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  Video,
  staticFile,
} from "remotion";
import { SubtitleBlock, type SubtitlePresetData } from "./components/SubtitleBlock";

const FPS = 30;

export interface CommentaryBlock {
  start: number; // seconds
  end: number; // seconds
  text: string;
  style?: "high" | "medium" | "low"; // 강조 레벨
  highlightWords?: string[]; // 강조할 단어들
}

export interface DemShortsCompositionProps {
  videoFile: string; // public/ 경로 파일명 (예: "seg_42.mp4")
  commentaryBlocks: CommentaryBlock[];
  subtitlePreset: SubtitlePresetData;
  ttsFile?: string; // public/ 경로 파일명
  bgmFile?: string; // public/ 경로 파일명
  sourceLabelText?: string; // "NATV 국회방송" 표시 (FR-029)
}

export const DemShortsComposition: React.FC<DemShortsCompositionProps> = ({
  videoFile,
  commentaryBlocks = [],
  subtitlePreset,
  ttsFile,
  bgmFile,
  sourceLabelText = "NATV 국회방송",
}) => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {/* 원본 NATV 구간 영상 — objectFit:contain 으로 letterbox (16:9 클립 → 9:16 프레임) */}
      {videoFile && (
        <Video
          src={staticFile(videoFile)}
          style={{ width: "100%", height: "100%", objectFit: "contain" }}
        />
      )}

      {/* 해설 자막 블록 */}
      {commentaryBlocks.map((block, idx) => {
        const startFrame = Math.max(0, Math.round(block.start * FPS));
        const durFrames = Math.max(1, Math.round((block.end - block.start) * FPS));
        return (
          <Sequence
            key={idx}
            from={startFrame}
            durationInFrames={durFrames}
            name={`commentary-${idx}`}
          >
            <SubtitleBlock
              text={block.text}
              preset={subtitlePreset}
              style={block.style || "medium"}
              highlightWords={block.highlightWords || []}
            />
          </Sequence>
        );
      })}

      {/* NATV 출처 라벨 (FR-029) — 네비게이션 바 아래 (20% = ~160px) 고정 */}
      <div
        style={{
          position: "absolute",
          top: "20%",
          right: 40,
          padding: "8px 16px",
          background: "rgba(0,0,0,0.7)",
          color: "#fff",
          fontSize: 28,
          fontWeight: 600,
          borderRadius: 6,
          fontFamily: "Pretendard, -apple-system, sans-serif",
        }}
      >
        📺 {sourceLabelText}
      </div>

      {/* TTS 음성 오버레이 */}
      {ttsFile && <Audio src={staticFile(ttsFile)} volume={1.0} />}

      {/* BGM (낮은 볼륨 배경음악) */}
      {bgmFile && (
        <Audio src={staticFile(bgmFile)} volume={0.12} />
      )}
    </AbsoluteFill>
  );
};
