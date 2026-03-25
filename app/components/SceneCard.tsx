"use client";
import { useState, useRef, useEffect } from "react";

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
  scene: SceneData;
  image: SceneImage | undefined;
  onImageClick: (sceneId: number) => void;
  onTextSave: (sceneId: number, text: string, voiceText: string) => void;
}

export function SceneCard({ scene, image, onImageClick, onTextSave }: Props) {
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(scene.text);
  const [editVoice, setEditVoice] = useState(scene.voice_text);
  const textRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setEditText(scene.text);
    setEditVoice(scene.voice_text);
  }, [scene.text, scene.voice_text]);

  const handleSave = () => {
    onTextSave(scene.id, editText, editVoice);
    setEditing(false);
  };

  const handleCancel = () => {
    setEditText(scene.text);
    setEditVoice(scene.voice_text);
    setEditing(false);
  };

  const typeLabel =
    scene.type === "title"
      ? "제목"
      : scene.type === "comment"
        ? "댓글"
        : "본문";
  const typeBg =
    scene.type === "title"
      ? "bg-yellow-600"
      : scene.type === "comment"
        ? "bg-purple-600"
        : "bg-blue-600";

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden">
      <div className="flex gap-3 p-3">
        {/* Image thumbnail */}
        <div
          className="w-20 h-28 flex-shrink-0 rounded-md overflow-hidden cursor-pointer bg-gray-700 flex items-center justify-center hover:ring-2 hover:ring-blue-500 transition"
          onClick={() => onImageClick(scene.id)}
        >
          {image ? (
            <img
              src={`/api/download?path=${encodeURIComponent(image.image_path)}`}
              alt={`씬 ${scene.id}`}
              className="w-full h-full object-cover"
            />
          ) : (
            <span className="text-2xl text-gray-500">+</span>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span
              className={`text-xs px-1.5 py-0.5 rounded ${typeBg} text-white`}
            >
              {typeLabel}
            </span>
            <span className="text-xs text-gray-500">
              씬 {scene.id} | {scene.timestamp.toFixed(1)}s
            </span>
          </div>

          {editing ? (
            <div className="space-y-2">
              <div>
                <label className="text-xs text-gray-400">표시 텍스트</label>
                <textarea
                  ref={textRef}
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  rows={2}
                  className="w-full px-2 py-1 bg-gray-900 border border-gray-600 rounded text-sm focus:border-blue-500 focus:outline-none resize-y"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400">음성 텍스트</label>
                <textarea
                  value={editVoice}
                  onChange={(e) => setEditVoice(e.target.value)}
                  rows={2}
                  className="w-full px-2 py-1 bg-gray-900 border border-gray-600 rounded text-sm focus:border-blue-500 focus:outline-none resize-y"
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleSave}
                  className="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-xs font-medium transition"
                >
                  저장
                </button>
                <button
                  onClick={handleCancel}
                  className="px-3 py-1 bg-gray-600 hover:bg-gray-500 rounded text-xs font-medium transition"
                >
                  취소
                </button>
              </div>
            </div>
          ) : (
            <div
              onDoubleClick={() => setEditing(true)}
              className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed cursor-text hover:bg-gray-700/50 rounded px-1 -mx-1 transition"
              title="더블클릭으로 편집"
            >
              {scene.text}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
