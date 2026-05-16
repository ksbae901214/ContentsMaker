// T117: 월간 편향 밸런스 리포트 페이지 (FR-038, SC-011, SC-012)
"use client";

import { useCallback, useEffect, useState } from "react";
import { ElectionBanner } from "../components/ElectionBanner";

type BiasReportData = {
  id?: number;
  month: string;
  total_uploads: number;
  person_shares: Record<string, number>;
  party_shares: Record<string, number>;
  template_usage: Record<string, number>;
  avg_risk_score: number;
  top_n_person_warning: string[];
  recommendations: string[];
  generated_at: string;
  persisted?: boolean;
  error?: string;
};

function defaultMonth(): string {
  const d = new Date();
  d.setDate(1);
  d.setMonth(d.getMonth() - 1);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}

function sharesToBars(shares: Record<string, number>): Array<{ key: string; pct: number }> {
  return Object.entries(shares)
    .map(([key, v]) => ({ key, pct: v * 100 }))
    .sort((a, b) => b.pct - a.pct);
}

function SharesBarList({
  shares,
  highlightAbove = 30,
}: {
  shares: Record<string, number>;
  highlightAbove?: number;
}) {
  const rows = sharesToBars(shares);
  if (rows.length === 0) {
    return <div className="text-gray-500 text-sm">데이터 없음</div>;
  }
  return (
    <div className="space-y-2">
      {rows.map(({ key, pct }) => {
        const warn = pct > highlightAbove;
        return (
          <div key={key} className="flex items-center gap-3">
            <div className="w-32 text-sm text-gray-300 truncate">{key}</div>
            <div className="flex-1 bg-gray-800 rounded h-5 relative overflow-hidden">
              <div
                className="h-full rounded"
                style={{
                  width: `${Math.min(100, pct)}%`,
                  background: warn
                    ? "linear-gradient(90deg, #f87171, #ef4444)"
                    : "linear-gradient(90deg, #60a5fa, #3b82f6)",
                }}
              />
              <span
                className="absolute right-2 top-0 text-xs leading-5"
                style={{ color: warn ? "#fecaca" : "#dbeafe" }}
              >
                {pct.toFixed(1)}%
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function TemplateCounts({ counts }: { counts: Record<string, number> }) {
  const rows = Object.entries(counts)
    .map(([k, v]) => ({ key: k, count: v }))
    .sort((a, b) => b.count - a.count);
  if (rows.length === 0) {
    return <div className="text-gray-500 text-sm">데이터 없음</div>;
  }
  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
      {rows.map(({ key, count }) => (
        <div key={key} className="bg-gray-800 rounded p-3 text-center">
          <div className="text-xs text-gray-400 mb-1">{key}</div>
          <div className="text-xl font-bold">{count}</div>
        </div>
      ))}
    </div>
  );
}

export default function ReportsPage() {
  const [month, setMonth] = useState(defaultMonth());
  const [report, setReport] = useState<BiasReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async (m: string) => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`/api/dem-shorts/reports?month=${encodeURIComponent(m)}`);
      const data = (await res.json()) as BiasReportData;
      if (data.error) {
        setError(data.error);
        setReport(null);
      } else {
        setReport(data);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "리포트 조회 실패");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(month);
  }, [load, month]);

  return (
    <main className="max-w-5xl mx-auto px-4 py-8">
      <ElectionBanner />
      <header className="mb-6 flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-bold mb-1">📊 월간 편향 리포트</h1>
          <p className="text-gray-400 text-sm">
            업로드된 쇼츠의 인물·정당·프리셋 점유율 + 권고 (FR-038)
          </p>
        </div>
        <div className="flex items-end gap-2">
          <div>
            <label className="block text-xs text-gray-400 mb-1">대상 월 (YYYY-MM)</label>
            <input
              type="month"
              value={month}
              onChange={(e) => setMonth(e.target.value)}
              className="px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm"
            />
          </div>
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
          리포트 조회 중...
        </div>
      )}

      {!loading && report && report.total_uploads === 0 && (
        <div className="bg-gray-900 rounded-lg p-12 text-center">
          <div className="text-4xl mb-3">📭</div>
          <p className="text-gray-400 mb-2">
            {report.month} 기준 업로드 이력이 없습니다.
          </p>
        </div>
      )}

      {!loading && report && report.total_uploads > 0 && (
        <div className="space-y-6">
          {/* 요약 카드 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-gray-900 rounded-lg p-4">
              <div className="text-xs text-gray-400 mb-1">대상 월</div>
              <div className="text-2xl font-bold">{report.month}</div>
            </div>
            <div className="bg-gray-900 rounded-lg p-4">
              <div className="text-xs text-gray-400 mb-1">총 업로드</div>
              <div className="text-2xl font-bold">{report.total_uploads}</div>
            </div>
            <div className="bg-gray-900 rounded-lg p-4">
              <div className="text-xs text-gray-400 mb-1">평균 risk_score</div>
              <div className="text-2xl font-bold">
                {report.avg_risk_score.toFixed(1)}
              </div>
            </div>
            <div className="bg-gray-900 rounded-lg p-4">
              <div className="text-xs text-gray-400 mb-1">권고 건수</div>
              <div className="text-2xl font-bold text-amber-400">
                {report.recommendations.length}
              </div>
            </div>
          </div>

          {/* 권고 메시지 */}
          {report.recommendations.length > 0 && (
            <section className="bg-amber-900/20 border border-amber-700 rounded-lg p-4">
              <h2 className="text-base font-semibold text-amber-300 mb-2">
                ⚠ 권고 ({report.recommendations.length})
              </h2>
              <ul className="space-y-1 text-sm text-amber-100">
                {report.recommendations.map((r, idx) => (
                  <li key={idx} className="flex gap-2">
                    <span className="text-amber-400">•</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* 인물 점유율 */}
          <section className="bg-gray-900 rounded-lg p-5">
            <h2 className="text-base font-semibold mb-3">
              인물별 점유율 <span className="text-xs text-gray-500">(30% 초과 시 빨강)</span>
            </h2>
            <SharesBarList shares={report.person_shares} highlightAbove={30} />
          </section>

          {/* 정당 점유율 */}
          <section className="bg-gray-900 rounded-lg p-5">
            <h2 className="text-base font-semibold mb-3">정당별 점유율</h2>
            <SharesBarList shares={report.party_shares} highlightAbove={100} />
          </section>

          {/* 자막 프리셋 분포 */}
          <section className="bg-gray-900 rounded-lg p-5">
            <h2 className="text-base font-semibold mb-3">자막 프리셋 사용 횟수</h2>
            <TemplateCounts counts={report.template_usage} />
          </section>

          <div className="text-xs text-gray-500 pt-2">
            생성 시각: {new Date(report.generated_at).toLocaleString("ko-KR")}
            {report.persisted === false && (
              <span className="ml-2 text-amber-500">
                · 미저장 (실시간 계산 — CLI: <code>bias-report</code>로 저장)
              </span>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
