"use client";
import { useState, useRef } from "react";

// ── Types ──────────────────────────────────────────────────────────────────

interface MomentData {
  start_sec: number;
  end_sec: number;
  kind: string;
  speaker: string;
  summary: string;
  hook_question: string;
  keywords: string[];
  confidence: number;
}

interface DetectResult {
  workDir: string;
  videoTitle: string;
  channel: string;
  detector: string;
  moments: MomentData[];
}

interface MetaResult {
  titleCandidates: string[];
  hashtags: string[];
  pinnedComment: string;
}

type AppState = "idle" | "detecting" | "moments" | "processing" | "done" | "error";

const KIND_LABEL: Record<string, string> = {
  laughter: "😂 웃음",
  clash: "⚔️ 충돌",
  outburst: "📢 언성",
  gaffe: "🫢 실언",
  silence: "🤐 정적",
  other: "✨ 기타",
};

// ── Component ──────────────────────────────────────────────────────────────

export default function JpoliticsPage() {
  const [state, setState] = useState<AppState>("idle");
  const [url, setUrl] = useState("");
  const [noMultimodal, setNoMultimodal] = useState(false);
  const [detectResult, setDetectResult] = useState<DetectResult | null>(null);
  const [selectedIdx, setSelectedIdx] = useState(1); // 1-based
  const [cropX, setCropX] = useState(0.5);
  const [pad, setPad] = useState(0.5);
  const [progress, setProgress] = useState<string[]>([]);
  const [outputPath, setOutputPath] = useState("");
  const [metaResult, setMetaResult] = useState<MetaResult | null>(null);
  const [metaLoading, setMetaLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  function isValidYouTubeUrl(u: string): boolean {
    try {
      const parsed = new URL(u);
      const host = parsed.hostname.toLowerCase();
      return (
        host === "www.youtube.com" ||
        host === "youtube.com" ||
        host === "m.youtube.com" ||
        host === "youtu.be"
      );
    } catch {
      return false;
    }
  }

  async function handleDetect() {
    if (!url.trim() || !isValidYouTubeUrl(url.trim())) {
      setErrorMsg("YouTube URL을 입력하세요 (youtube.com / youtu.be)");
      setState("error");
      return;
    }
    setState("detecting");
    setErrorMsg("");
    setDetectResult(null);
    setOutputPath("");
    setMetaResult(null);
    setProgress(["📥 영상 다운로드 + 모먼트 검출 중..."]);

    try {
      const res = await fetch("/api/jpolitics/detect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim(), noMultimodal }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        setErrorMsg(data.detail || data.error || "검출 실패");
        setState("error");
        return;
      }
      setDetectResult(data as DetectResult);
      setSelectedIdx(1);
      setState("moments");
    } catch (e: unknown) {
      setErrorMsg(e instanceof Error ? e.message : "네트워크 오류");
      setState("error");
    }
  }

  async function handleRender() {
    if (!detectResult) return;
    setState("processing");
    setProgress([]);
    setOutputPath("");
    setMetaResult(null);

    abortRef.current = new AbortController();

    try {
      const res = await fetch("/api/jpolitics/render", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workDir: detectResult.workDir,
          momentIdx: selectedIdx,
          cropX,
          pad,
        }),
        signal: abortRef.current.signal,
      });

      if (!res.ok || !res.body) {
        setErrorMsg("렌더 API 오류");
        setState("error");
        return;
      }

      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const evt = JSON.parse(line.slice(6));
            if (evt.type === "progress") {
              setProgress((p) => [...p, evt.message]);
            } else if (evt.type === "done") {
              setOutputPath(evt.outputPath || "");
              setState("done");
            } else if (evt.type === "error") {
              setErrorMsg(evt.message || "렌더 실패");
              setState("error");
            }
          } catch {
            // ignore parse errors
          }
        }
      }
    } catch (e: unknown) {
      if ((e as { name?: string }).name === "AbortError") {
        setErrorMsg("렌더가 취소되었습니다");
      } else {
        setErrorMsg(e instanceof Error ? e.message : "렌더 오류");
      }
      setState("error");
    }
  }

  async function handleLoadMeta() {
    if (!detectResult) return;
    setMetaLoading(true);
    try {
      const res = await fetch("/api/jpolitics/meta", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workDir: detectResult.workDir,
          momentIdx: selectedIdx,
        }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        setMetaResult(null);
      } else {
        setMetaResult(data as MetaResult);
      }
    } catch {
      setMetaResult(null);
    } finally {
      setMetaLoading(false);
    }
  }

  async function copyText(text: string, idx: number) {
    await navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 1500);
  }

  function handleReset() {
    setState("idle");
    setUrl("");
    setDetectResult(null);
    setOutputPath("");
    setMetaResult(null);
    setProgress([]);
    setErrorMsg("");
  }

  const selectedMoment = detectResult?.moments[selectedIdx - 1] ?? null;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-4 max-w-lg mx-auto">
      {/* Header */}
      <div className="mb-4">
        <h1 className="text-xl font-bold text-amber-400">
          🟡 정치쇼츠 V3 — 모먼트 직캠
        </h1>
        <p className="text-xs text-gray-400 mt-0.5">
          감정이 터진 순간을 잘라내는 정치 숏폼 생성기
        </p>
      </div>

      {/* Warning banner */}
      <div className="mb-4 rounded-lg p-3 bg-gradient-to-r from-rose-900/60 to-amber-900/60 border border-rose-700/50">
        <p className="text-xs font-semibold text-rose-200">
          ⚠️ 검수 필수 &nbsp;|&nbsp; 자동 업로드 차단 &nbsp;|&nbsp; 원본 영상 저작권 확인 후 사용
        </p>
      </div>

      {/* ── IDLE: URL input ─────────────────────────────────────────────── */}
      {(state === "idle" || state === "error") && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              YouTube URL
            </label>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleDetect()}
              placeholder="https://www.youtube.com/watch?v=..."
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-amber-500"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              id="noMultimodal"
              type="checkbox"
              checked={noMultimodal}
              onChange={(e) => setNoMultimodal(e.target.checked)}
              className="w-4 h-4 rounded accent-amber-500"
            />
            <label htmlFor="noMultimodal" className="text-xs text-gray-400">
              Gemini 멀티모달 생략 (transcript 폴백 — 무료 한도 절약)
            </label>
          </div>

          {state === "error" && errorMsg && (
            <div className="rounded-lg p-3 bg-red-900/40 border border-red-700/50">
              <p className="text-sm text-red-300">❌ {errorMsg}</p>
            </div>
          )}

          <button
            onClick={handleDetect}
            disabled={!url.trim()}
            className="w-full py-3 rounded-lg font-bold text-sm bg-amber-600 hover:bg-amber-500 active:bg-amber-700 disabled:opacity-40 disabled:cursor-not-allowed transition"
          >
            🔍 모먼트 검출 시작
          </button>

          <div className="grid grid-cols-3 gap-2 text-xs text-center text-gray-400">
            <div>
              <div>📥 입력</div>
              <div className="font-medium text-gray-200">YouTube URL</div>
            </div>
            <div>
              <div>⚙️ 처리</div>
              <div className="font-medium text-gray-200">~3분</div>
            </div>
            <div>
              <div>📁 출력</div>
              <div className="font-medium text-gray-200">9:16 MP4</div>
            </div>
          </div>
        </div>
      )}

      {/* ── DETECTING ───────────────────────────────────────────────────── */}
      {state === "detecting" && (
        <div className="space-y-4">
          <div className="rounded-lg p-4 bg-gray-800 border border-gray-700">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-5 h-5 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm font-medium text-amber-300">모먼트 검출 중...</span>
            </div>
            {progress.map((msg, i) => (
              <p key={i} className="text-xs text-gray-400">{msg}</p>
            ))}
          </div>
          <p className="text-xs text-gray-500 text-center">
            영상 다운로드 + 감정 모먼트 분석 중 (2~5분 소요)
          </p>
        </div>
      )}

      {/* ── MOMENTS: select a moment ────────────────────────────────────── */}
      {state === "moments" && detectResult && (
        <div className="space-y-4">
          <div className="rounded-lg p-3 bg-gray-800 border border-gray-700">
            <p className="text-xs text-gray-400 mb-0.5">
              📺 {detectResult.channel || "채널 미상"}
            </p>
            <p className="text-sm font-medium line-clamp-2">{detectResult.videoTitle}</p>
            <p className="text-xs text-gray-500 mt-1">
              검출기: {detectResult.detector} &nbsp;|&nbsp;
              모먼트 {detectResult.moments.length}개
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              모먼트 선택
            </label>
            <div className="space-y-2">
              {detectResult.moments.map((m, i) => (
                <button
                  key={i}
                  onClick={() => setSelectedIdx(i + 1)}
                  className={`w-full text-left rounded-lg p-3 border transition ${
                    selectedIdx === i + 1
                      ? "border-amber-500 bg-amber-900/20"
                      : "border-gray-700 bg-gray-800 hover:border-gray-500"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-amber-300">
                      [{i + 1}] {KIND_LABEL[m.kind] ?? m.kind}
                    </span>
                    <span className="text-xs text-gray-400">
                      {m.start_sec.toFixed(0)}s~{m.end_sec.toFixed(0)}s &nbsp;
                      확신도 {(m.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="text-xs text-yellow-200 font-medium">{m.hook_question}</p>
                  <p className="text-xs text-gray-400 mt-0.5 line-clamp-2">{m.summary}</p>
                  {m.speaker && (
                    <p className="text-xs text-blue-300 mt-0.5">👤 {m.speaker}</p>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Crop / Pad options */}
          <div className="rounded-lg p-3 bg-gray-800 border border-gray-700 space-y-3">
            <p className="text-xs font-medium text-gray-300">렌더 옵션</p>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">
                가로 크롭 중심 (0=왼쪽 / 0.5=가운데 / 1=오른쪽): {cropX.toFixed(2)}
              </label>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={cropX}
                onChange={(e) => setCropX(parseFloat(e.target.value))}
                className="w-full accent-amber-500"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">
                여유 시간(초): {pad.toFixed(1)}s
              </label>
              <input
                type="range"
                min={0}
                max={3}
                step={0.1}
                value={pad}
                onChange={(e) => setPad(parseFloat(e.target.value))}
                className="w-full accent-amber-500"
              />
            </div>
          </div>

          <button
            onClick={handleRender}
            className="w-full py-3 rounded-lg font-bold text-sm bg-amber-600 hover:bg-amber-500 active:bg-amber-700 transition"
          >
            🎬 모먼트 [{selectedIdx}] 렌더 시작
          </button>

          <button
            onClick={handleReset}
            className="w-full py-2 rounded-lg text-xs text-gray-400 bg-gray-800 hover:bg-gray-700 transition"
          >
            ↩ 처음으로
          </button>
        </div>
      )}

      {/* ── PROCESSING: SSE progress ────────────────────────────────────── */}
      {state === "processing" && (
        <div className="space-y-4">
          <div className="rounded-lg p-4 bg-gray-800 border border-gray-700">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-5 h-5 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm font-medium text-amber-300">렌더 진행 중...</span>
            </div>
            <div className="space-y-1">
              {progress.map((msg, i) => (
                <p key={i} className={`text-xs ${i === progress.length - 1 ? "text-gray-200" : "text-gray-500"}`}>
                  {msg}
                </p>
              ))}
            </div>
          </div>
          <p className="text-xs text-gray-500 text-center">
            클립 컷 + Remotion 렌더 중 (1~4분 소요)
          </p>
        </div>
      )}

      {/* ── DONE ────────────────────────────────────────────────────────── */}
      {state === "done" && (
        <div className="space-y-4">
          <div className="rounded-lg p-4 bg-green-900/30 border border-green-700/50">
            <p className="text-sm font-bold text-green-300 mb-1">✅ 렌더 완료!</p>
            <p className="text-xs text-gray-300 break-all">{outputPath}</p>
          </div>

          {/* Warning */}
          <div className="rounded-lg p-3 bg-rose-900/30 border border-rose-700/50">
            <p className="text-xs text-rose-300 font-semibold">
              ⛔ 자동 업로드 차단 — 반드시 수동 검수 후 업로드하세요
            </p>
            <p className="text-xs text-rose-400 mt-1">
              원본 영상 저작권 및 인물 초상권을 직접 확인하세요.
            </p>
          </div>

          {/* Download link */}
          {outputPath && (
            <a
              href={`/api/download?path=${encodeURIComponent(outputPath)}`}
              download
              className="block w-full py-2.5 rounded-lg font-bold text-sm text-center bg-blue-700 hover:bg-blue-600 active:bg-blue-800 transition"
            >
              ⬇️ MP4 다운로드
            </a>
          )}

          {/* Metadata section */}
          <div>
            <button
              onClick={handleLoadMeta}
              disabled={metaLoading}
              className="w-full py-2.5 rounded-lg text-sm font-medium bg-gray-700 hover:bg-gray-600 disabled:opacity-50 transition"
            >
              {metaLoading ? "⏳ 메타데이터 생성 중..." : "📋 제목 후보 / 해시태그 생성"}
            </button>
          </div>

          {metaResult && (
            <div className="rounded-lg p-4 bg-gray-800 border border-gray-700 space-y-4">
              <div>
                <p className="text-xs font-semibold text-gray-300 mb-2">제목 후보</p>
                <div className="space-y-2">
                  {metaResult.titleCandidates.map((title, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between gap-2 rounded p-2 bg-gray-700"
                    >
                      <p className="text-xs text-gray-200 flex-1">{title}</p>
                      <button
                        onClick={() => copyText(title, i)}
                        className="text-xs text-gray-400 hover:text-white shrink-0"
                      >
                        {copiedIdx === i ? "✅" : "복사"}
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <p className="text-xs font-semibold text-gray-300 mb-2">해시태그</p>
                <div className="flex flex-wrap gap-1">
                  {metaResult.hashtags.map((tag, i) => (
                    <span key={i} className="px-2 py-0.5 rounded-full bg-gray-700 text-xs text-blue-300">
                      {tag}
                    </span>
                  ))}
                </div>
                <button
                  onClick={() => copyText(metaResult.hashtags.join(" "), 100)}
                  className="mt-2 text-xs text-gray-400 hover:text-white"
                >
                  {copiedIdx === 100 ? "✅ 복사됨" : "해시태그 전체 복사"}
                </button>
              </div>

              {metaResult.pinnedComment && (
                <div>
                  <p className="text-xs font-semibold text-gray-300 mb-2">고정 댓글 초안</p>
                  <div className="rounded p-2 bg-gray-700">
                    <p className="text-xs text-gray-200 whitespace-pre-line">{metaResult.pinnedComment}</p>
                    <button
                      onClick={() => copyText(metaResult.pinnedComment, 200)}
                      className="mt-1 text-xs text-gray-400 hover:text-white"
                    >
                      {copiedIdx === 200 ? "✅ 복사됨" : "복사"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Selected moment info */}
          {selectedMoment && (
            <div className="rounded-lg p-3 bg-gray-800 border border-gray-700">
              <p className="text-xs font-semibold text-amber-300 mb-1">
                모먼트 [{selectedIdx}] — {KIND_LABEL[selectedMoment.kind] ?? selectedMoment.kind}
              </p>
              <p className="text-xs text-yellow-200">{selectedMoment.hook_question}</p>
              <p className="text-xs text-gray-400 mt-0.5">{selectedMoment.summary}</p>
              {selectedMoment.speaker && (
                <p className="text-xs text-blue-300 mt-0.5">👤 {selectedMoment.speaker}</p>
              )}
            </div>
          )}

          <button
            onClick={handleReset}
            className="w-full py-2 rounded-lg text-xs text-gray-400 bg-gray-800 hover:bg-gray-700 transition"
          >
            ↩ 처음으로 (새 영상)
          </button>
        </div>
      )}
    </div>
  );
}
