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
  scenes: SceneData[];
  sceneImages: SceneImage[];
  scriptPath: string;
  useBgm: boolean;
  onScenesChange: (scenes: SceneData[]) => void;
  onImagesChange: (images: SceneImage[]) => void;
  onVideoUpdate: (videoPath: string) => void;
}

export function SceneEditor({
  scenes,
  sceneImages,
  scriptPath,
  useBgm,
  onScenesChange,
  onImagesChange,
  onVideoUpdate,
}: Props) {
  const [modalSceneId, setModalSceneId] = useState<number | null>(null);
  const [rendering, setRendering] = useState(false);
  const [renderProgress, setRenderProgress] = useState("");
  const [hasChanges, setHasChanges] = useState(false);

  const imageMap = new Map(sceneImages.map((img) => [img.scene_id, img]));

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
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-400">씬 편집</h3>
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
            onImageClick={handleImageClick}
            onTextSave={handleTextSave}
          />
        ))}
      </div>

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
