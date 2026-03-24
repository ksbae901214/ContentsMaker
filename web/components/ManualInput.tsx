"use client";

import { useState } from "react";

interface Props {
  onSubmit: (data: { title: string; body: string; comments: string[] }) => void;
}

export function ManualInput({ onSubmit }: Props) {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [comments, setComments] = useState<string[]>([""]);

  const addComment = () => {
    if (comments.length < 10) {
      setComments([...comments, ""]);
    }
  };

  const updateComment = (index: number, value: string) => {
    const updated = [...comments];
    updated[index] = value;
    setComments(updated);
  };

  const removeComment = (index: number) => {
    setComments(comments.filter((_, i) => i !== index));
  };

  const handleSubmit = () => {
    if (!title.trim() || !body.trim()) return;
    onSubmit({
      title: title.trim(),
      body: body.trim(),
      comments: comments.filter((c) => c.trim()),
    });
  };

  const isValid = title.trim() && body.trim();

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">
          제목 *
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="블라인드 게시글 제목"
          className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">
          본문 *
        </label>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="블라인드 게시글 본문을 입력하세요"
          rows={8}
          className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none resize-y"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">
          댓글 (선택)
        </label>
        {comments.map((comment, i) => (
          <div key={i} className="flex gap-2 mb-2">
            <input
              type="text"
              value={comment}
              onChange={(e) => updateComment(i, e.target.value)}
              placeholder={`댓글 ${i + 1}`}
              className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none text-sm"
            />
            {comments.length > 1 && (
              <button
                onClick={() => removeComment(i)}
                className="text-red-400 hover:text-red-300 px-2"
              >
                ✕
              </button>
            )}
          </div>
        ))}
        <button
          onClick={addComment}
          className="text-sm text-blue-400 hover:text-blue-300"
        >
          + 댓글 추가
        </button>
      </div>

      <button
        onClick={handleSubmit}
        disabled={!isValid}
        className={`w-full py-3 rounded-lg font-medium transition ${
          isValid
            ? "bg-blue-600 hover:bg-blue-500 cursor-pointer"
            : "bg-gray-700 text-gray-500 cursor-not-allowed"
        }`}
      >
        🎬 영상 생성하기
      </button>
    </div>
  );
}
