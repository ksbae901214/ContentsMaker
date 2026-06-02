// T039: VideoCard — 단일 NATV 영상 카드 (썸네일·제목·점수 뱃지)
import Link from "next/link";

export interface SourceVideo {
  video_id: string;
  title: string;
  description?: string;
  published_at: string;
  duration_sec: number;
  thumbnail_url?: string;
  session_type: string;
  dem_score: number;
  stt_status: string;
  status: string;
  excluded_reason?: string | null;
}

const SESSION_LABELS: Record<string, string> = {
  plenary: "본회의",
  committee: "상임위",
  audit: "국정감사",
  hearing: "청문회",
  press: "기자회견",
  other: "기타",
};

function formatDuration(sec: number): string {
  if (sec <= 0) return "--:--";
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("ko-KR", { month: "short", day: "numeric" });
  } catch {
    return iso.slice(0, 10);
  }
}

function scoreColor(score: number): string {
  if (score >= 80) return "bg-green-600 text-white";
  if (score >= 50) return "bg-yellow-600 text-white";
  return "bg-gray-700 text-gray-300";
}

export function VideoCard({ video }: { video: SourceVideo }) {
  const isExcluded = video.status === "excluded";

  return (
    <Link
      href={`/dem-shorts/${video.video_id}`}
      className={`block bg-gray-800 hover:bg-gray-750 rounded-lg overflow-hidden border border-gray-700 hover:border-blue-500 transition ${
        isExcluded ? "opacity-50" : ""
      }`}
    >
      <div className="relative aspect-video bg-gray-900">
        {video.thumbnail_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={video.thumbnail_url}
            alt={video.title}
            className="w-full h-full object-cover"
          />
        )}
        <div className={`absolute top-2 right-2 px-2 py-0.5 rounded text-xs font-bold ${scoreColor(video.dem_score)}`}>
          {video.dem_score.toFixed(0)}점
        </div>
        <div className="absolute bottom-2 right-2 bg-black/70 px-1.5 py-0.5 rounded text-xs text-white">
          {formatDuration(video.duration_sec)}
        </div>
      </div>
      <div className="p-3">
        <div className="text-sm font-medium text-white line-clamp-2 leading-tight mb-2">
          {video.title}
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <span className="bg-gray-700 px-1.5 py-0.5 rounded">
            {SESSION_LABELS[video.session_type] || video.session_type}
          </span>
          <span>{formatDate(video.published_at)}</span>
          {video.stt_status === "done" && (
            <span className="text-green-400" title="STT 완료">✓</span>
          )}
        </div>
        {isExcluded && video.excluded_reason && (
          <div className="mt-1 text-xs text-red-400">
            ⚠ {video.excluded_reason === "length_over_6h"
              ? "6시간 초과"
              : video.excluded_reason === "no_dem_politician"
              ? "민주당 인물 미감지"
              : video.excluded_reason}
          </div>
        )}
      </div>
    </Link>
  );
}
