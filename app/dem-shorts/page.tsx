// T038: Dem-Shorts Dashboard — US1 메인 페이지
// NATV 신규 영상 + 민주당 점유도 점수 내림차순 (FR-004)
"use client";

import { useCallback, useEffect, useState } from "react";
import { ElectionBanner } from "./components/ElectionBanner";
import { VideoCard, type SourceVideo } from "./components/VideoCard";

type SessionFilter = "" | "plenary" | "committee" | "audit" | "hearing" | "press";

export default function DemShortsDashboard() {
  const [videos, setVideos] = useState<SourceVideo[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Filters
  const [sinceHours, setSinceHours] = useState(24);
  const [minScore, setMinScore] = useState(0);
  const [sessionType, setSessionType] = useState<SessionFilter>("");
  const [includeExcluded, setIncludeExcluded] = useState(false);

  const fetchVideos = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({
        since_hours: String(sinceHours),
        min_score: String(minScore),
        include_excluded: String(includeExcluded),
        limit: "50",
      });
      if (sessionType) params.set("session_type", sessionType);
      const r = await fetch(`/api/dem-shorts/videos?${params.toString()}`);
      const d = await r.json();
      if (d.error) setError(d.error);
      setVideos(d.videos || []);
      setTotal(d.total || 0);
    } catch (e: any) {
      setError(e.message || "영상 조회 실패");
    } finally {
      setLoading(false);
    }
  }, [sinceHours, minScore, sessionType, includeExcluded]);

  useEffect(() => {
    fetchVideos();
  }, [fetchVideos]);

  return (
    <main className="max-w-6xl mx-auto px-4 py-8">
      <ElectionBanner />
      <header className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-1">🎙️ Dem-Shorts Studio</h1>
          <p className="text-gray-400 text-sm">
            NATV 신규 영상 · 민주당 점유도 기준 우선순위
          </p>
        </div>
        <button
          onClick={fetchVideos}
          className="py-2 px-4 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-medium"
        >
          🔄 새로고침
        </button>
      </header>

      {/* Filter bar */}
      <div className="bg-gray-900 rounded-lg p-4 mb-6 grid grid-cols-1 md:grid-cols-4 gap-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">최근</label>
          <select
            value={sinceHours}
            onChange={(e) => setSinceHours(parseInt(e.target.value, 10))}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm"
          >
            <option value={6}>6시간</option>
            <option value={24}>24시간</option>
            <option value={72}>3일</option>
            <option value={168}>1주</option>
            <option value={720}>30일</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">최소 점유도</label>
          <select
            value={minScore}
            onChange={(e) => setMinScore(parseFloat(e.target.value))}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm"
          >
            <option value={0}>전체</option>
            <option value={50}>중간 이상 (50+)</option>
            <option value={80}>높음 (80+)</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">세션 타입</label>
          <select
            value={sessionType}
            onChange={(e) => setSessionType(e.target.value as SessionFilter)}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm"
          >
            <option value="">전체</option>
            <option value="plenary">본회의</option>
            <option value="committee">상임위</option>
            <option value="audit">국정감사</option>
            <option value="hearing">청문회</option>
            <option value="press">기자회견</option>
          </select>
        </div>
        <div className="flex items-end">
          <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-300">
            <input
              type="checkbox"
              checked={includeExcluded}
              onChange={(e) => setIncludeExcluded(e.target.checked)}
              className="w-4 h-4"
            />
            자동 제외 포함
          </label>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 mb-4 text-sm text-red-300">
          ⚠ {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="text-center py-12 text-gray-500">
          <div className="text-3xl mb-2 animate-pulse">📺</div>
          영상 목록 조회 중...
        </div>
      )}

      {/* Empty */}
      {!loading && !error && videos.length === 0 && (
        <div className="bg-gray-900 rounded-lg p-12 text-center">
          <div className="text-4xl mb-3">📭</div>
          <p className="text-gray-400 mb-2">조건에 맞는 영상이 없습니다</p>
          <p className="text-gray-500 text-xs">
            NATV 폴링 배치(<code>python3 -m src.dem_shorts.cli poll-natv</code>)를 실행하거나
            필터를 조정해보세요.
          </p>
        </div>
      )}

      {/* Stats */}
      {!loading && videos.length > 0 && (
        <div className="flex items-center justify-between mb-4 text-sm text-gray-400">
          <span>
            <span className="text-white font-medium">{videos.length}</span>개 표시
            {total > videos.length && <> · 총 {total}개</>}
          </span>
          <span>점유도 높은 순으로 정렬</span>
        </div>
      )}

      {/* Grid */}
      {!loading && videos.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {videos.map((v) => (
            <VideoCard key={v.video_id} video={v} />
          ))}
        </div>
      )}
    </main>
  );
}
