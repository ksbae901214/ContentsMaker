"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { JpoliticsPlanPicker } from "./components/JpoliticsPlanPicker";
import { JpoliticsScriptReviewer } from "./components/JpoliticsScriptReviewer";

type SourceType = "youtube" | "topic";
type Status = "input" | "loading" | "picking" | "reviewing" | "rendering" | "done" | "error";

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

interface PlansResponse {
  ok: boolean;
  outputDir?: string;
  videoTitle?: string;
  videoDurationSec?: number;
  plans?: JpoliticsPlan[];
  error?: string;
  message?: string;
}

interface RenderResponse {
  ok: boolean;
  videoPath?: string;
  videoDurationSec?: number;
  summary?: { lines: string[]; hashtags: string[] };
  error?: string;
}

export default function JpoliticsPage() {
  const router = useRouter();
  const [sourceType, setSourceType] = useState<SourceType>("youtube");
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [topic, setTopic] = useState("");
  const [tone, setTone] = useState("분노·격앙");
  const [details, setDetails] = useState("");
  const [videoTitle, setVideoTitle] = useState("");
  const [status, setStatus] = useState<Status>("input");
  const [error, setError] = useState<string>("");
  const [outputDir, setOutputDir] = useState<string>("");
  const [plans, setPlans] = useState<JpoliticsPlan[] | null>(null);
  const [selectedPlan, setSelectedPlan] = useState<JpoliticsPlan | null>(null);
  const [renderResult, setRenderResult] = useState<RenderResponse | null>(null);

  async function handleGeneratePlans() {
    setError("");
    setStatus("loading");
    try {
      const body =
        sourceType === "youtube"
          ? { sourceType, youtubeUrl, videoTitle: videoTitle || undefined }
          : { sourceType, topic, tone, details };
      const res = await fetch("/api/jpolitics/plans", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data: PlansResponse = await res.json();
      if (!data.ok || !data.plans || !data.outputDir) {
        setError(data.message || data.error || "기획안 생성 실패");
        setStatus("error");
        return;
      }
      setPlans(data.plans);
      setOutputDir(data.outputDir);
      if (data.videoTitle) setVideoTitle(data.videoTitle);
      setStatus("picking");
    } catch (e) {
      setError(`네트워크 오류: ${String(e)}`);
      setStatus("error");
    }
  }

  async function handleRender(overrides: Partial<JpoliticsPlan>) {
    if (!selectedPlan) return;
    setError("");
    setStatus("rendering");
    try {
      const res = await fetch("/api/jpolitics/render", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          outputDir,
          selectedPlanRank: selectedPlan.rank,
          scriptOverrides: overrides,
        }),
      });
      const data: RenderResponse = await res.json();
      if (!data.ok) {
        setError(data.error || "영상 생성 실패");
        setStatus("error");
        return;
      }
      setRenderResult(data);
      setStatus("done");
    } catch (e) {
      setError(`렌더 오류: ${String(e)}`);
      setStatus("error");
    }
  }

  function reset() {
    setStatus("input");
    setError("");
    setPlans(null);
    setSelectedPlan(null);
    setRenderResult(null);
    setOutputDir("");
  }

  return (
    <main className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push("/")}
              className="text-gray-400 hover:text-white text-sm"
            >
              ← 메인
            </button>
            <h1 className="text-2xl font-bold">
              🟡 정치 V3 — @김정치입니다 포맷
            </h1>
          </div>
          <span className="text-xs text-gray-500">격리 모드 (jpolitics)</span>
        </div>

        {/* 검수 필수 배너 (FR-030) */}
        <div className="mb-6 bg-rose-900/40 border border-rose-700 rounded-lg p-4">
          <p className="text-sm">
            ⚠️ <strong>검수 필수</strong>: 생성된 영상의 사실 확인·법적 책임은 게시자에게 있습니다.
            정치 콘텐츠는 보도·논평 목적으로 한정하며, 자동 업로드는 영구 차단됩니다.
          </p>
        </div>

        {/* Status: input */}
        {status === "input" && (
          <section className="bg-gray-900 rounded-lg p-6">
            <div className="flex gap-2 mb-4">
              <button
                onClick={() => setSourceType("youtube")}
                className={`flex-1 py-2 rounded ${
                  sourceType === "youtube" ? "bg-amber-600" : "bg-gray-700"
                }`}
              >
                📺 YouTube URL
              </button>
              <button
                onClick={() => setSourceType("topic")}
                className={`flex-1 py-2 rounded ${
                  sourceType === "topic" ? "bg-amber-600" : "bg-gray-700"
                }`}
              >
                ✏️ 주제 입력
              </button>
            </div>

            {sourceType === "youtube" ? (
              <div className="space-y-3">
                <input
                  type="text"
                  placeholder="https://www.youtube.com/watch?v=..."
                  value={youtubeUrl}
                  onChange={(e) => setYoutubeUrl(e.target.value)}
                  className="w-full p-3 bg-gray-800 rounded text-sm"
                />
                <input
                  type="text"
                  placeholder="영상 제목 (선택)"
                  value={videoTitle}
                  onChange={(e) => setVideoTitle(e.target.value)}
                  className="w-full p-3 bg-gray-800 rounded text-sm"
                />
              </div>
            ) : (
              <div className="space-y-3">
                <input
                  type="text"
                  placeholder="주제 (예: 양향자 vs 추미애 경기도지사 대결)"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  className="w-full p-3 bg-gray-800 rounded text-sm"
                />
                <input
                  type="text"
                  placeholder="톤 (기본: 분노·격앙)"
                  value={tone}
                  onChange={(e) => setTone(e.target.value)}
                  className="w-full p-3 bg-gray-800 rounded text-sm"
                />
                <textarea
                  placeholder="상세 설명 (선택)"
                  value={details}
                  onChange={(e) => setDetails(e.target.value)}
                  rows={3}
                  className="w-full p-3 bg-gray-800 rounded text-sm"
                />
              </div>
            )}

            <button
              onClick={handleGeneratePlans}
              disabled={
                sourceType === "youtube" ? !youtubeUrl : !topic
              }
              className="mt-4 w-full bg-amber-600 hover:bg-amber-700 disabled:opacity-40 py-3 rounded font-bold"
            >
              3개 기획안 생성
            </button>
          </section>
        )}

        {/* Status: loading */}
        {status === "loading" && (
          <section className="bg-gray-900 rounded-lg p-10 text-center">
            <div className="animate-spin h-10 w-10 border-4 border-amber-500 border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-sm text-gray-400">
              Gemini → Claude 3개 기획안 생성 중 (약 30~60초)
            </p>
          </section>
        )}

        {/* Status: picking — 3 plans 노출 */}
        {status === "picking" && plans && (
          <JpoliticsPlanPicker
            plans={plans}
            onSelect={(plan) => {
              setSelectedPlan(plan);
              setStatus("reviewing");
            }}
          />
        )}

        {/* Status: reviewing — 사용자 검수 */}
        {status === "reviewing" && selectedPlan && (
          <JpoliticsScriptReviewer
            plan={selectedPlan}
            onRender={handleRender}
            onBack={() => setStatus("picking")}
          />
        )}

        {/* Status: rendering */}
        {status === "rendering" && (
          <section className="bg-gray-900 rounded-lg p-10 text-center">
            <div className="animate-spin h-10 w-10 border-4 border-amber-500 border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-sm text-gray-400">
              TTS 합성 + Remotion V3 렌더 중 (약 2~4분)
            </p>
          </section>
        )}

        {/* Status: done */}
        {status === "done" && renderResult && (
          <section className="bg-gray-900 rounded-lg p-6 space-y-4">
            <h2 className="text-xl font-bold">✅ 영상 생성 완료</h2>
            <p className="text-sm text-gray-400">
              경로: <code className="bg-gray-800 px-2 py-1 rounded">{renderResult.videoPath}</code>
            </p>
            <p className="text-sm text-gray-400">
              재생 시간: {renderResult.videoDurationSec?.toFixed(1)}초
            </p>
            {renderResult.summary && (
              <div className="bg-gray-800 rounded p-4 space-y-2">
                <h3 className="font-bold">3줄 요약</h3>
                <ul className="text-sm space-y-1">
                  {renderResult.summary.lines.map((l, i) => (
                    <li key={i}>• {l}</li>
                  ))}
                </ul>
                <h3 className="font-bold mt-3">해시태그</h3>
                <p className="text-sm">{renderResult.summary.hashtags.join(" ")}</p>
              </div>
            )}
            <p className="text-xs text-gray-500">
              ⚠️ 업로드 전 반드시 검수하세요. V3는 자동 업로드 기능을 제공하지 않습니다 (FR-029).
            </p>
            <button
              onClick={reset}
              className="bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded text-sm"
            >
              새 영상 생성
            </button>
          </section>
        )}

        {/* Status: error */}
        {status === "error" && (
          <section className="bg-red-900/40 border border-red-700 rounded-lg p-6">
            <p className="text-red-300 mb-3">❌ {error}</p>
            <button
              onClick={reset}
              className="bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded text-sm"
            >
              다시 시작
            </button>
          </section>
        )}
      </div>
    </main>
  );
}
