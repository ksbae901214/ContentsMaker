// T093: 10-Item Compliance Gate UI (FR-025)
// ⚠️ "건너뛰기" 버튼 절대 미구현 — 기획서 6.1-2 권고
"use client";

import { useState } from "react";

export interface GateItemResult {
  status: "pass" | "fail" | "warn";
  reason?: string;
}

export interface GateResult {
  overall_status: "pass" | "fail" | "warn_only";
  risk_score: number;
  items: {
    item_1_commentary_length: string;
    item_2_ratio: string;
    item_3_duration: string;
    item_4_source_label: string;
    item_5_bias_guardrail: string;
    item_6_template_repeat: string;
    item_7_whitelist_person: string;
    item_8_election_guard: string;
    item_9_fact_checked: string;
    item_10_no_defamation: string;
  };
  failure_reasons: { item: string; reason: string }[];
  manual_fact_check_signed_by: string | null;
  manual_defamation_check_signed_by: string | null;
  is_passed?: boolean;
}

interface GateChecklistProps {
  draftId: number;
  onGatePassed: () => void;
  operatorId?: string;
}

const ITEM_LABELS: Record<string, string> = {
  item_1_commentary_length: "1. 해설 자막 50자 이상",
  item_2_ratio: "2. 원본≤50%, 해설≥30%",
  item_3_duration: "3. 전체 길이 ≤60초",
  item_4_source_label: "4. NATV 출처 표시",
  item_5_bias_guardrail: "5. 편향/혐오 가드레일 (경고)",
  item_6_template_repeat: "6. 최근 3회 연속 템플릿 아님 (경고)",
  item_7_whitelist_person: "7. Whitelist 인물 1명↑",
  item_8_election_guard: "8. 선거법 가드",
  item_9_fact_checked: "9. 수동 팩트 체크 서명",
  item_10_no_defamation: "10. 수동 명예훼손 체크 서명",
};

const BLOCKING_ITEMS = [
  "item_1_commentary_length",
  "item_2_ratio",
  "item_3_duration",
  "item_4_source_label",
  "item_7_whitelist_person",
  "item_8_election_guard",
  "item_9_fact_checked",
  "item_10_no_defamation",
];

function statusColor(status: string, isBlocking: boolean): string {
  if (status === "pass") return "#2e7d32";
  if (status === "warn") return "#f57c00";
  return isBlocking ? "#c62828" : "#c62828"; // 차단은 빨강, 경고는 주황
}

function statusIcon(status: string): string {
  if (status === "pass") return "✅";
  if (status === "warn") return "⚠️";
  return "❌";
}

export function GateChecklist({ draftId, onGatePassed, operatorId = "owner" }: GateChecklistProps) {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<GateResult | null>(null);
  const [error, setError] = useState("");
  const [factCheckSigned, setFactCheckSigned] = useState(false);
  const [defamationCheckSigned, setDefamationCheckSigned] = useState(false);

  const runGate = async () => {
    if (!factCheckSigned || !defamationCheckSigned) {
      setError("팩트 체크와 명예훼손 체크 두 항목 모두 확인 필요");
      return;
    }
    setRunning(true);
    setError("");
    try {
      const res = await fetch(`/api/dem-shorts/drafts/${draftId}/gate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          manual_fact_check: factCheckSigned,
          manual_defamation_check: defamationCheckSigned,
          operator_id: operatorId,
        }),
      });
      const data = await res.json();
      setResult(data);
      if (data.is_passed) {
        onGatePassed();
      }
    } catch (e: any) {
      setError(e.message || "게이트 실행 실패");
    } finally {
      setRunning(false);
    }
  };

  const isPassed = result?.is_passed === true;

  return (
    <div style={{ background: "#fafafa", padding: 20, borderRadius: 8 }}>
      <h3 style={{ margin: "0 0 8px 0" }}>⚖️ 10-Item Compliance Gate</h3>
      <p style={{ fontSize: 13, color: "#666", margin: "0 0 16px 0" }}>
        어떤 UI 조작으로도 미통과 항목이 있으면 렌더링/업로드 불가 (SC-005).
      </p>

      {/* 10개 아이템 결과 */}
      {result && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ padding: "8px 12px", background: isPassed ? "#e8f5e9" : "#ffebee", borderRadius: 6, marginBottom: 12 }}>
            <strong>종합: {result.overall_status.toUpperCase()} (risk={result.risk_score.toFixed(1)})</strong>
            {isPassed ? " — 렌더링 가능" : " — 미통과 항목을 수정하세요"}
          </div>
          <div style={{ display: "grid", gap: 4 }}>
            {Object.entries(result.items).map(([key, status]) => {
              const isBlocking = BLOCKING_ITEMS.includes(key);
              const reason = result.failure_reasons.find((r) => r.item === key)?.reason;
              return (
                <div
                  key={key}
                  style={{
                    padding: "8px 12px",
                    background: status === "pass" ? "#e8f5e9" : status === "warn" ? "#fff3e0" : "#ffebee",
                    borderRadius: 4,
                    display: "grid",
                    gridTemplateColumns: "auto 1fr auto",
                    gap: 12,
                    alignItems: "center",
                  }}
                >
                  <span>{statusIcon(status)}</span>
                  <span style={{ fontSize: 14, color: statusColor(status, isBlocking) }}>
                    {ITEM_LABELS[key]}
                    {reason && <span style={{ color: "#666", marginLeft: 8 }}>— {reason}</span>}
                  </span>
                  <span style={{ fontSize: 12, color: "#666" }}>
                    {isBlocking ? "🔒 차단" : "⚠️ 경고"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 수동 체크박스 2개 (item_9, item_10) */}
      <div style={{ background: "#fff", padding: 12, borderRadius: 6, marginBottom: 12, border: "1px solid #ddd" }}>
        <strong style={{ display: "block", marginBottom: 8 }}>운영자 수동 확인 (필수)</strong>
        <label style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
          <input
            type="checkbox"
            checked={factCheckSigned}
            onChange={(e) => setFactCheckSigned(e.target.checked)}
          />
          <span>9. 해설 내용 팩트 검증 완료 (최소 2개 출처 링크 포함)</span>
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <input
            type="checkbox"
            checked={defamationCheckSigned}
            onChange={(e) => setDefamationCheckSigned(e.target.checked)}
          />
          <span>10. 명예훼손 가능 표현 없음을 확인</span>
        </label>
      </div>

      {error && (
        <div style={{ color: "#c00", marginBottom: 12 }}>{error}</div>
      )}

      <button
        onClick={runGate}
        disabled={running || !factCheckSigned || !defamationCheckSigned}
        style={{
          padding: "10px 24px",
          background: running ? "#999" : "#0066cc",
          color: "#fff",
          border: "none",
          borderRadius: 4,
          cursor: running ? "default" : "pointer",
          fontSize: 15,
          fontWeight: 600,
        }}
      >
        {running ? "게이트 실행 중..." : "게이트 실행"}
      </button>
    </div>
  );
}
