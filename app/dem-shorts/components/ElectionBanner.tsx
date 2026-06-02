// T101: ElectionBanner — 선거기간 중 대시보드 상단 경고 배너 (FR-030)
"use client";

import { useEffect, useState } from "react";

type NextElection = {
  type: "presidential_election" | "general_election";
  date: string;
  days_until: number;
  guard_threshold_days: number;
};

type ElectionStatus = {
  in_election_period: boolean;
  next_election: NextElection | null;
  neutral_mode_enforced: boolean;
};

const TYPE_LABEL: Record<NextElection["type"], string> = {
  presidential_election: "대통령 선거",
  general_election: "국회의원 총선거",
};

export function ElectionBanner() {
  const [status, setStatus] = useState<ElectionStatus | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/dem-shorts/election");
        if (!res.ok) throw new Error(`status ${res.status}`);
        const data = (await res.json()) as ElectionStatus;
        if (!cancelled) setStatus(data);
      } catch (e: unknown) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "선거 상태 조회 실패");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <div
        role="status"
        style={{
          padding: "8px 12px",
          background: "#fff3cd",
          color: "#856404",
          fontSize: 13,
          borderBottom: "1px solid #ffeeba",
        }}
      >
        선거 상태 조회 실패: {error}
      </div>
    );
  }

  if (!status) return null;

  // 선거기간 중이 아니면 배너 숨김 (FR-030: 선거기간 진입 시 표시)
  if (!status.in_election_period) return null;

  const next = status.next_election;
  const label = next ? TYPE_LABEL[next.type] : "선거";
  const daysUntil = next?.days_until ?? 0;
  const dateStr = next?.date ?? "";

  return (
    <div
      role="alert"
      data-testid="election-banner"
      style={{
        padding: "12px 16px",
        background: "linear-gradient(90deg, #fee2e2 0%, #fef3c7 100%)",
        color: "#7f1d1d",
        border: "1px solid #fca5a5",
        borderRadius: 6,
        marginBottom: 12,
        fontSize: 14,
        fontWeight: 600,
        display: "flex",
        alignItems: "center",
        gap: 12,
        flexWrap: "wrap",
      }}
    >
      <span style={{ fontSize: 18 }}>⚠️</span>
      <span>
        선거기간 중 — {label} D-{daysUntil} ({dateStr})
      </span>
      <span
        style={{
          marginLeft: "auto",
          fontSize: 12,
          fontWeight: 500,
          padding: "4px 8px",
          background: "#fff",
          borderRadius: 4,
          border: "1px solid #fca5a5",
        }}
      >
        중립 모드 강제 · 편향 임계값 30점 (FR-031)
      </span>
    </div>
  );
}
