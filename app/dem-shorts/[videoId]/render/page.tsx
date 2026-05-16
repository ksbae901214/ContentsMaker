// T091: 해설 자막 작성 + 실시간 글자 수 경고 + 팩트 URL 입력 + 게이트 실행
// (FR-024, FR-029)
"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { CommentaryEditor, type CommentaryBlock } from "../../components/CommentaryEditor";
import { ElectionBanner } from "../../components/ElectionBanner";
import { GateChecklist } from "../../components/GateChecklist";
import { UploadDialog } from "../../components/UploadDialog";

const PRESETS = ["leejaemyung", "jungcheongrae", "youth", "hotissue", "default"] as const;
const TTS_VOICES = ["male_strong", "male_stable", "female_calm", "female_young"] as const;

interface Draft {
  id: number;
  segment_id: number;
  cut_start_sec: number;
  cut_end_sec: number;
  commentary_blocks: CommentaryBlock[];
  commentary_char_count: number;
  tts_voice: string | null;
  tts_enabled: boolean;
  subtitle_preset: string;
  bgm_filename: string | null;
  fact_source_urls: string[];
  risk_score: number;
  status: string;
  rendered_path: string | null;
}

export default function RenderEditorPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const videoId = params?.videoId as string;
  const draftIdParam = searchParams.get("draft_id");

  const [draft, setDraft] = useState<Draft | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [genBusy, setGenBusy] = useState(false);
  const [candidates, setCandidates] = useState<{ text: string; confidence: number }[]>([]);
  const [gateRun, setGateRun] = useState(false);
  const [gatePassed, setGatePassed] = useState(false);
  const [rendering, setRendering] = useState(false);
  const [renderedPath, setRenderedPath] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [uploadedUrl, setUploadedUrl] = useState<string | null>(null);

  const loadDraft = useCallback(async () => {
    if (!draftIdParam) {
      setError("draft_id 쿼리 파라미터가 필요합니다");
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`/api/dem-shorts/drafts/${draftIdParam}`);
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.error || `HTTP ${res.status}`);
      }
      const d = await res.json();
      setDraft(d);
      setRenderedPath(d.rendered_path);
      setGatePassed(d.status === "gate_passed" || d.status === "rendered" || d.status === "uploaded");
    } catch (e: any) {
      setError(e.message || "draft 로드 실패");
    } finally {
      setLoading(false);
    }
  }, [draftIdParam]);

  useEffect(() => {
    loadDraft();
  }, [loadDraft]);

  if (loading) return <div style={{ padding: 24 }}>로딩 중...</div>;
  if (error || !draft) {
    return <div style={{ padding: 24, color: "#c00" }}>{error || "draft를 찾을 수 없습니다"}</div>;
  }

  const cutDuration = draft.cut_end_sec - draft.cut_start_sec;

  const patch = async (body: Partial<Draft>) => {
    setSaving(true);
    setError("");
    try {
      const res = await fetch(`/api/dem-shorts/drafts/${draft.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.error || `HTTP ${res.status}`);
      }
      const updated = await res.json();
      setDraft(updated);
    } catch (e: any) {
      setError(e.message || "저장 실패");
    } finally {
      setSaving(false);
    }
  };

  const generateCommentary = async () => {
    setGenBusy(true);
    setCandidates([]);
    try {
      const res = await fetch(`/api/dem-shorts/drafts/${draft.id}/commentary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tone_hint: "팩트 기반 객관적", max_chars_per_candidate: 15 }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.error || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setCandidates(data.candidates || []);
    } catch (e: any) {
      setError(e.message || "해설 생성 실패");
    } finally {
      setGenBusy(false);
    }
  };

  const startRender = async () => {
    if (!gatePassed) {
      setError("게이트 통과 후 렌더링 가능");
      return;
    }
    setRendering(true);
    setError("");
    try {
      const res = await fetch(`/api/dem-shorts/drafts/${draft.id}/render`, {
        method: "POST",
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.error || `HTTP ${res.status}`);
      }
      // SSE 스트림 처리 단순화: 전체 body 읽기
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value);
          const lines = chunk.split("\n");
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const evt = JSON.parse(line.slice(6));
                if (evt.type === "done") {
                  setRenderedPath(evt.rendered_path);
                } else if (evt.type === "error") {
                  setError(evt.error);
                }
              } catch {}
            }
          }
        }
      }
    } catch (e: any) {
      setError(e.message || "렌더링 실패");
    } finally {
      setRendering(false);
    }
  };

  const totalChars = draft.commentary_blocks.reduce((s, b) => s + (b.text || "").length, 0);

  return (
    <main style={{ maxWidth: 1000, margin: "0 auto", padding: "24px 16px" }}>
      <ElectionBanner />
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>
          쇼츠 초안 #{draft.id} 편집
        </h1>
        <p style={{ color: "#666", fontSize: 13, marginTop: 4 }}>
          영상: {videoId} · 컷: {draft.cut_start_sec}s → {draft.cut_end_sec}s ({cutDuration}s)
          · 상태: <strong>{draft.status}</strong>
        </p>
      </header>

      {saving && <div style={{ color: "#0066cc", marginBottom: 8 }}>저장 중...</div>}
      {error && <div style={{ color: "#c00", marginBottom: 12 }}>{error}</div>}

      {/* 1. AI 해설 후보 생성 */}
      <section style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
          <h2 style={{ fontSize: 18, margin: 0 }}>1. AI 해설 후보 생성</h2>
          <button
            onClick={generateCommentary}
            disabled={genBusy}
            style={{ padding: "6px 14px", background: "#0066cc", color: "#fff", border: "none", borderRadius: 4 }}
          >
            {genBusy ? "생성 중..." : "🤖 3개 후보 생성"}
          </button>
        </div>
        {candidates.length > 0 && (
          <div style={{ display: "grid", gap: 8 }}>
            {candidates.map((c, i) => (
              <div
                key={i}
                style={{ padding: 10, background: "#f5f5f5", borderRadius: 4, cursor: "pointer" }}
                onClick={() => {
                  // 후보를 클릭하면 마지막 블록으로 추가
                  const lastEnd = draft.commentary_blocks.length > 0
                    ? draft.commentary_blocks[draft.commentary_blocks.length - 1].end
                    : 0;
                  const newBlocks = [
                    ...draft.commentary_blocks,
                    {
                      start: Math.min(lastEnd, cutDuration - 1),
                      end: Math.min(lastEnd + 3, cutDuration),
                      text: c.text,
                      style: "medium" as const,
                    },
                  ];
                  patch({ commentary_blocks: newBlocks });
                }}
              >
                "{c.text}" (신뢰도 {(c.confidence * 100).toFixed(0)}%)
                <span style={{ color: "#999", fontSize: 12, marginLeft: 8 }}>클릭해 블록으로 추가</span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 2. 해설 블록 편집 */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, margin: "0 0 12px 0" }}>2. 해설 블록 편집 (실시간 글자 수 검증)</h2>
        <CommentaryEditor
          blocks={draft.commentary_blocks}
          onChange={(blocks) => patch({ commentary_blocks: blocks })}
          maxDuration={cutDuration}
        />
        <div style={{ marginTop: 8, fontSize: 13, color: totalChars < 50 ? "#c00" : "#090" }}>
          현재 {totalChars}자 (게이트 통과를 위해 50자 이상 필요)
        </div>
      </section>

      {/* 3. TTS + 자막 프리셋 + BGM */}
      <section style={{ marginBottom: 24, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
        <label>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>자막 프리셋</div>
          <select
            value={draft.subtitle_preset}
            onChange={(e) => patch({ subtitle_preset: e.target.value })}
            style={{ width: "100%", padding: 8 }}
          >
            {PRESETS.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </label>
        <label>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>TTS 보이스</div>
          <select
            value={draft.tts_voice || ""}
            onChange={(e) => patch({ tts_voice: e.target.value || null, tts_enabled: !!e.target.value })}
            style={{ width: "100%", padding: 8 }}
          >
            <option value="">사용 안 함</option>
            {TTS_VOICES.map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
        </label>
        <label>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>BGM 파일명 (manifest 등록 필수)</div>
          <input
            type="text"
            value={draft.bgm_filename || ""}
            onChange={(e) => patch({ bgm_filename: e.target.value || null })}
            placeholder="calm_01.mp3"
            style={{ width: "100%", padding: 8 }}
          />
        </label>
      </section>

      {/* 4. 팩트 링크 */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, margin: "0 0 8px 0" }}>3. 팩트 출처 URL (최소 2개, FR-029)</h2>
        {draft.fact_source_urls.map((url, i) => (
          <div key={i} style={{ display: "flex", gap: 8, marginBottom: 6 }}>
            <input
              type="url"
              value={url}
              onChange={(e) => {
                const updated = [...draft.fact_source_urls];
                updated[i] = e.target.value;
                patch({ fact_source_urls: updated });
              }}
              style={{ flex: 1, padding: 6 }}
            />
            <button
              onClick={() => patch({ fact_source_urls: draft.fact_source_urls.filter((_, idx) => idx !== i) })}
              style={{ padding: "4px 10px", background: "#cc0000", color: "#fff", border: "none", borderRadius: 4 }}
            >
              삭제
            </button>
          </div>
        ))}
        <button
          onClick={() => patch({ fact_source_urls: [...draft.fact_source_urls, "https://"] })}
          style={{ padding: "4px 14px", background: "#0066cc", color: "#fff", border: "none", borderRadius: 4 }}
        >
          + URL 추가
        </button>
      </section>

      {/* 5. 컴플라이언스 게이트 */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, margin: "0 0 12px 0" }}>4. 컴플라이언스 게이트</h2>
        <GateChecklist
          draftId={draft.id}
          onGatePassed={() => setGatePassed(true)}
          operatorId="owner"
        />
      </section>

      {/* 6. 렌더링 */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, margin: "0 0 12px 0" }}>5. 렌더링</h2>
        <button
          onClick={startRender}
          disabled={!gatePassed || rendering}
          style={{
            padding: "10px 24px",
            background: gatePassed ? "#009900" : "#ccc",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            cursor: gatePassed ? "pointer" : "not-allowed",
            fontWeight: 600,
          }}
        >
          {rendering ? "렌더링 중..." : gatePassed ? "🎬 렌더링 시작" : "게이트 통과 후 가능"}
        </button>
        {renderedPath && (
          <div style={{ marginTop: 10, color: "#090" }}>
            ✅ 렌더링 완료: {renderedPath}
          </div>
        )}
      </section>

      {/* 7. 업로드 */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, margin: "0 0 12px 0" }}>6. YouTube 업로드</h2>
        <button
          onClick={() => setShowUpload(true)}
          disabled={!renderedPath}
          style={{
            padding: "10px 24px",
            background: renderedPath ? "#cc0000" : "#ccc",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            cursor: renderedPath ? "pointer" : "not-allowed",
            fontWeight: 600,
          }}
        >
          🚀 업로드 다이얼로그 열기
        </button>
        {uploadedUrl && (
          <div style={{ marginTop: 10, color: "#090" }}>
            ✅ 업로드됨: <a href={uploadedUrl} target="_blank" rel="noopener noreferrer">{uploadedUrl}</a>
          </div>
        )}
      </section>

      <UploadDialog
        draftId={draft.id}
        defaultTitle={`쇼츠 #${draft.id}`}
        defaultDescription={
          `NATV 국회방송 영상을 요약했습니다.\n\n📺 출처: NATV 국회방송\n📰 팩트 링크:\n` +
          draft.fact_source_urls.map((u) => `- ${u}`).join("\n") + "\n"
        }
        defaultTags={["NATV", "정치"]}
        open={showUpload}
        onClose={() => setShowUpload(false)}
        onUploaded={(url) => setUploadedUrl(url)}
      />
    </main>
  );
}
