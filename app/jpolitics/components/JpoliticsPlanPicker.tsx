"use client";

interface JpoliticsPlan {
  rank: number;
  angle: string;
  format_type: string;
  layout_classification: string;
  topic: string;
  hook: string;
  clip_section: string;
  reason: string;
  flow_intro: string;
  flow_middle: string;
  flow_climax: string;
  narrations: Array<{
    scene_id: number;
    text: string;
    voice_text: string;
    visual_layout: string;
    subtitle_color: string;
    subtitle_emphasis: boolean;
    clip_search_query?: string | null;
    cards_metadata?: Array<{ name: string; party: string; data_label?: string; data_value?: string }> | null;
  }>;
  cta: string;
  headline_pin: string;
}

interface Props {
  plans: JpoliticsPlan[];
  onSelect: (plan: JpoliticsPlan) => void;
}

const ANGLE_LABEL: Record<string, string> = {
  title_anchor: "🎯 제목 후크",
  audience_resonance: "💬 시청자 공감",
  comparison: "⚖️ 비교 구도",
};

const LAYOUT_LABEL: Record<string, string> = {
  talking_head: "👤 1인 인터뷰",
  vs_2way: "⚔️ 2인 대결",
  comparison_grid: "🔲 다인 비교",
  data_comparison: "📊 데이터 강조",
};

export function JpoliticsPlanPicker({ plans, onSelect }: Props) {
  return (
    <section className="space-y-4">
      <h2 className="text-xl font-bold">기획안 3개 — 1개 선택</h2>
      {plans.map((plan) => (
        <div
          key={plan.rank}
          className="bg-gray-900 border border-gray-700 hover:border-amber-500 rounded-lg p-5 transition"
        >
          <div className="flex items-start justify-between mb-3">
            <div>
              <span className="text-xs bg-amber-700 px-2 py-0.5 rounded mr-2">
                Rank {plan.rank}
              </span>
              <span className="text-xs bg-gray-700 px-2 py-0.5 rounded mr-2">
                {ANGLE_LABEL[plan.angle] || plan.angle}
              </span>
              <span className="text-xs bg-gray-700 px-2 py-0.5 rounded">
                {LAYOUT_LABEL[plan.layout_classification] || plan.layout_classification}
              </span>
            </div>
            <button
              onClick={() => onSelect(plan)}
              className="bg-amber-600 hover:bg-amber-700 px-4 py-2 rounded text-sm font-bold"
            >
              이 기획안 선택
            </button>
          </div>

          <h3 className="text-lg font-bold mb-2">{plan.topic}</h3>
          <p className="text-sm text-gray-300 mb-1">
            <strong>후크:</strong> {plan.hook}
          </p>
          <p className="text-sm text-gray-400 mb-1">
            <strong>고정 헤드라인:</strong>{" "}
            <span className="bg-yellow-500 text-black px-2 py-0.5 rounded font-bold">
              {plan.headline_pin}
            </span>
          </p>
          <p className="text-xs text-gray-500 mb-2">
            <strong>핵심 구간:</strong> {plan.clip_section}
          </p>
          <p className="text-xs text-gray-400 italic">{plan.reason}</p>

          {plan.narrations.length > 0 && (
            <details className="mt-3 text-xs text-gray-500">
              <summary className="cursor-pointer">씬 {plan.narrations.length}개 미리보기</summary>
              <ul className="mt-2 ml-4 space-y-1">
                {plan.narrations.slice(0, 5).map((n) => (
                  <li key={n.scene_id}>
                    [{n.scene_id}] {n.text}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      ))}
    </section>
  );
}
