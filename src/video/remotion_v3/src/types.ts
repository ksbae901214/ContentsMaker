/**
 * V3 공용 타입 정의.
 *
 * Python → TypeScript 경계에서 snake_case → camelCase 자동 변환 후 사용
 * (renderer.py의 _convert_to_camel_case()).
 *
 * 사양: specs/010-jpolitics-v3-isolated/contracts/remotion_v3.md
 */

export type SubtitleColor = "white" | "yellow" | "red" | "blue";
export type DataEmphasisColor = "red" | "yellow" | "blue";
export type VisualLayout = "normal" | "vs_card" | "grid_2x2" | "data_card";
export type SceneType = "title" | "body" | "comment";
export type SourceType = "jpolitics_youtube" | "jpolitics_topic";

export type PoliticianCardProps = {
  name: string;
  party: string;
  partyColor: string;
  photoPath?: string;
  dataLabel?: string;
  dataValue?: string;
};

export type SceneTiming = {
  sceneId: number;
  startMs: number;
  endMs: number;
};

export type JpoliticsSceneProps = {
  id: number;
  timestamp: number;
  duration: number;
  type: SceneType;
  text: string;
  voiceText: string;
  visualLayout: VisualLayout;
  subtitleColor: SubtitleColor;
  subtitleEmphasis: boolean;
  comparisonCards?: PoliticianCardProps[];
  dataEmphasisColor: DataEmphasisColor;
  clipPath?: string;
};

export type JpoliticsMetadata = {
  title: string;
  sourceType: SourceType;
  sourceUrl?: string;
  sourceLabel?: string;
  durationSec: number;
  createdAt: string;
  topic?: string;
};

export type JpoliticsAudio = {
  ttsVoice: "ko-KR-InJoonNeural";
  ttsRate: "+22%";
  ttsScript: string;
  audioPath: string;
  sceneTimings: SceneTiming[];
};

export type JpoliticsBackground = {
  type: "gradient";
  colors: [string, string];
};

export type JpoliticsCompositionProps = {
  metadata: JpoliticsMetadata;
  scenes: JpoliticsSceneProps[];
  audio: JpoliticsAudio;
  background: JpoliticsBackground;
  headlinePin: string;
};

/**
 * SubtitleBlock 색상 매핑.
 * FR-018: 자막 4색 시스템 (V2 패턴 복제).
 */
export const SUBTITLE_COLOR_MAP: Record<SubtitleColor, string> = {
  white: "#000000", // 흰 라이트박스 위 검정 글자 (기본)
  yellow: "#B8860B", // 다크 골든로드 (가독성 위해)
  red: "#E61E2B",
  blue: "#0066CC",
};

/**
 * 강조 시 강제 빨강.
 * FR-018: subtitleEmphasis = true → 폰트 1.4x + 빨강 #E61E2B.
 */
export const EMPHASIS_COLOR = "#E61E2B";

/**
 * 데이터 강조색 매핑 (grid_2x2, data_card).
 * FR-023.
 */
export const DATA_EMPHASIS_COLOR_MAP: Record<DataEmphasisColor, string> = {
  red: "#E61E2B",
  yellow: "#FFD700",
  blue: "#0066CC",
};
