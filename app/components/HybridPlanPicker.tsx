"use client";

import { useState } from "react";

export interface HybridBeatDTO {
  kind: "tts" | "original";
  duration_sec: number;
  // TTS fields
  subtitle?: string;
  tts_text?: string;
  subtitle_color?: string;
  // original fields
  clip_start_sec?: number;
  clip_end_sec?: number;
  speaker_name?: string;
  quote_lines?: string[];
}

export interface HybridShortsPlanDTO {
  topic: string;
  hook: HybridBeatDTO;
  beats: HybridBeatDTO[];
  cta: HybridBeatDTO;
  angle: string;
  source_title?: string;
  source_channel?: string;
  _meta?: { tts_sec: number; original_sec: number; total_sec: number };
}

interface Props {
  plans: HybridShortsPlanDTO[];
  onSelect: (planIdx: number) => void;
  disabled?: boolean;
}

const ANGLE_LABEL: Record<string, string> = {
  title_anchor: "🎯 영상 제목 직결",
  audience_resonance: "💬 시청자 반응 공감",
  comparison: "⚖️ 비교·대조",
};

function fmtSec(sec: number): string {
  return `${sec.toFixed(0)}s`;
}

function fmtTime(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

export default function HybridPlanPicker({ plans, onSelect, disabled }: Props) {
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
        ⚠️ V3 하이브리드: 원본 발언 ~50% + TTS 논평 ~50%. 게시 전 검수 필수.
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: 16,
        }}
      >
        {plans.map((p, idx) => {
          const meta = p._meta;
          const allBeats = [p.hook, ...p.beats, p.cta];
          const ttsCount = allBeats.filter(b => b.kind === "tts").length;
          const origCount = allBeats.filter(b => b.kind === "original").length;

          return (
            <div
              key={idx}
              style={{
                border: "1px solid #4a3f6b",
                borderRadius: 8,
                padding: 16,
                background: "#0d0d1a",
              }}
            >
              {/* Angle badge */}
              <div style={{ marginBottom: 8 }}>
                <span
                  style={{
                    background: "#7c3aed",
                    color: "white",
                    padding: "2px 8px",
                    borderRadius: 4,
                    fontSize: 12,
                  }}
                >
                  {ANGLE_LABEL[p.angle] || p.angle}
                </span>
                <span style={{ marginLeft: 6, fontSize: 11, color: "#a78bfa" }}>
                  📺 V3 하이브리드
                </span>
              </div>

              {/* Topic */}
              <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 16 }}>
                {p.topic}
              </div>

              {/* Hook */}
              <div
                style={{
                  background: "#1a1a2e",
                  padding: 10,
                  borderRadius: 6,
                  marginBottom: 10,
                  fontSize: 14,
                  lineHeight: 1.4,
                  borderLeft: "3px solid #7c3aed",
                }}
              >
                🎣 <strong>{p.hook.subtitle || p.hook.tts_text}</strong>
              </div>

              {/* Beat stats */}
              {meta && (
                <div style={{ fontSize: 13, color: "#bbb", marginBottom: 8 }}>
                  <span style={{ color: "#a78bfa" }}>📢 TTS {fmtSec(meta.tts_sec)}</span>
                  {" · "}
                  <span style={{ color: "#34d399" }}>🎬 원본 {fmtSec(meta.original_sec)}</span>
                  {" · "}
                  <span style={{ color: "#9ca3af" }}>총 {fmtSec(meta.total_sec)}</span>
                </div>
              )}
              <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 8 }}>
                비트 {ttsCount + origCount}개 (TTS {ttsCount} / 원본 {origCount})
              </div>

              {/* Beat list expandable */}
              <details
                style={{ marginBottom: 10 }}
                open={expanded === idx}
                onToggle={(e) => {
                  if ((e.target as HTMLDetailsElement).open) setExpanded(idx);
                }}
              >
                <summary style={{ cursor: "pointer", fontSize: 13, color: "#888" }}>
                  비트 구성 보기
                </summary>
                <div style={{ paddingTop: 8, fontSize: 12 }}>
                  {allBeats.map((b, bi) => (
                    <div
                      key={bi}
                      style={{
                        marginBottom: 4,
                        padding: "4px 8px",
                        borderRadius: 4,
                        background: b.kind === "tts" ? "#1e1b3a" : "#0d2b1e",
                        borderLeft: `2px solid ${b.kind === "tts" ? "#7c3aed" : "#10b981"}`,
                      }}
                    >
                      <span style={{ color: b.kind === "tts" ? "#a78bfa" : "#34d399", fontWeight: 600 }}>
                        {b.kind === "tts" ? "📢" : "🎬"} {b.kind.toUpperCase()}
                      </span>
                      {" "}
                      <span style={{ color: "#6b7280" }}>
                        {fmtSec(b.duration_sec)}
                      </span>
                      {" · "}
                      <span style={{ color: "#e5e7eb" }}>
                        {b.kind === "tts"
                          ? (b.subtitle || b.tts_text || "")
                          : (b.quote_lines?.[0] || `${fmtTime(b.clip_start_sec ?? 0)}~${fmtTime(b.clip_end_sec ?? 0)}`)}
                      </span>
                    </div>
                  ))}
                </div>
              </details>

              {/* CTA */}
              <div
                style={{
                  fontSize: 13,
                  color: "#aaa",
                  marginBottom: 12,
                  paddingTop: 8,
                  borderTop: "1px solid #222",
                }}
              >
                🎬 <strong>CTA:</strong> {p.cta.subtitle || p.cta.tts_text}
              </div>

              <button
                type="button"
                disabled={disabled}
                onClick={() => onSelect(idx)}
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  background: disabled ? "#444" : "#7c3aed",
                  color: "white",
                  border: "none",
                  borderRadius: 6,
                  cursor: disabled ? "not-allowed" : "pointer",
                  fontSize: 14,
                  fontWeight: 600,
                }}
              >
                이 기획안으로 하이브리드 렌더
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
