"use client";

import { useState, useCallback } from "react";

interface Props {
  onSubmit: (files: File[]) => void;
}

export function ImageUploader({ onSubmit }: Props) {
  const [files, setFiles] = useState<File[]>([]);
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = Array.from(e.dataTransfer.files).filter((f) =>
      f.type.startsWith("image/")
    );
    setFiles((prev) => [...prev, ...dropped]);
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles((prev) => [...prev, ...Array.from(e.target.files!)]);
    }
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-8 text-center transition cursor-pointer ${
          dragOver
            ? "border-blue-500 bg-blue-500/10"
            : "border-gray-600 hover:border-gray-500"
        }`}
        onClick={() => document.getElementById("file-input")?.click()}
      >
        <div className="text-4xl mb-3">📸</div>
        <p className="text-lg font-medium mb-1">
          블라인드 스크린샷을 드래그하세요
        </p>
        <p className="text-gray-500 text-sm">또는 클릭하여 파일 선택 (여러 장 가능)</p>
        <input
          id="file-input"
          type="file"
          accept="image/*"
          multiple
          onChange={handleFileChange}
          className="hidden"
        />
      </div>

      {files.length > 0 && (
        <div className="mt-4 space-y-2">
          {files.map((file, i) => (
            <div
              key={i}
              className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-2"
            >
              <span className="text-sm truncate">{file.name}</span>
              <button
                onClick={() => removeFile(i)}
                className="text-red-400 hover:text-red-300 ml-2"
              >
                ✕
              </button>
            </div>
          ))}

          <button
            onClick={() => onSubmit(files)}
            className="w-full mt-4 py-3 bg-blue-600 hover:bg-blue-500 rounded-lg font-medium transition"
          >
            🎬 영상 생성하기 ({files.length}장)
          </button>
        </div>
      )}
    </div>
  );
}
