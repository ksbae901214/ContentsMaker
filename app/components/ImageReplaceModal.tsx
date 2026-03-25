"use client";
import { useState, useRef } from "react";

interface Props {
  sceneId: number;
  currentPrompt: string;
  onClose: () => void;
  onRegenerate: (sceneId: number, prompt: string) => Promise<void>;
  onUpload: (sceneId: number, file: File) => Promise<void>;
}

export function ImageReplaceModal({
  sceneId,
  currentPrompt,
  onClose,
  onRegenerate,
  onUpload,
}: Props) {
  const [prompt, setPrompt] = useState(currentPrompt);
  const [loading, setLoading] = useState(false);
  const [loadingAction, setLoadingAction] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const handleRegenerate = async () => {
    setLoading(true);
    setLoadingAction("regenerate");
    try {
      await onRegenerate(sceneId, prompt);
      onClose();
    } catch {
      setLoading(false);
      setLoadingAction("");
    }
  };

  const handleEdit = async () => {
    setLoading(true);
    setLoadingAction("edit");
    try {
      await onRegenerate(sceneId, prompt);
      onClose();
    } catch {
      setLoading(false);
      setLoadingAction("");
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setLoadingAction("upload");
    try {
      await onUpload(sceneId, file);
      onClose();
    } catch {
      setLoading(false);
      setLoadingAction("");
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-gray-800 rounded-xl w-full max-w-md p-6 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-bold">
            씬 {sceneId} 이미지 교체
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-xl"
          >
            x
          </button>
        </div>

        <div>
          <label className="block text-sm text-gray-400 mb-1">
            이미지 프롬프트
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={4}
            className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm focus:border-blue-500 focus:outline-none resize-y"
            disabled={loading}
          />
        </div>

        <div className="space-y-2">
          <button
            onClick={handleRegenerate}
            disabled={loading || !prompt.trim()}
            className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 rounded-lg text-sm font-medium transition"
          >
            {loadingAction === "regenerate"
              ? "생성 중..."
              : "새로 생성 (프롬프트로 새 이미지)"}
          </button>
          <button
            onClick={handleEdit}
            disabled={loading || !prompt.trim()}
            className="w-full py-2.5 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 disabled:text-gray-500 rounded-lg text-sm font-medium transition"
          >
            {loadingAction === "edit"
              ? "수정 중..."
              : "수정 재생성 (프롬프트 수정 후 생성)"}
          </button>
          <button
            onClick={() => fileRef.current?.click()}
            disabled={loading}
            className="w-full py-2.5 bg-green-600 hover:bg-green-500 disabled:bg-gray-700 disabled:text-gray-500 rounded-lg text-sm font-medium transition"
          >
            {loadingAction === "upload"
              ? "업로드 중..."
              : "직접 업로드 (내 이미지 사용)"}
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            className="hidden"
          />
        </div>
      </div>
    </div>
  );
}
