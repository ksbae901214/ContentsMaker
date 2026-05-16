"use client";

import { useState } from "react";

export interface NarrationDTO {
  start_sec: number;
  end_sec: number;
  text: string;
}

export interface ShortsPlanDTO {
  topic: string;
  hook: string;
  clip_start_sec: number;
  clip_end_sec: number;
  clip_reason: string;
  flow_intro: string;
  flow_middle: string;
  flow_climax: string;
  narrations: NarrationDTO[];
  cta: string;
  angle: "title_anchor" | "audience_resonance" | "comparison" | string;
}

interface Props {
  plans: ShortsPlanDTO[];
  onSelect: (planIdx: number) => void;
  disabled?: boolean;
}

const ANGLE_LABEL: Record<string, string> = {
  title_anchor: "🎯 영상 제목 직결",
  audience_resonance: "💬 시청자 반응 공감",
  comparison: "⚖️ 비교·대조",
};

function fmtTime(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

export default function PoliticalPlanPicker({ plans, onSelect, disabled }: Props) {
  const [expanded, setExpanded] = useState<number | null>(null);

  if (!plans || plans.length !== 3) {
    return (
      <div style={{ padding: 16, color: "#666" }}>
        기획안이 3개가 아닙니다 ({plans?.length ?? 0}개)
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 12, fontSize: 14, color: "#888" }}>
        ⚠️ 출력은 자동 생성 결과입니다. 게시 전 사용자 검수가 필요합니다.
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: 16,
        }}
      >
        {plans.map((p, idx) => (
          <div
            key={idx}
            style={{
              border: "1px solid #333",
              borderRadius: 8,
              padding: 16,
              background: "#0f0f0f",
            }}
          >
            <div style={{ marginBottom: 8 }}>
              <span
                style={{
                  background: "#ff5757",
                  color: "white",
                  padding: "2px 8px",
                  borderRadius: 4,
                  fontSize: 12,
                }}
              >
                {ANGLE_LABEL[p.angle] || p.angle}
              </span>
            </div>

            <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 16 }}>{p.topic}</div>

            <div
              style={{
                background: "#1a1a1a",
                padding: 10,
                borderRadius: 6,
                marginBottom: 10,
                fontSize: 14,
                lineHeight: 1.4,
                borderLeft: "3px solid #ff5757",
              }}
            >
              💥 <strong>{p.hook}</strong>
            </div>

            <div style={{ fontSize: 13, color: "#bbb", marginBottom: 8 }}>
              📍 사용 구간: <strong style={{ color: "#fff" }}>
                {fmtTime(p.clip_start_sec)} ~ {fmtTime(p.clip_end_sec)}
              </strong>
              <div style={{ marginTop: 4, color: "#999" }}>{p.clip_reason}</div>
            </div>

            <details
              style={{ marginBottom: 10 }}
              open={expanded === idx}
              onToggle={(e) => {
                if ((e.target as HTMLDetailsElement).open) setExpanded(idx);
              }}
            >
              <summary style={{ cursor: "pointer", fontSize: 13, color: "#888" }}>
                구성 흐름 + 나레이션 ({p.narrations?.length || 0}줄)
              </summary>
              <div style={{ paddingTop: 8, fontSize: 13 }}>
                <div style={{ marginBottom: 6 }}>
                  <strong style={{ color: "#ff5757" }}>시작</strong> · {p.flow_intro}
                </div>
                <div style={{ marginBottom: 6 }}>
                  <strong style={{ color: "#ff5757" }}>중간</strong> · {p.flow_middle}
                </div>
                <div style={{ marginBottom: 12 }}>
                  <strong style={{ color: "#ff5757" }}>클라이맥스</strong> · {p.flow_climax}
                </div>
                <div style={{ marginTop: 8 }}>
                  {(p.narrations || []).map((n, ni) => (
                    <div key={ni} style={{ marginBottom: 4, color: "#ddd" }}>
                      <span style={{ color: "#888" }}>
                        ({n.start_sec.toFixed(0)}~{n.end_sec.toFixed(0)}초)
                      </span>{" "}
                      "{n.text}"
                    </div>
                  ))}
                </div>
              </div>
            </details>

            <div
              style={{
                fontSize: 13,
                color: "#aaa",
                marginBottom: 12,
                paddingTop: 8,
                borderTop: "1px solid #222",
              }}
            >
              🎬 <strong>CTA:</strong> {p.cta}
            </div>

            <button
              type="button"
              disabled={disabled}
              onClick={() => onSelect(idx)}
              style={{
                width: "100%",
                padding: "10px 12px",
                background: disabled ? "#444" : "#ff5757",
                color: "white",
                border: "none",
                borderRadius: 6,
                cursor: disabled ? "not-allowed" : "pointer",
                fontSize: 14,
                fontWeight: 600,
              }}
            >
              이 기획안으로 진행
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
