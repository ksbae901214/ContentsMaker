"use client";
import { useState } from "react";

interface SceneData {
  id: number;
  timestamp: number;
  duration: number;
  type: string;
  text: string;
  voice_text: string;
  emphasis: string;
}

interface Props {
  title: string;
  scenes: SceneData[];
  scriptPath: string;
  emotion: string;
  duration: number;
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
    </main>
  );
}
