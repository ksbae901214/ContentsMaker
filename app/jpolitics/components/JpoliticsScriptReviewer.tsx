"use client";

import { useState } from "react";

interface Narration {
  scene_id: number;
  text: string;
  voice_text: string;
  visual_layout: string;
  subtitle_color: string;
  subtitle_emphasis: boolean;
  clip_search_query?: string | null;
  cards_metadata?: Array<{ name: string; party: string; data_label?: string; data_value?: string }> | null;
}

interface JpoliticsPlan {
  rank: number;
  angle: string;
  topic: string;
  headline_pin: string;
  narrations: Narration[];
  cta: string;
  layout_classification: string;
  hook: string;
  clip_section: string;
  reason: string;
  flow_intro: string;
  flow_middle: string;
  flow_climax: string;
  format_type: string;
}

interface Props {
  plan: JpoliticsPlan;
  onRender: (overrides: Partial<JpoliticsPlan>) => void;
  onBack: () => void;
}

const SUBTITLE_COLORS = ["white", "yellow", "red", "blue"] as const;
const VISUAL_LAYOUTS = ["normal", "vs_card", "grid_2x2", "data_card"] as const;

export function JpoliticsScriptReviewer({ plan, onRender, onBack }: Props) {
  const [narrations, setNarrations] = useState<Narration[]>(plan.narrations);
  const [headlinePin, setHeadlinePin] = useState(plan.headline_pin);
  const [cta, setCta] = useState(plan.cta);

  function updateNarration(idx: number, changes: Partial<Narration>) {
    setNarrations((prev) =>
      prev.map((n, i) => (i === idx ? { ...n, ...changes } : n))
    );
  }

  function handleSubmit() {
    onRender({
      narrations,
      headline_pin: headlinePin,
      cta,
    });
  }

  const headlineLen = headlinePin.length;
  const headlineValid = headlineLen >= 8 && headlineLen <= 14;

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">씬 검수 & 편집</h2>
        <button onClick={onBack} className="text-sm text-gray-400 hover:text-white">
          ← 기획안 다시 선택
        </button>
      </div>

      {/* 고정 헤드라인 */}
      <div className="bg-gray-900 rounded-lg p-5">
        <label className="block text-sm font-bold mb-2">
          🟡 고정 헤드라인 (영상 전체, 8~14자)
        </label>
        <input
          type="text"
          value={headlinePin}
          onChange={(e) => setHeadlinePin(e.target.value)}
          className={`w-full p-3 rounded text-black font-bold text-center text-lg ${
            headlineValid ? "bg-yellow-400" : "bg-yellow-200"
          }`}
        />
        <p className={`text-xs mt-1 ${headlineValid ? "text-green-400" : "text-red-400"}`}>
          {headlineLen}자 {headlineValid ? "✓" : "(8~14자 필요)"}
        </p>
      </div>

      {/* 씬 편집 */}
      <div className="space-y-3">
        {narrations.map((n, idx) => (
          <div key={n.scene_id} className="bg-gray-900 rounded-lg p-4 space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-xs bg-gray-700 px-2 py-1 rounded">씬 {n.scene_id}</span>
              <select
                value={n.visual_layout}
                onChange={(e) => updateNarration(idx, { visual_layout: e.target.value })}
                className="text-xs bg-gray-800 rounded px-2 py-1"
              >
                {VISUAL_LAYOUTS.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
              <select
                value={n.subtitle_color}
                onChange={(e) => updateNarration(idx, { subtitle_color: e.target.value })}
                className="text-xs bg-gray-800 rounded px-2 py-1"
              >
                {SUBTITLE_COLORS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
              <label className="text-xs flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={n.subtitle_emphasis}
                  onChange={(e) =>
                    updateNarration(idx, { subtitle_emphasis: e.target.checked })
                  }
                />
                강조
              </label>
            </div>

            <label className="block text-xs text-gray-400">자막</label>
            <input
              type="text"
              value={n.text}
              onChange={(e) => updateNarration(idx, { text: e.target.value })}
              className="w-full p-2 bg-gray-800 rounded text-sm"
            />

            <label className="block text-xs text-gray-400">TTS 원문</label>
            <textarea
              value={n.voice_text}
              onChange={(e) => updateNarration(idx, { voice_text: e.target.value })}
              rows={2}
              className="w-full p-2 bg-gray-800 rounded text-sm"
            />

            {n.clip_search_query && (
              <p className="text-xs text-gray-500">
                🔍 클립 검색어: <code>{n.clip_search_query}</code>
              </p>
            )}
            {n.cards_metadata && n.cards_metadata.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-1">
                {n.cards_metadata.map((c, i) => (
                  <span
                    key={i}
                    className="text-xs bg-gray-800 px-2 py-1 rounded"
                  >
                    👤 {c.name} ({c.party})
                    {c.data_value && ` · ${c.data_label}=${c.data_value}`}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* CTA */}
      <div className="bg-gray-900 rounded-lg p-4">
        <label className="block text-sm font-bold mb-1">CTA</label>
        <input
          type="text"
          value={cta}
          onChange={(e) => setCta(e.target.value)}
          className="w-full p-2 bg-gray-800 rounded text-sm"
        />
      </div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!headlineValid}
        className="w-full bg-amber-600 hover:bg-amber-700 disabled:opacity-40 py-3 rounded font-bold"
      >
        🎬 영상 생성
      </button>
    </section>
  );
}
