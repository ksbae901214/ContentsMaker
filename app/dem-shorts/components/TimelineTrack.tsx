// T055: TimelineTrack — 영상 타임라인 + 인물별 발언 구간 색상 하이라이트.
// FR-014, FR-015: confidence < 0.7 → 회색 (미식별)
import type { SpeechSegment } from "./SegmentCard";

interface TimelineTrackProps {
  durationSec: number;
  segments: SpeechSegment[];
  activeId: number | null;
  onSegmentClick?: (seg: SpeechSegment) => void;
  currentTimeSec?: number;
}

// 인물별 색상 — politician_id mod palette 길이.
const PALETTE = [
  { bg: "bg-blue-500", border: "border-blue-400" },
  { bg: "bg-purple-500", border: "border-purple-400" },
  { bg: "bg-pink-500", border: "border-pink-400" },
  { bg: "bg-green-500", border: "border-green-400" },
  { bg: "bg-orange-500", border: "border-orange-400" },
  { bg: "bg-teal-500", border: "border-teal-400" },
];

const UNIDENTIFIED = { bg: "bg-gray-600", border: "border-gray-500" };

function colorFor(politicianId: number | null): { bg: string; border: string } {
  if (politicianId == null) return UNIDENTIFIED;
  return PALETTE[politicianId % PALETTE.length];
}

export function TimelineTrack({
  durationSec,
  segments,
  activeId,
  onSegmentClick,
  currentTimeSec,
}: TimelineTrackProps) {
  if (durationSec <= 0) {
    return <div className="h-8 bg-gray-800 rounded" />;
  }

  const playheadPct = currentTimeSec != null ? (currentTimeSec / durationSec) * 100 : null;

  return (
    <div className="relative h-10 bg-gray-800 rounded overflow-hidden">
      {segments.map((seg) => {
        const leftPct = (seg.start_sec / durationSec) * 100;
        const widthPct = Math.max(
          ((seg.end_sec - seg.start_sec) / durationSec) * 100,
          0.3
        );
        const c = colorFor(seg.politician_id);
        const isActive = seg.id === activeId;
        return (
          <button
            key={seg.id}
            onClick={() => onSegmentClick?.(seg)}
            className={`absolute top-0 h-full ${c.bg} hover:brightness-110 transition ${
              isActive ? `ring-2 ring-white z-10` : ""
            }`}
            style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
            title={
              seg.politician_name
                ? `${seg.politician_name} · conf ${seg.confidence.toFixed(2)}`
                : `(미식별) conf ${seg.confidence.toFixed(2)}`
            }
          />
        );
      })}
      {playheadPct != null && (
        <div
          className="absolute top-0 w-0.5 h-full bg-yellow-400 pointer-events-none z-20"
          style={{ left: `${playheadPct}%` }}
        />
      )}
    </div>
  );
}
