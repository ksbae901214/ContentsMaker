// T054: 타임라인 편집기 — 비디오 + 발언자 하이라이트 (US2)
"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";

import { ElectionBanner } from "../components/ElectionBanner";
import { SegmentCard, type SpeechSegment } from "../components/SegmentCard";
import { TimelineTrack } from "../components/TimelineTrack";

interface SourceVideo {
  video_id: string;
  title: string;
  duration_sec: number;
  session_type: string;
  dem_score: number;
  status: string;
  stt_status: string;
  diarization_status: string;
  download_path: string | null;
}

export default function VideoTimelinePage() {
  const params = useParams<{ videoId: string }>();
  const router = useRouter();
  const videoId = params.videoId;

  const [video, setVideo] = useState<SourceVideo | null>(null);
  const [segments, setSegments] = useState<SpeechSegment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [sortBy, setSortBy] = useState<"time" | "score">("score");
  const [showUnidentified, setShowUnidentified] = useState(false);
  const [currentTimeSec, setCurrentTimeSec] = useState(0);
  const videoRef = useRef<HTMLVideoElement>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const r = await fetch(`/api/dem-shorts/videos/${videoId}`);
      if (r.status === 404) {
        setError("영상을 찾을 수 없습니다");
        setLoading(false);
        return;
      }
      const d = await r.json();
      if (d.error) setError(d.error);
      else {
        setVideo(d.video);
        setSegments(d.segments || []);
      }
    } catch (e: any) {
      setError(e.message || "조회 실패");
    } finally {
      setLoading(false);
    }
  }, [videoId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const sortedSegments = useMemo(() => {
    let filtered = segments;
    if (!showUnidentified) {
      filtered = filtered.filter((s) => s.politician_id != null && s.confidence >= 0.7);
    }
    if (sortBy === "score") {
      return [...filtered].sort((a, b) => b.recommendation_score - a.recommendation_score);
    }
    return [...filtered].sort((a, b) => a.start_sec - b.start_sec);
  }, [segments, sortBy, showUnidentified]);

  const handleSelect = useCallback((seg: SpeechSegment) => {
    setSelectedId(seg.id);
    if (videoRef.current) {
      videoRef.current.currentTime = seg.start_sec;
      videoRef.current.play().catch(() => {});
    }
  }, []);

  const handleCutShorts = useCallback(
    (seg: SpeechSegment) => {
      // Phase 5 US3 에서 draft 생성 API 연결. 지금은 stub.
      alert(
        `쇼츠 자르기는 Phase 5 구현 예정입니다.\n\n` +
          `선택된 구간: ${seg.stt_text.slice(0, 40)}...\n` +
          `${seg.politician_name} · ${Math.floor(seg.end_sec - seg.start_sec)}초`
      );
    },
    []
  );

  if (loading) {
    return (
      <main className="max-w-6xl mx-auto px-4 py-8 text-center text-gray-400">
        <div className="text-3xl mb-2 animate-pulse">⏳</div>
        영상 + 타임라인 로딩 중...
      </main>
    );
  }

  if (error || !video) {
    return (
      <main className="max-w-6xl mx-auto px-4 py-8">
        <Link
          href="/dem-shorts"
          className="text-sm text-gray-400 hover:text-white mb-4 inline-block"
        >
          ← 대시보드
        </Link>
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 text-red-300">
          {error || "영상 없음"}
        </div>
      </main>
    );
  }

  const identifiedCount = segments.filter(
    (s) => s.politician_id != null && s.confidence >= 0.7
  ).length;

  return (
    <main className="max-w-6xl mx-auto px-4 py-6">
      <ElectionBanner />
      <Link
        href="/dem-shorts"
        className="text-sm text-gray-400 hover:text-white mb-3 inline-block"
      >
        ← 대시보드
      </Link>

      <header className="mb-4">
        <h1 className="text-xl font-bold text-white mb-1">{video.title}</h1>
        <div className="flex items-center gap-3 text-sm text-gray-400">
          <span className="bg-green-600 text-white px-2 py-0.5 rounded text-xs font-bold">
            점유도 {video.dem_score.toFixed(0)}
          </span>
          <span>{video.duration_sec > 0 && `${Math.floor(video.duration_sec / 60)}분`}</span>
          <span className="capitalize">{video.session_type}</span>
          <span>
            {identifiedCount} / {segments.length} 식별됨
          </span>
        </div>
      </header>

      {/* Video player */}
      <div className="bg-black rounded-lg mb-4 overflow-hidden">
        {video.download_path ? (
          <video
            ref={videoRef}
            src={`/api/download?path=${encodeURIComponent(video.download_path)}`}
            controls
            onTimeUpdate={(e) => setCurrentTimeSec(e.currentTarget.currentTime)}
            className="w-full max-h-[480px]"
          />
        ) : (
          <div className="aspect-video flex items-center justify-center text-gray-500">
            영상 다운로드 대기 중 ·
            <code className="ml-2 text-yellow-400">
              python3 -m src.dem_shorts.cli download --video-id {video.video_id}
            </code>
          </div>
        )}
      </div>

      {/* Timeline */}
      <div className="mb-4">
        <div className="text-xs text-gray-400 mb-1">타임라인 (클릭 → 해당 지점 재생)</div>
        <TimelineTrack
          durationSec={video.duration_sec}
          segments={sortedSegments}
          activeId={selectedId}
          onSegmentClick={handleSelect}
          currentTimeSec={currentTimeSec}
        />
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSortBy(sortBy === "score" ? "time" : "score")}
            className="text-xs bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded border border-gray-700"
          >
            {sortBy === "score" ? "🏆 점수순" : "⏱ 시간순"}
          </button>
          <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={showUnidentified}
              onChange={(e) => setShowUnidentified(e.target.checked)}
              className="w-3 h-3"
            />
            (미식별) 포함
          </label>
        </div>
        <div className="text-xs text-gray-500">
          {sortedSegments.length}개 구간
        </div>
      </div>

      {/* Segments */}
      {segments.length === 0 ? (
        <div className="bg-gray-900 rounded-lg p-6 text-center text-gray-500 text-sm">
          <div className="text-3xl mb-2">🎙️</div>
          발언자 식별이 아직 실행되지 않았습니다.
          <div className="mt-2 text-xs">
            터미널에서:
            <code className="block mt-1 text-yellow-400">
              python3 -m src.dem_shorts.cli stt --video-id {video.video_id}
              <br />
              python3 -m src.dem_shorts.cli diarize --video-id {video.video_id}
              <br />
              python3 -m src.dem_shorts.cli identify --video-id {video.video_id}
            </code>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {sortedSegments.map((s) => (
            <SegmentCard
              key={s.id}
              segment={s}
              selected={selectedId === s.id}
              onSelect={handleSelect}
              onCutShorts={handleCutShorts}
            />
          ))}
        </div>
      )}
    </main>
  );
}
