"use client";

import { useEffect, useState } from "react";

type VideoMeta = {
  video_id: string;
  title: string;
  channel_title: string;
  view_count: number;
  comment_count: number;
  thumbnail_url: string;
  url: string;
};

type NewsItem = {
  title: string;
  link: string;
  pub_date: string;
};

type IssueCluster = {
  topic: string;
  videos: VideoMeta[];
  news: NewsItem[];
  total_views: number;
  total_comments: number;
  news_count: number;
};

type RankedIssue = {
  rank: number;
  score: number;
  cluster: IssueCluster;
};

type BriefingData = {
  briefing: {
    date: string;
    generated_at: string;
    ranked_issues: RankedIssue[];
    channel_count: number;
    raw_video_count: number;
    raw_news_count: number;
  };
  plans_by_rank: Record<string, unknown>;
};

const INITIAL_VISIBLE = 10;  // 상위 10개만 표시. 더 보기 버튼으로 10씩 추가 가능.
const LOAD_MORE_STEP = 10;

export default function DailyBriefingPage() {
  const [data, setData] = useState<BriefingData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runLog, setRunLog] = useState<string>("");
  const [visibleCount, setVisibleCount] = useState(INITIAL_VISIBLE);

  async function loadLatest() {
    setLoading(true);
    setError(null);
    setVisibleCount(INITIAL_VISIBLE);  // 새로 로드 시 보이는 개수 초기화
    try {
      const r = await fetch("/api/daily-briefing");
      if (r.status === 404) {
        setData(null);
        setError("저장된 브리핑이 없습니다. 아래 버튼으로 새로 실행하세요.");
        return;
      }
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const j = await r.json();
      setData(j);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function runNew() {
    setLoading(true);
    setError(null);
    setRunLog("브리핑 실행 중... (수집 + 클러스터링 + Claude 3-plan 5건, 최대 10분)");
    try {
      const r = await fetch("/api/daily-briefing", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ top: 5 }),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        throw new Error(j.error || `HTTP ${r.status}`);
      }
      const j = await r.json();
      setRunLog(j.log || "완료");
      await loadLatest();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadLatest(); }, []);

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: 24, fontFamily: "system-ui, -apple-system, sans-serif" }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>오늘의 정치 브리핑</h1>
      <p style={{ color: "#666", marginBottom: 24 }}>
        어제(KST) YouTube 정치 채널 + 네이버 뉴스를 수집해 핫한 이슈 순으로 기획안을 자동 생성합니다.
      </p>

      <div style={{ display: "flex", gap: 12, marginBottom: 24 }}>
        <button
          onClick={runNew}
          disabled={loading}
          style={{
            padding: "10px 20px", background: loading ? "#999" : "#0066cc",
            color: "white", border: "none", borderRadius: 6, cursor: loading ? "not-allowed" : "pointer",
            fontSize: 15, fontWeight: 600,
          }}
        >
          {loading ? "실행 중..." : "새 브리핑 실행"}
        </button>
        <button
          onClick={loadLatest}
          disabled={loading}
          style={{
            padding: "10px 20px", background: "#f0f0f0", color: "#333",
            border: "1px solid #ccc", borderRadius: 6, cursor: loading ? "not-allowed" : "pointer",
            fontSize: 15,
          }}
        >
          최신 결과 다시 로드
        </button>
      </div>

      {runLog && (
        <pre style={{
          background: "#f7f7f7", padding: 12, borderRadius: 6, fontSize: 12,
          color: "#444", maxHeight: 200, overflow: "auto", marginBottom: 16,
        }}>{runLog}</pre>
      )}

      {error && (
        <div style={{ padding: 12, background: "#fee", color: "#900", borderRadius: 6, marginBottom: 16 }}>
          {error}
        </div>
      )}

      {data && (
        <>
          <div style={{ background: "#f9f9f9", padding: 12, borderRadius: 6, marginBottom: 16, fontSize: 14 }}>
            <strong>날짜:</strong> {data.briefing.date} | <strong>채널:</strong> {data.briefing.channel_count}개
            | <strong>영상:</strong> {data.briefing.raw_video_count}개 | <strong>기사:</strong> {data.briefing.raw_news_count}개
            | <strong>생성:</strong> {new Date(data.briefing.generated_at).toLocaleString("ko-KR")}
          </div>

          {data.briefing.ranked_issues.length === 0 && (
            <p style={{ color: "#666" }}>이슈가 수집되지 않았습니다. 채널 목록을 data/briefing_channels.json에 추가하세요.</p>
          )}

          {(() => {
            // 영상이 있는 이슈만 (뉴스만 있는 폴백 클러스터 제외)
            const withVideo = data.briefing.ranked_issues.filter(
              (ri) => ri.cluster.videos.length > 0,
            );
            const visible = withVideo.slice(0, visibleCount);
            return (
              <>
                {withVideo.length !== data.briefing.ranked_issues.length && (
                  <div style={{ fontSize: 12, color: "#888", marginBottom: 8 }}>
                    영상 있는 이슈만 표시 ({withVideo.length} / 전체 {data.briefing.ranked_issues.length})
                  </div>
                )}
                {visible.map((ri) => (
                  <IssueCard key={ri.rank} issue={ri} plans={data.plans_by_rank[ri.rank]} />
                ))}
                {visibleCount < withVideo.length && (
                  <button
                    onClick={() => setVisibleCount((v) => v + LOAD_MORE_STEP)}
                    style={{
                      width: "100%", padding: 12, marginTop: 12,
                      background: "#f0f0f0", border: "1px solid #ccc", borderRadius: 6,
                      cursor: "pointer", fontSize: 14,
                    }}
                  >
                    더 보기 ({visibleCount} / {withVideo.length} 표시 중)
                  </button>
                )}
              </>
            );
          })()}
        </>
      )}
    </div>
  );
}

function IssueCard({ issue, plans }: { issue: RankedIssue; plans?: unknown }) {
  const [expanded, setExpanded] = useState(false);
  const top = issue.cluster.videos.length > 0
    ? issue.cluster.videos.reduce((a, b) => a.view_count > b.view_count ? a : b)
    : null;

  return (
    <div style={{
      border: "1px solid #ddd", borderRadius: 8, padding: 16, marginBottom: 12,
      background: issue.rank <= 3 ? "#fffef0" : "white",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
        <span style={{
          fontSize: 18, fontWeight: 700, color: issue.rank <= 3 ? "#c60" : "#666",
          minWidth: 30, textAlign: "center",
        }}>#{issue.rank}</span>
        <h3 style={{ flex: 1, fontSize: 17, fontWeight: 600, margin: 0 }}>{issue.cluster.topic}</h3>
        <span style={{ fontSize: 13, color: "#888" }}>score {Math.round(issue.score).toLocaleString()}</span>
      </div>

      <div style={{ fontSize: 13, color: "#666", marginBottom: 8 }}>
        영상 {issue.cluster.videos.length}개 · 기사 {issue.cluster.news.length}개 ·
        합산 {issue.cluster.total_views.toLocaleString()}회 · 댓글 {issue.cluster.total_comments.toLocaleString()}
      </div>

      {top && (
        <div style={{ display: "flex", gap: 12, marginBottom: 8 }}>
          {top.thumbnail_url && (
            <img src={top.thumbnail_url} alt="" style={{ width: 120, height: 68, objectFit: "cover", borderRadius: 4 }} />
          )}
          <div style={{ flex: 1, fontSize: 13 }}>
            <a href={top.url} target="_blank" rel="noopener" style={{ color: "#0066cc", textDecoration: "none" }}>
              {top.title}
            </a>
            <div style={{ color: "#888", marginTop: 4 }}>
              {top.channel_title} · {top.view_count.toLocaleString()}회 · 댓글 {top.comment_count.toLocaleString()}
            </div>
          </div>
        </div>
      )}

      <button
        onClick={() => setExpanded((v) => !v)}
        style={{
          fontSize: 13, color: "#0066cc", background: "none", border: "none",
          padding: 0, cursor: "pointer", marginTop: 4,
        }}
      >
        {expanded ? "▲ 접기" : "▼ 자세히 (기획안 / 영상 / 기사)"}
      </button>

      {expanded && (
        <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid #eee" }}>
          <PlansSection plans={plans} topVideoUrl={top?.url} />
          {issue.cluster.videos.length > 1 && (
            <div style={{ marginTop: 12 }}>
              <strong style={{ fontSize: 13 }}>다른 영상:</strong>
              <ul style={{ fontSize: 13, margin: "4px 0 0 16px" }}>
                {issue.cluster.videos.slice(1).map((v) => (
                  <li key={v.video_id}>
                    <a href={v.url} target="_blank" rel="noopener">{v.title}</a>{" "}
                    <span style={{ color: "#888" }}>({v.view_count.toLocaleString()}회)</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {issue.cluster.news.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <strong style={{ fontSize: 13 }}>관련 기사:</strong>
              <ul style={{ fontSize: 13, margin: "4px 0 0 16px" }}>
                {issue.cluster.news.map((n, i) => (
                  <li key={i}>
                    <a href={n.link} target="_blank" rel="noopener">{n.title}</a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function PlansSection({ plans, topVideoUrl }: { plans: unknown; topVideoUrl?: string }) {
  if (!plans) {
    return (
      <div style={{ fontSize: 13, color: "#888" }}>
        기획안이 아직 생성되지 않았습니다 (rank 6+ 또는 자막 부재).
      </div>
    );
  }
  // manual_required 표시
  if (typeof plans === "object" && plans !== null && "reason" in plans) {
    const p = plans as { reason: string; youtube_url?: string };
    return (
      <div style={{ padding: 8, background: "#fff5e6", borderRadius: 4, fontSize: 13 }}>
        ⚠️ {p.reason} —{" "}
        {p.youtube_url && <a href={p.youtube_url} target="_blank" rel="noopener">영상 보기</a>}
      </div>
    );
  }
  // ThreePlansResult — plans 배열 표시
  const result = plans as { plans?: Array<{ topic: string; hook: string; angle: string; cta: string }> };
  if (!result.plans || result.plans.length === 0) {
    return <div style={{ fontSize: 13, color: "#888" }}>기획안 데이터가 비어 있습니다.</div>;
  }
  return (
    <div>
      <strong style={{ fontSize: 13 }}>기획안 {result.plans.length}개:</strong>
      <div style={{ display: "grid", gap: 8, marginTop: 8 }}>
        {result.plans.map((p, i) => (
          <div key={i} style={{ padding: 10, background: "#f7f7f7", borderRadius: 4, fontSize: 13 }}>
            <div style={{ marginBottom: 4 }}>
              <strong>{p.topic}</strong>{" "}
              <span style={{ color: "#888", fontSize: 11 }}>[{p.angle}]</span>
            </div>
            <div style={{ color: "#444" }}>HOOK: {p.hook}</div>
            <div style={{ color: "#444" }}>CTA: {p.cta}</div>
          </div>
        ))}
      </div>
      {topVideoUrl && (
        <div style={{ marginTop: 8, fontSize: 12, color: "#666" }}>
          이 plan으로 영상을 만들려면: <code>python3 -m src.main political-pro {topVideoUrl}</code>{" "}
          또는 메인 페이지의 "정치_pro" 탭에서 URL 붙여넣고 실행
        </div>
      )}
    </div>
  );
}
