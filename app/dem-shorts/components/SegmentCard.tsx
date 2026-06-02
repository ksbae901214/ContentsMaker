// T056: SegmentCard — 발언 구간 카드 (추천점수 + 인물 정보 + 자르기 버튼)
export interface SpeechSegment {
  id: number;
  start_sec: number;
  end_sec: number;
  confidence: number;
  stt_text: string;
  recommendation_score: number;
  emotion_strength: number;
  issue_keywords: string | null; // JSON string in SQLite
  is_solo: number;
  has_profanity: number;
  politician_id: number | null;
  politician_name: string | null;
  politician_photo?: string | null;
}

function formatTime(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function scoreColor(score: number): string {
  if (score >= 80) return "text-green-400";
  if (score >= 50) return "text-yellow-400";
  return "text-gray-400";
}

function parseKeywords(raw: string | null): string[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

interface Props {
  segment: SpeechSegment;
  onSelect?: (seg: SpeechSegment) => void;
  onCutShorts?: (seg: SpeechSegment) => void;
  selected?: boolean;
}

export function SegmentCard({ segment, onSelect, onCutShorts, selected }: Props) {
  const keywords = parseKeywords(segment.issue_keywords);
  const unidentified = segment.politician_id == null || segment.confidence < 0.7;

  return (
    <div
      className={`bg-gray-800 rounded-lg border ${
        selected ? "border-blue-500 ring-1 ring-blue-500" : "border-gray-700"
      } p-3 cursor-pointer hover:border-gray-600 transition`}
      onClick={() => onSelect?.(segment)}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          {segment.politician_photo && !unidentified && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={segment.politician_photo}
              alt=""
              className="w-8 h-8 rounded-full object-cover"
            />
          )}
          <div className="min-w-0">
            <div className="text-sm font-medium text-white truncate">
              {unidentified ? (
                <span className="text-gray-400">(미식별 · conf {segment.confidence.toFixed(2)})</span>
              ) : (
                segment.politician_name
              )}
            </div>
            <div className="text-xs text-gray-500">
              {formatTime(segment.start_sec)}–{formatTime(segment.end_sec)} ·{" "}
              {Math.floor(segment.end_sec - segment.start_sec)}초
            </div>
          </div>
        </div>
        <div className="text-right flex-shrink-0">
          <div className={`text-lg font-bold ${scoreColor(segment.recommendation_score)}`}>
            {segment.recommendation_score.toFixed(0)}
          </div>
          <div className="text-xs text-gray-500">점수</div>
        </div>
      </div>

      <p className="text-xs text-gray-300 line-clamp-2 mb-2">
        {segment.stt_text || <span className="text-gray-500">(전사 없음)</span>}
      </p>

      <div className="flex flex-wrap gap-1 mb-2">
        {segment.is_solo === 1 && (
          <span className="text-xs bg-purple-900/50 text-purple-300 px-1.5 py-0.5 rounded">
            단독
          </span>
        )}
        {keywords.slice(0, 3).map((kw) => (
          <span
            key={kw}
            className="text-xs bg-blue-900/50 text-blue-300 px-1.5 py-0.5 rounded"
          >
            #{kw}
          </span>
        ))}
        {segment.has_profanity === 1 && (
          <span className="text-xs bg-red-900/50 text-red-300 px-1.5 py-0.5 rounded">
            ⚠ 부적절 표현
          </span>
        )}
      </div>

      {onCutShorts && !unidentified && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onCutShorts(segment);
          }}
          className="w-full py-1.5 bg-blue-600 hover:bg-blue-500 rounded text-xs font-medium"
        >
          ✂️ 쇼츠 만들기
        </button>
      )}
    </div>
  );
}
