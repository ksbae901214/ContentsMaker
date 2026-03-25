"use client";
import { useState } from "react";
import { SceneCard } from "./SceneCard";
import { ImageReplaceModal } from "./ImageReplaceModal";

interface SceneImage {
  scene_id: number;
  image_path: string;
  prompt: string;
}

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
  sceneImages: SceneImage[];
  scriptPath: string;
  useBgm: boolean;
  onTitleChange: (title: string) => void;
  onScenesChange: (scenes: SceneData[]) => void;
  onImagesChange: (images: SceneImage[]) => void;
  onVideoUpdate: (videoPath: string) => void;
}

export function SceneEditor({
  title,
  scenes,
  sceneImages,
  scriptPath,
  useBgm,
  onTitleChange,
  onScenesChange,
  onImagesChange,
  onVideoUpdate,
}: Props) {
  const [modalSceneId, setModalSceneId] = useState<number | null>(null);
  const [rendering, setRendering] = useState(false);
  const [renderProgress, setRenderProgress] = useState("");
  const [hasChanges, setHasChanges] = useState(false);
  const [selectedScenes, setSelectedScenes] = useState<Set<number>>(new Set());
  const [regenerating, setRegenerating] = useState(false);
  const [regenProgress, setRegenProgress] = useState("");
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState(title);

  const imageMap = new Map(sceneImages.map((img) => [img.scene_id, img]));

  const handleSelect = (sceneId: number, checked: boolean) => {
    const next = new Set(selectedScenes);
    if (checked) next.add(sceneId);
    else next.delete(sceneId);
    setSelectedScenes(next);
  };

  const handleSelectAll = () => {
    if (selectedScenes.size === scenes.length) {
      setSelectedScenes(new Set());
    } else {
      setSelectedScenes(new Set(scenes.map((s) => s.id)));
    }
  };

  const handleImageClick = (sceneId: number) => {
    setModalSceneId(sceneId);
  };

  const handleRegenerate = async (sceneId: number, prompt: string) => {
    const res = await fetch("/api/scene/image", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sceneId, prompt, mode: "regenerate" }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || "이미지 생성 실패");
    }
    const data = await res.json();
    const updated = sceneImages.filter((img) => img.scene_id !== sceneId);
    onImagesChange([
      ...updated,
      { scene_id: data.sceneId ?? data.scene_id, image_path: data.imagePath ?? data.image_path, prompt: data.prompt },
    ]);
    setHasChanges(true);
  };

  const handleUpload = async (sceneId: number, file: File) => {
    const fd = new FormData();
    fd.set("sceneId", String(sceneId));
    fd.set("file", file);
    const res = await fetch("/api/scene/image", { method: "POST", body: fd });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || "업로드 실패");
    }
    const data = await res.json();
    const updated = sceneImages.filter((img) => img.scene_id !== sceneId);
    onImagesChange([
      ...updated,
      { scene_id: data.sceneId ?? data.scene_id, image_path: data.imagePath ?? data.image_path, prompt: data.prompt ?? "(uploaded)" },
    ]);
    setHasChanges(true);
  };

  const handleBatchRegenerate = async () => {
    if (selectedScenes.size === 0) return;
    setRegenerating(true);
    const ids = Array.from(selectedScenes).sort();
    let done = 0;

    for (const sceneId of ids) {
      const existing = imageMap.get(sceneId);
      const prompt = existing?.prompt || "";
      if (!prompt || prompt === "(uploaded)") {
        done++;
        setRegenProgress(`${done}/${ids.length} (씬 ${sceneId} 프롬프트 없음 — 스킵)`);
        continue;
      }
      setRegenProgress(`${done}/${ids.length} 씬 ${sceneId} 생성 중...`);
      try {
        await handleRegenerate(sceneId, prompt);
      } catch {
        // continue with next
      }
      done++;
    }
    setRegenProgress("");
    setRegenerating(false);
    setSelectedScenes(new Set());
  };

  const handleTextSave = async (
    sceneId: number,
    text: string,
    voiceText: string,
  ) => {
    const res = await fetch("/api/scene/script", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scriptPath, sceneId, text, voiceText }),
    });
    if (!res.ok) return;

    const updatedScenes = scenes.map((s) => {
      if (s.id !== sceneId) return s;
      return { ...s, text, voice_text: voiceText };
    });
    onScenesChange(updatedScenes);
    setHasChanges(true);
  };

  const handleTitleSave = async () => {
    const trimmed = titleDraft.trim();
    if (!trimmed || trimmed === title) {
      setEditingTitle(false);
      setTitleDraft(title);
      return;
    }
    const res = await fetch("/api/scene/script", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scriptPath, title: trimmed }),
    });
    if (res.ok) {
      onTitleChange(trimmed);
      setHasChanges(true);
    }
    setEditingTitle(false);
  };

  const handleRerender = async () => {
    setRendering(true);
    setRenderProgress("준비 중...");

    try {
      const res = await fetch("/api/rerender", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scriptPath,
          sceneImages: sceneImages.map((img) => ({
            scene_id: img.scene_id,
            image_path: img.image_path,
          })),
          useBgm,
        }),
      });

      const reader = res.body?.getReader();
      if (!reader) throw new Error("스트림 열기 실패");

      const dec = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        for (const line of dec
          .decode(value)
          .split("\n")
          .filter((l) => l.startsWith("data: "))) {
          try {
            const d = JSON.parse(line.slice(6));
            if (d.type === "progress") setRenderProgress(d.message);
            else if (d.type === "done") {
              onVideoUpdate(d.result.videoPath);
              setHasChanges(false);
            } else if (d.type === "error") throw new Error(d.message);
          } catch (e: any) {
            if (!e.message?.includes("JSON")) throw e;
          }
        }
      }
    } catch (e: any) {
      setRenderProgress(`오류: ${e.message}`);
    } finally {
      setRendering(false);
    }
  };

  const modalImage = modalSceneId !== null ? imageMap.get(modalSceneId) : null;

  return (
    <div className="space-y-3">
      {/* Title edit */}
      <div className="bg-gray-800 rounded-lg p-3">
        <label className="text-xs text-gray-500 mb-1 block">영상 제목</label>
        {editingTitle ? (
          <div className="flex gap-2">
            <input
              value={titleDraft}
              onChange={(e) => setTitleDraft(e.target.value)}
              className="flex-1 px-2 py-1 bg-gray-900 border border-gray-600 rounded text-sm focus:border-blue-500 focus:outline-none"
              autoFocus
              onKeyDown={(e) => { if (e.key === "Enter") handleTitleSave(); if (e.key === "Escape") { setEditingTitle(false); setTitleDraft(title); } }}
            />
            <button onClick={handleTitleSave} className="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-xs font-medium">저장</button>
            <button onClick={() => { setEditingTitle(false); setTitleDraft(title); }} className="px-3 py-1 bg-gray-600 hover:bg-gray-500 rounded text-xs font-medium">취소</button>
          </div>
        ) : (
          <div
            onClick={() => { setEditingTitle(true); setTitleDraft(title); }}
            className="text-sm font-medium cursor-pointer hover:bg-gray-700/50 rounded px-1 -mx-1 py-0.5 transition"
            title="클릭하여 제목 수정"
          >
            {title}
          </div>
        )}
      </div>

      {/* Scene list header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium text-gray-400">씬 편집</h3>
          <button
            onClick={handleSelectAll}
            className="text-xs text-blue-400 hover:text-blue-300"
          >
            {selectedScenes.size === scenes.length ? "전체 해제" : "전체 선택"}
          </button>
        </div>
        <span className="text-xs text-gray-500">
          더블클릭: 대본 편집 | 이미지 클릭: 교체
        </span>
      </div>

      <div className="space-y-2">
        {scenes.map((scene) => (
          <SceneCard
            key={scene.id}
            scene={scene}
            image={imageMap.get(scene.id)}
            selected={selectedScenes.has(scene.id)}
            onSelect={handleSelect}
            onImageClick={handleImageClick}
            onTextSave={handleTextSave}
          />
        ))}
      </div>

      {/* Batch regenerate button */}
      {selectedScenes.size > 0 && (
        <button
          onClick={handleBatchRegenerate}
          disabled={regenerating}
          className="w-full py-2.5 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 disabled:text-gray-500 rounded-lg text-sm font-medium transition"
        >
          {regenerating
            ? regenProgress
            : `선택한 ${selectedScenes.size}개 씬 이미지 재생성`}
        </button>
      )}

      <button
        onClick={handleRerender}
        disabled={rendering || !hasChanges}
        className={`w-full py-3 rounded-lg font-medium transition ${
          hasChanges && !rendering
            ? "bg-orange-600 hover:bg-orange-500"
            : "bg-gray-700 text-gray-500 cursor-not-allowed"
        }`}
      >
        {rendering
          ? renderProgress
          : hasChanges
            ? "영상 재렌더링"
            : "변경사항 없음"}
      </button>

      {modalSceneId !== null && (
        <ImageReplaceModal
          sceneId={modalSceneId}
          currentPrompt={modalImage?.prompt || ""}
          onClose={() => setModalSceneId(null)}
          onRegenerate={handleRegenerate}
          onUpload={handleUpload}
        />
      )}
    </div>
  );
}
