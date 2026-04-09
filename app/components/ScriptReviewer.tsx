"use client";
import { useState, useCallback } from "react";

interface SceneData {
  id: number;
  timestamp: number;
  duration: number;
  type: string;
  text: string;
  voice_text: string;
  emphasis: string;
}

interface ScenePrompt {
  scene_id: number;
  type: string;
  text: string;
  voice_text: string;
  image_prompt: string;
  motion_prompt: string;
}

interface Props {
  title: string;
  scenes: SceneData[];
  scriptPath: string;
  emotion: string;
  duration: number;
  imageStyle?: string;
  onTitleChange: (title: string) => void;
  onScenesChange: (scenes: SceneData[]) => void;
  onGenerate: () => void;
  onCancel: () => void;
  isSubmitting?: boolean;
}

const EMOTION_LABELS: Record<string, string> = {
  funny: "😂 재밌음",
  touching: "🥹 감동",
  angry: "😤 분노",
  relatable: "🤝 공감",
};

/**
 * ScriptReviewer — lightweight edit screen shown between Claude analysis
 * and the expensive image/video/render pipeline.
 *
 * Lets the user tweak the title, per-scene on-screen text, and per-scene
 * voice_text (TTS). Every save hits /api/scene/script which rewrites the
 * JSON file on disk — the backend then re-loads it in Phase 2.
 */
export function ScriptReviewer({
  title,
  scenes,
  scriptPath,
  emotion,
  duration,
  imageStyle = "realistic",
  onTitleChange,
  onScenesChange,
  onGenerate,
  onCancel,
  isSubmitting = false,
}: Props) {
  const [titleDraft, setTitleDraft] = useState(title);
  const [editingTitle, setEditingTitle] = useState(false);
  const [sceneDrafts, setSceneDrafts] = useState<Record<number, { text: string; voice_text: string }>>({});
  const [savingId, setSavingId] = useState<number | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [showPrompts, setShowPrompts] = useState(false);
  const [prompts, setPrompts] = useState<ScenePrompt[] | null>(null);
  const [promptsLoading, setPromptsLoading] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const copyToClipboard = useCallback(async (text: string, key: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 1500);
  }, []);

  const openPrompts = async () => {
    setShowPrompts(true);
    if (prompts) return; // already loaded
    setPromptsLoading(true);
    try {
      const res = await fetch("/api/prompts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scriptPath, imageStyle }),
      });
      if (!res.ok) throw new Error("프롬프트 생성 실패");
      const data = await res.json();
      setPrompts(data.prompts);
    } catch (e: any) {
      setErrorMsg(e.message || "프롬프트 생성 실패");
      setShowPrompts(false);
    } finally {
      setPromptsLoading(false);
    }
  };

  const getDraft = (scene: SceneData) =>
    sceneDrafts[scene.id] ?? { text: scene.text, voice_text: scene.voice_text };

  const updateDraft = (sceneId: number, key: "text" | "voice_text", value: string) => {
    const current = sceneDrafts[sceneId] ?? (() => {
      const s = scenes.find((x) => x.id === sceneId);
      return { text: s?.text || "", voice_text: s?.voice_text || "" };
    })();
    setSceneDrafts({ ...sceneDrafts, [sceneId]: { ...current, [key]: value } });
  };

  const saveTitle = async () => {
    const trimmed = titleDraft.trim();
    if (!trimmed || trimmed === title) {
      setEditingTitle(false);
      setTitleDraft(title);
      return;
    }
    try {
      const res = await fetch("/api/scene/script", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scriptPath, title: trimmed }),
      });
      if (!res.ok) throw new Error("제목 저장 실패");
      onTitleChange(trimmed);
      setEditingTitle(false);
    } catch (e: any) {
      setErrorMsg(e.message || "제목 저장 실패");
    }
  };

  const saveScene = async (sceneId: number) => {
    const draft = sceneDrafts[sceneId];
    if (!draft) return;
    setSavingId(sceneId);
    setErrorMsg("");
    try {
      const res = await fetch("/api/scene/script", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scriptPath,
          sceneId,
          text: draft.text,
          voiceText: draft.voice_text,
        }),
      });
      if (!res.ok) throw new Error("씬 저장 실패");
      const updated = scenes.map((s) =>
        s.id === sceneId ? { ...s, text: draft.text, voice_text: draft.voice_text } : s,
      );
      onScenesChange(updated);
      const { [sceneId]: _, ...rest } = sceneDrafts;
      setSceneDrafts(rest);
    } catch (e: any) {
      setErrorMsg(e.message || `씬 ${sceneId} 저장 실패`);
    } finally {
      setSavingId(null);
    }
  };

  // Save all pending drafts then trigger the Phase 2 pipeline.
  const handleGenerate = async () => {
    const pendingIds = Object.keys(sceneDrafts).map(Number);
    for (const id of pendingIds) {
      await saveScene(id);
    }
    if (editingTitle) await saveTitle();
    onGenerate();
  };

  const pendingCount = Object.keys(sceneDrafts).length + (editingTitle && titleDraft !== title ? 1 : 0);

  return (
    <main className="max-w-2xl mx-auto px-4 py-8">
      <header className="text-center mb-6">
        <div className="text-5xl mb-3">📝</div>
        <h2 className="text-2xl font-bold">스크립트 검토 및 수정</h2>
        <p className="text-gray-400 text-sm mt-1">
          AI가 생성한 스크립트를 원하는 대로 수정한 후 영상을 생성하세요
        </p>
      </header>

      {/* Metadata summary */}
      <div className="bg-gray-800 rounded-lg p-4 mb-4 text-sm">
        <div className="flex justify-between mb-2">
          <span className="text-gray-400">감정</span>
          <span>{EMOTION_LABELS[emotion] || emotion}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">예상 길이</span>
          <span>{duration}초 · {scenes.length}씬</span>
        </div>
      </div>

      {/* Title editor */}
      <div className="bg-gray-800 rounded-lg p-4 mb-4">
        <label className="text-xs text-gray-500 mb-2 block">📌 영상 제목</label>
        {editingTitle ? (
          <div className="flex gap-2">
            <input
              value={titleDraft}
              onChange={(e) => setTitleDraft(e.target.value)}
              className="flex-1 px-3 py-2 bg-gray-900 border border-gray-600 rounded focus:border-blue-500 focus:outline-none text-sm"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter") saveTitle();
                if (e.key === "Escape") {
                  setEditingTitle(false);
                  setTitleDraft(title);
                }
              }}
            />
            <button
              onClick={saveTitle}
              className="px-3 py-2 bg-blue-600 hover:bg-blue-500 rounded text-xs font-medium"
            >
              저장
            </button>
            <button
              onClick={() => {
                setEditingTitle(false);
                setTitleDraft(title);
              }}
              className="px-3 py-2 bg-gray-600 hover:bg-gray-500 rounded text-xs font-medium"
            >
              취소
            </button>
          </div>
        ) : (
          <div
            onClick={() => {
              setEditingTitle(true);
              setTitleDraft(title);
            }}
            className="text-base font-medium cursor-pointer hover:bg-gray-700/50 rounded px-2 py-2 transition"
            title="클릭하여 수정"
          >
            {title} <span className="text-gray-500 text-xs ml-2">✏️ 수정</span>
          </div>
        )}
      </div>

      {/* Scene list */}
      <div className="space-y-3 mb-4">
        {scenes.map((scene) => {
          const draft = getDraft(scene);
          const isDirty =
            draft.text !== scene.text || draft.voice_text !== scene.voice_text;
          return (
            <div
              key={scene.id}
              className={`bg-gray-800 rounded-lg p-4 border-2 transition ${
                isDirty ? "border-yellow-500" : "border-transparent"
              }`}
            >
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs text-gray-500">
                  씬 {scene.id} · {scene.type} · {scene.duration.toFixed(1)}초
                </span>
                {isDirty && (
                  <button
                    onClick={() => saveScene(scene.id)}
                    disabled={savingId === scene.id}
                    className="px-2 py-1 bg-yellow-600 hover:bg-yellow-500 rounded text-xs font-medium disabled:opacity-50"
                  >
                    {savingId === scene.id ? "저장 중..." : "💾 저장"}
                  </button>
                )}
              </div>
              <label className="text-xs text-gray-400 block mb-1">
                🖼️ 화면에 표시할 글
              </label>
              <textarea
                value={draft.text}
                onChange={(e) => updateDraft(scene.id, "text", e.target.value)}
                rows={2}
                className="w-full px-3 py-2 mb-2 bg-gray-900 border border-gray-700 rounded focus:border-blue-500 focus:outline-none text-sm resize-y"
              />
              <label className="text-xs text-gray-400 block mb-1">
                🎙️ TTS 음성 대본
              </label>
              <textarea
                value={draft.voice_text}
                onChange={(e) => updateDraft(scene.id, "voice_text", e.target.value)}
                rows={2}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded focus:border-blue-500 focus:outline-none text-sm resize-y"
              />
            </div>
          );
        })}
      </div>

      {errorMsg && (
        <div className="mb-4 p-3 bg-red-900/50 border border-red-500 rounded-lg text-red-200 text-sm">
          {errorMsg}
        </div>
      )}

      {/* Action bar */}
      <div className="flex gap-3 sticky bottom-4">
        <button
          onClick={onCancel}
          disabled={isSubmitting}
          className="py-3 px-5 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium transition disabled:opacity-50"
        >
          ← 취소
        </button>
        <button
          onClick={openPrompts}
          disabled={isSubmitting}
          className="py-3 px-4 bg-purple-700 hover:bg-purple-600 rounded-lg font-medium transition disabled:opacity-50 whitespace-nowrap"
        >
          📋 프롬프트
        </button>
        <button
          onClick={handleGenerate}
          disabled={isSubmitting}
          className="flex-1 py-3 bg-blue-600 hover:bg-blue-500 rounded-lg font-medium transition disabled:opacity-50"
        >
          {isSubmitting
            ? "영상 생성 중..."
            : pendingCount > 0
              ? `💾 ${pendingCount}건 저장 후 🎬 영상 생성`
              : "🎬 영상 생성"}
        </button>
      </div>

      {/* Prompt export modal */}
      {showPrompts && (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 overflow-y-auto py-8 px-4">
          <div className="bg-gray-900 rounded-xl w-full max-w-2xl border border-gray-700 shadow-2xl">
            <div className="flex justify-between items-center px-5 py-4 border-b border-gray-700">
              <div>
                <h3 className="text-lg font-bold">📋 Freepik 프롬프트</h3>
                <p className="text-xs text-gray-400 mt-0.5">각 씬의 프롬프트를 복사해서 Freepik에 직접 입력하세요</p>
              </div>
              <button
                onClick={() => setShowPrompts(false)}
                className="text-gray-400 hover:text-white text-xl leading-none px-2"
              >
                ✕
              </button>
            </div>

            <div className="p-5 space-y-5">
              {promptsLoading && (
                <div className="text-center py-10 text-gray-400">
                  <div className="text-3xl mb-2">⏳</div>
                  프롬프트 생성 중...
                </div>
              )}

              {prompts && prompts.map((p) => (
                <div key={p.scene_id} className="bg-gray-800 rounded-lg p-4 space-y-3">
                  <div className="flex items-center gap-2 text-xs text-gray-400 mb-1">
                    <span className="bg-gray-700 px-2 py-0.5 rounded font-mono">씬 {p.scene_id}</span>
                    <span>{p.type}</span>
                    <span className="truncate text-gray-500">{p.text}</span>
                  </div>

                  {/* Image prompt */}
                  <div>
                    <div className="flex justify-between items-center mb-1">
                      <label className="text-xs font-semibold text-purple-400">🖼️ 이미지 프롬프트 (Freepik Image Generator)</label>
                      <button
                        onClick={() => copyToClipboard(p.image_prompt, `img-${p.scene_id}`)}
                        className="text-xs px-2 py-1 bg-purple-800 hover:bg-purple-700 rounded transition"
                      >
                        {copiedKey === `img-${p.scene_id}` ? "✅ 복사됨" : "복사"}
                      </button>
                    </div>
                    <div className="text-xs bg-gray-900 rounded p-3 text-gray-300 font-mono whitespace-pre-wrap break-all leading-relaxed max-h-32 overflow-y-auto">
                      {p.image_prompt}
                    </div>
                  </div>

                  {/* Motion prompt */}
                  <div>
                    <div className="flex justify-between items-center mb-1">
                      <label className="text-xs font-semibold text-blue-400">🎬 영상 프롬프트 (Freepik Video Generator)</label>
                      <button
                        onClick={() => copyToClipboard(p.motion_prompt, `vid-${p.scene_id}`)}
                        className="text-xs px-2 py-1 bg-blue-800 hover:bg-blue-700 rounded transition"
                      >
                        {copiedKey === `vid-${p.scene_id}` ? "✅ 복사됨" : "복사"}
                      </button>
                    </div>
                    <div className="text-xs bg-gray-900 rounded p-3 text-gray-300 font-mono whitespace-pre-wrap break-all leading-relaxed max-h-32 overflow-y-auto">
                      {p.motion_prompt}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {prompts && (
              <div className="px-5 pb-5">
                <button
                  onClick={async () => {
                    const all = prompts.map((p) =>
                      `=== 씬 ${p.scene_id} (${p.type}) ===\n[씬 내용]\n${p.text}\n\n[이미지 프롬프트]\n${p.image_prompt}\n\n[영상 프롬프트]\n${p.motion_prompt}`
                    ).join("\n\n" + "─".repeat(60) + "\n\n");
                    await copyToClipboard(all, "all");
                  }}
                  className="w-full py-2.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm font-medium transition"
                >
                  {copiedKey === "all" ? "✅ 전체 복사됨" : "📋 전체 복사"}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
