"use client";
import { useState, useRef } from "react";
import { SceneCard } from "./SceneCard";
import { ImageReplaceModal } from "./ImageReplaceModal";
import { Timeline } from "./Timeline";
import { SubtitleStyleEditor, type SubtitleStyle } from "./SubtitleStyleEditor";
import { TransitionPicker } from "./TransitionPicker";
import { VoicePicker } from "./VoicePicker";
import { VideoPreview } from "./VideoPreview";

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

type ViewMode = "card" | "timeline";

interface SceneVideo {
  scene_id: number;
  video_path: string;
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
  sceneImages: SceneImage[];
  scriptPath: string;
  useBgm: boolean;
  emotionType?: string;
  audioPath?: string;
  imageStyle?: string;
  sceneVideos?: SceneVideo[];
  onTitleChange: (title: string) => void;
  onScenesChange: (scenes: SceneData[]) => void;
  onImagesChange: (images: SceneImage[]) => void;
  onVideoUpdate: (videoPath: string) => void;
  onVideosChange?: (videos: SceneVideo[]) => void;
}

export function SceneEditor({
  title,
  scenes,
  sceneImages,
  scriptPath,
  useBgm,
  emotionType = "relatable",
  audioPath,
  imageStyle = "realistic",
  sceneVideos,
  onTitleChange,
  onScenesChange,
  onImagesChange,
  onVideoUpdate,
  onVideosChange,
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
  const [viewMode, setViewMode] = useState<ViewMode>("card");
  const [styleSceneId, setStyleSceneId] = useState<number | null>(null);
  const [transitionSceneId, setTransitionSceneId] = useState<number | null>(null);
  const [showVoicePicker, setShowVoicePicker] = useState(false);
  const [currentVoice, setCurrentVoice] = useState("ko-KR-SunHiNeural");
  const [showPreview, setShowPreview] = useState(false);
  const [translating, setTranslating] = useState(false);
  const [targetLang, setTargetLang] = useState<"en" | "ja" | null>(null);
  const [showPrompts, setShowPrompts] = useState(false);
  const [prompts, setPrompts] = useState<ScenePrompt[] | null>(null);
  const [promptsLoading, setPromptsLoading] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const imageMap = new Map(sceneImages.map((img) => [img.scene_id, img]));
  const videoMap = new Map((sceneVideos || []).map((v) => [v.scene_id, v]));
  const isVideoMode = sceneVideos !== undefined;

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
      {
        scene_id: data.sceneId ?? data.scene_id,
        image_path: data.imagePath ?? data.image_path,
        prompt: data.prompt,
      },
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
      {
        scene_id: data.sceneId ?? data.scene_id,
        image_path: data.imagePath ?? data.image_path,
        prompt: data.prompt ?? "(uploaded)",
      },
    ]);
    setHasChanges(true);
  };

  const copyToClipboard = async (text: string, key: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 1500);
  };

  const openPrompts = async () => {
    setShowPrompts(true);
    if (prompts) return;
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
    } catch {
      setShowPrompts(false);
    } finally {
      setPromptsLoading(false);
    }
  };

  const handleVideoUpload = async (sceneId: number, file: File) => {
    const fd = new FormData();
    fd.set("sceneId", String(sceneId));
    fd.set("file", file);
    const res = await fetch("/api/scene/video", { method: "POST", body: fd });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || "업로드 실패");
    }
    const data = await res.json();
    const updated = (sceneVideos || []).filter((v) => v.scene_id !== sceneId);
    onVideosChange?.([...updated, { scene_id: data.scene_id, video_path: data.video_path }]);
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
        setRegenProgress(
          `${done}/${ids.length} (씬 ${sceneId} 프롬프트 없음 — 스킵)`
        );
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
    voiceText: string
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

  const handleSplit = async (sceneId: number) => {
    const scene = scenes.find((s) => s.id === sceneId);
    if (!scene) return;
    const text = scene.text.replace(/\\n/g, "\n");
    const mid = Math.floor(text.length / 2);

    try {
      const res = await fetch("/api/scene/split", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scene_id: sceneId,
          split_position: mid,
          script_path: scriptPath,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        console.error("Split failed:", err.error);
        return;
      }
      const data = await res.json();
      if (data.scenes) {
        onScenesChange(data.scenes);
        setHasChanges(true);
      }
    } catch (e) {
      console.error("Split error:", e);
    }
  };

  const handleMerge = async (sceneId: number) => {
    const idx = scenes.findIndex((s) => s.id === sceneId);
    if (idx === -1 || idx >= scenes.length - 1) return;
    const nextScene = scenes[idx + 1];

    try {
      const res = await fetch("/api/scene/merge", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scene_id_1: sceneId,
          scene_id_2: nextScene.id,
          script_path: scriptPath,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        console.error("Merge failed:", err.error);
        return;
      }
      const data = await res.json();
      if (data.scenes) {
        onScenesChange(data.scenes);
        setHasChanges(true);
      }
    } catch (e) {
      console.error("Merge error:", e);
    }
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
          sceneVideos: (sceneVideos || []).map((v) => ({
            scene_id: v.scene_id,
            video_path: v.video_path,
          })),
          useBgm,
        }),
      });

      const reader = res.body?.getReader();
      if (!reader) throw new Error("스트림 열기 실패");

      const dec = new TextDecoder();
      // Buffer partial lines across TCP chunk boundaries (SSE parser fix).
      let buf = "";
      const processLine = (line: string) => {
        if (!line.startsWith("data: ")) return;
        let d: any;
        try { d = JSON.parse(line.slice(6)); }
        catch { return; }
        if (d.type === "progress") setRenderProgress(d.message);
        else if (d.type === "done") {
          onVideoUpdate(d.result.videoPath);
          setHasChanges(false);
        } else if (d.type === "error") throw new Error(d.message);
      };
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          if (buf.trim()) processLine(buf);
          break;
        }
        buf += dec.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";
        for (const line of lines) processLine(line);
      }
    } catch (e: any) {
      setRenderProgress(`오류: ${e.message}`);
    } finally {
      setRendering(false);
    }
  };

  const handleStyleClick = (sceneId: number) => {
    setStyleSceneId(sceneId);
  };

  const handleStyleChange = (newStyle: SubtitleStyle) => {
    setHasChanges(true);
  };

  const modalImage =
    modalSceneId !== null ? imageMap.get(modalSceneId) : null;

  const DEFAULT_SUBTITLE_STYLE: SubtitleStyle = {
    font_family: "Noto Sans KR",
    font_size: 55,
    font_weight: "bold",
    color: "#FFFFFF",
    shadow: "3px 3px 8px rgba(0,0,0,0.7)",
    position_y: 0.6,
    bg_color: null,
    bg_opacity: 0.0,
  };

  return (
    <div className="space-y-3">
      {/* Title edit */}
      <div className="bg-gray-800 rounded-lg p-3">
        <label className="text-xs text-gray-500 mb-1 block">영상 제목</label>
        {editingTitle ? (
          <div className="flex gap-2 items-start">
            <textarea
              value={titleDraft}
              onChange={(e) => setTitleDraft(e.target.value)}
              className="flex-1 px-2 py-1 bg-gray-900 border border-gray-600 rounded text-sm focus:border-blue-500 focus:outline-none resize-y min-h-[2.5rem] whitespace-pre-wrap"
              autoFocus
              rows={2}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault();
                  handleTitleSave();
                }
                if (e.key === "Escape") {
                  setEditingTitle(false);
                  setTitleDraft(title);
                }
              }}
            />
            <div className="flex flex-col gap-1">
              <button
                onClick={handleTitleSave}
                className="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-xs font-medium"
                title="Cmd/Ctrl + Enter"
              >
                저장
              </button>
              <button
                onClick={() => {
                  setEditingTitle(false);
                  setTitleDraft(title);
                }}
                className="px-3 py-1 bg-gray-600 hover:bg-gray-500 rounded text-xs font-medium"
              >
                취소
              </button>
            </div>
          </div>
        ) : (
          <div
            onClick={() => {
              setEditingTitle(true);
              setTitleDraft(title);
            }}
            className="text-sm font-medium cursor-pointer hover:bg-gray-700/50 rounded px-1 -mx-1 py-0.5 transition whitespace-pre-wrap"
            title="클릭하여 제목 수정"
          >
            {title}
          </div>
        )}
      </div>

      {/* Preview toggle + panel */}
      <div className="flex gap-2">
        <button
          onClick={() => setShowPreview(!showPreview)}
          className={`flex-1 py-2 rounded-lg text-sm font-medium transition ${
            showPreview ? "bg-indigo-600 hover:bg-indigo-500" : "bg-gray-800 hover:bg-gray-700 text-gray-400"
          }`}
        >
          {showPreview ? "▼ 미리보기 숨기기" : "▶ 미리보기"}
        </button>
        <button
          onClick={openPrompts}
          className="py-2 px-4 rounded-lg text-sm font-medium transition bg-purple-700 hover:bg-purple-600"
        >
          📋 프롬프트
        </button>
        <button
          onClick={handleRerender}
          disabled={rendering || !hasChanges}
          className={`py-2 px-4 rounded-lg text-sm font-medium transition ${
            hasChanges && !rendering
              ? "bg-orange-600 hover:bg-orange-500"
              : "bg-gray-800 text-gray-500 cursor-not-allowed"
          }`}
        >
          {rendering ? renderProgress : "최종 렌더링"}
        </button>
      </div>

      {showPreview && (
        <VideoPreview
          title={title}
          emotionType={emotionType}
          scenes={scenes}
          sceneImages={sceneImages}
          audioPath={audioPath}
        />
      )}

      {/* Scene list header with view toggle */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium text-gray-400">씬 편집</h3>
          {viewMode === "card" && (
            <button
              onClick={handleSelectAll}
              className="text-xs text-blue-400 hover:text-blue-300"
            >
              {selectedScenes.size === scenes.length
                ? "전체 해제"
                : "전체 선택"}
            </button>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">
            {viewMode === "card"
              ? "더블클릭: 대본 편집 | 이미지 클릭: 교체"
              : "드래그: 순서 변경 | 우측 핸들: 길이 조절"}
          </span>
          <button
            onClick={() => setShowVoicePicker(true)}
            className="px-2 py-1 text-xs bg-gray-800 hover:bg-gray-700 rounded-md text-gray-400 hover:text-white transition"
          >
            🎙 음성
          </button>
          <div className="flex bg-gray-800 rounded-md overflow-hidden">
            <button
              onClick={async () => {
                if (translating) return;
                setTranslating(true);
                try {
                  const res = await fetch("/api/translate", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      scenes: scenes.map((s) => ({ id: s.id, text: s.text })),
                      target_language: "en",
                    }),
                  });
                  if (res.ok) {
                    const data = await res.json();
                    setTargetLang("en");
                    setHasChanges(true);
                  }
                } catch {}
                setTranslating(false);
              }}
              disabled={translating}
              className={`px-2 py-1 text-xs transition ${
                targetLang === "en" ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
              }`}
            >
              {translating ? "..." : "EN"}
            </button>
            <button
              onClick={async () => {
                if (translating) return;
                setTranslating(true);
                try {
                  const res = await fetch("/api/translate", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      scenes: scenes.map((s) => ({ id: s.id, text: s.text })),
                      target_language: "ja",
                    }),
                  });
                  if (res.ok) {
                    setTargetLang("ja");
                    setHasChanges(true);
                  }
                } catch {}
                setTranslating(false);
              }}
              disabled={translating}
              className={`px-2 py-1 text-xs transition ${
                targetLang === "ja" ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
              }`}
            >
              {translating ? "..." : "JP"}
            </button>
          </div>
          <div className="flex bg-gray-800 rounded-md overflow-hidden">
            <button
              onClick={() => setViewMode("card")}
              className={`px-2 py-1 text-xs transition ${viewMode === "card" ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"}`}
            >
              카드
            </button>
            <button
              onClick={() => setViewMode("timeline")}
              className={`px-2 py-1 text-xs transition ${viewMode === "timeline" ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"}`}
            >
              타임라인
            </button>
          </div>
        </div>
      </div>

      {/* View: Card or Timeline */}
      {viewMode === "card" ? (
        <div className="space-y-2">
          {scenes.map((scene, idx) => (
            <div key={scene.id}>
              <SceneCard
                scene={scene}
                image={imageMap.get(scene.id)}
                selected={selectedScenes.has(scene.id)}
                isLast={idx === scenes.length - 1}
                onSelect={handleSelect}
                onImageClick={handleImageClick}
                onTextSave={handleTextSave}
                onSplit={handleSplit}
                onMerge={handleMerge}
                onStyleClick={handleStyleClick}
                onTransitionClick={(id) => setTransitionSceneId(id)}
              />
              {isVideoMode && (
                <VideoSceneStatus
                  sceneId={scene.id}
                  hasVideo={videoMap.has(scene.id)}
                  onUpload={handleVideoUpload}
                />
              )}
            </div>
          ))}
        </div>
      ) : (
        <Timeline
          scenes={scenes}
          scriptPath={scriptPath}
          onScenesChange={(newScenes) => {
            onScenesChange(newScenes);
            setHasChanges(true);
          }}
          onSplit={handleSplit}
          onMerge={handleMerge}
        />
      )}

      {/* Batch regenerate button */}
      {selectedScenes.size > 0 && viewMode === "card" && (
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

      {modalSceneId !== null && (
        <ImageReplaceModal
          sceneId={modalSceneId}
          currentPrompt={modalImage?.prompt || ""}
          onClose={() => setModalSceneId(null)}
          onRegenerate={handleRegenerate}
          onUpload={handleUpload}
        />
      )}

      {styleSceneId !== null && (
        <SubtitleStyleEditor
          style={DEFAULT_SUBTITLE_STYLE}
          sceneId={styleSceneId}
          scriptPath={scriptPath}
          onStyleChange={handleStyleChange}
          onClose={() => setStyleSceneId(null)}
        />
      )}

      {transitionSceneId !== null && (
        <TransitionPicker
          transition={{ type: "fade", duration: 0.5 }}
          sceneId={transitionSceneId}
          scriptPath={scriptPath}
          onTransitionChange={() => setHasChanges(true)}
          onClose={() => setTransitionSceneId(null)}
        />
      )}

      {showVoicePicker && (
        <VoicePicker
          currentVoice={currentVoice}
          scriptPath={scriptPath}
          onVoiceChange={(voice) => {
            setCurrentVoice(voice);
            setHasChanges(true);
          }}
          onClose={() => setShowVoicePicker(false)}
        />
      )}

      {/* Freepik 프롬프트 모달 */}
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
                  <div>
                    <div className="flex justify-between items-center mb-1">
                      <label className="text-xs font-semibold text-purple-400">🖼️ 이미지 프롬프트</label>
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
                  <div>
                    <div className="flex justify-between items-center mb-1">
                      <label className="text-xs font-semibold text-blue-400">🎬 영상 프롬프트</label>
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
    </div>
  );
}

// ── VideoSceneStatus ──────────────────────────────────────────────────────────
// Shown below each SceneCard when the pipeline is in video mode.
// Green badge if the scene has a video; orange badge + upload button if missing.

function VideoSceneStatus({
  sceneId,
  hasVideo,
  onUpload,
}: {
  sceneId: number;
  hasVideo: boolean;
  onUpload: (sceneId: number, file: File) => Promise<void>;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  if (hasVideo) {
    return (
      <div className="flex items-center gap-1.5 px-3 py-1 text-xs text-green-400 bg-green-900/20 border border-green-800/40 rounded-b-lg -mt-0.5">
        <span>✅</span>
        <span>씬 {sceneId} 영상 있음</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-orange-900/20 border border-orange-700/40 rounded-b-lg -mt-0.5">
      <span className="text-xs text-orange-400 flex-1">⚠️ 씬 {sceneId} 영상 없음</span>
      {error && <span className="text-xs text-red-400">{error}</span>}
      <button
        onClick={() => inputRef.current?.click()}
        disabled={uploading}
        className="text-xs px-2 py-1 bg-orange-700 hover:bg-orange-600 rounded transition disabled:opacity-50"
      >
        {uploading ? "업로드 중..." : "📁 영상 업로드"}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="video/*,.mp4,.webm,.mov"
        className="hidden"
        onChange={async (e) => {
          const file = e.target.files?.[0];
          if (!file) return;
          setUploading(true);
          setError("");
          try {
            await onUpload(sceneId, file);
          } catch (err: any) {
            setError(err.message || "업로드 실패");
          } finally {
            setUploading(false);
            e.target.value = "";
          }
        }}
      />
    </div>
  );
}
