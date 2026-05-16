// T116: 주간 여성·청년 정치인 랭킹 페이지 (FR-008)
"use client";

import { useCallback, useEffect, useState } from "react";
import { ElectionBanner } from "../components/ElectionBanner";

type RankingRow = {
  rank: number;
  score: number;
  delta: number;
  tag: "new" | "rising" | "pending" | null;
  data_sources: Record<string, number>;
  politician: {
    id: number;
    name: string;
    party: string;
    category: string;
    tier: string;
    photo_url: string | null;
  };
};

type RankingResponse = {
  week_start: string;
  rankings: RankingRow[];
  error?: string;
};

function tagBadge(tag: RankingRow["tag"]) {
  if (!tag) return null;
  const labels: Record<NonNullable<RankingRow["tag"]>, { text: string; bg: string; fg: string }> = {
    new: { text: "신규", bg: "#dbeafe", fg: "#1e3a8a" },
    rising: { text: "급상승", bg: "#fef3c7", fg: "#78350f" },
    pending: { text: "대기", bg: "#e5e7eb", fg: "#4b5563" },
  };
  const { text, bg, fg } = labels[tag];
  return (
    <span
      style={{
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: 11,
        background: bg,
        color: fg,
        fontWeight: 600,
      }}
    >
      {text}
    </span>
  );
}

function categoryLabel(category: string): string {
  const m: Record<string, string> = {
    female: "여성",
    youth: "청년",
    alliance: "연대",
    fixed: "고정",
  };
  return m[category] ?? category;
}

function formatDelta(delta: number): string {
  if (delta === 0) return "—";
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta.toFixed(1)}`;
}

export default function RankingPage() {
  const [weekStart, setWeekStart] = useState("");
  const [rankings, setRankings] = useState<RankingRow[]>([]);
  const [currentWeek, setCurrentWeek] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async (week?: string) => {
    setLoading(true);
    setError("");
    try {
      const qs = week ? `?week_start=${encodeURIComponent(week)}` : "";
      const res = await fetch(`/api/dem-shorts/rankings${qs}`);
      const data = (await res.json()) as RankingResponse;
      if (data.error) setError(data.error);
      setRankings(data.rankings || []);
      setCurrentWeek(data.week_start || "");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "랭킹 조회 실패");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <main className="max-w-5xl mx-auto px-4 py-8">
      <ElectionBanner />
      <header className="mb-6 flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-bold mb-1">📈 주간 랭킹</h1>
          <p className="text-gray-400 text-sm">
            여성·청년 정치인 주간 인기 랭킹 · 5개 공공 데이터 가중합 (FR-008)
          </p>
        </div>
        <div className="flex items-end gap-2">
          <div>
            <label className="block text-xs text-gray-400 mb-1">주 시작 (월요일)</label>
            <input
              type="date"
              value={weekStart}
              onChange={(e) => setWeekStart(e.target.value)}
              className="px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm"
            />
          </div>
          <button
            onClick={() => load(weekStart || undefined)}
            className="py-2 px-4 bg-blue-600 hover:bg-blue-500 rounded text-sm font-medium"
          >
            조회
          </button>
        </div>
      </header>

      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 mb-4 text-sm text-red-300">
          ⚠ {error}
        </div>
      )}

      {loading && (
        <div className="text-center py-12 text-gray-500">
          <div className="text-3xl mb-2 animate-pulse">⏳</div>
          랭킹 조회 중...
        </div>
      )}

      {!loading && rankings.length === 0 && !error && (
        <div className="bg-gray-900 rounded-lg p-12 text-center">
          <div className="text-4xl mb-3">🗂️</div>
          <p className="text-gray-400 mb-2">해당 주간 랭킹 데이터가 없습니다</p>
          <p className="text-gray-500 text-xs">
            CLI로 배치 실행: <code>python3 -m src.dem_shorts.cli ranking-batch</code>
          </p>
        </div>
      )}

      {!loading && rankings.length > 0 && (
        <>
          <div className="mb-3 text-sm text-gray-400">
            주 시작: <span className="text-white font-medium">{currentWeek}</span> ·{" "}
            {rankings.length}명
          </div>
          <div className="bg-gray-900 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-800 text-gray-400">
                  <th className="text-left px-4 py-3 w-12">#</th>
                  <th className="text-left px-4 py-3">정치인</th>
                  <th className="text-left px-4 py-3 w-24">카테고리</th>
                  <th className="text-left px-4 py-3 w-20">등급</th>
                  <th className="text-right px-4 py-3 w-24">점수</th>
                  <th className="text-right px-4 py-3 w-24">전주 대비</th>
                  <th className="text-center px-4 py-3 w-20">태그</th>
                </tr>
              </thead>
              <tbody>
                {rankings.map((row) => (
                  <tr key={row.politician.id} className="border-t border-gray-800">
                    <td className="px-4 py-3 font-bold">{row.rank}</td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-white">{row.politician.name}</div>
                      <div className="text-xs text-gray-500">{row.politician.party}</div>
                    </td>
                    <td className="px-4 py-3 text-gray-300">
                      {categoryLabel(row.politician.category)}
                    </td>
                    <td className="px-4 py-3 text-gray-300">{row.politician.tier}</td>
                    <td className="px-4 py-3 text-right font-mono">{row.score.toFixed(1)}</td>
                    <td
                      className="px-4 py-3 text-right font-mono"
                      style={{
                        color: row.delta > 0 ? "#86efac" : row.delta < 0 ? "#fca5a5" : "#9ca3af",
                      }}
                    >
                      {formatDelta(row.delta)}
                    </td>
                    <td className="px-4 py-3 text-center">{tagBadge(row.tag)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </main>
  );
}
