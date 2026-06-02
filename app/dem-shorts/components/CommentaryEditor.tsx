// T092: CommentaryEditor — 타임라인 기반 자막 블록 편집 (FR-019)
"use client";

import { useState } from "react";

export interface CommentaryBlock {
  start: number;
  end: number;
  text: string;
  style?: "high" | "medium" | "low";
  highlightWords?: string[];
}

interface CommentaryEditorProps {
  blocks: CommentaryBlock[];
  onChange: (blocks: CommentaryBlock[]) => void;
  maxDuration: number; // cut_duration
}

const MAX_CHARS_PER_LINE = 15;

export function CommentaryEditor({ blocks, onChange, maxDuration }: CommentaryEditorProps) {
  const [newText, setNewText] = useState("");

  const updateBlock = (idx: number, patch: Partial<CommentaryBlock>) => {
    const next = blocks.map((b, i) => (i === idx ? { ...b, ...patch } : b));
    onChange(next);
  };

  const removeBlock = (idx: number) => {
    onChange(blocks.filter((_, i) => i !== idx));
  };

  const addBlock = () => {
    if (!newText.trim()) return;
    const lastEnd = blocks.length > 0 ? blocks[blocks.length - 1].end : 0;
    const newBlock: CommentaryBlock = {
      start: Math.min(lastEnd, maxDuration - 1),
      end: Math.min(lastEnd + 3, maxDuration),
      text: newText.trim(),
      style: "medium",
    };
    onChange([...blocks, newBlock]);
    setNewText("");
  };

  const totalChars = blocks.reduce((sum, b) => sum + b.text.length, 0);
  const totalCoverage = blocks.reduce((sum, b) => sum + Math.max(0, b.end - b.start), 0);
  const coveragePct = maxDuration > 0 ? (totalCoverage / maxDuration) * 100 : 0;

  return (
    <div style={{ border: "1px solid #ddd", borderRadius: 8, padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
        <strong>해설 자막 블록</strong>
        <span style={{ fontSize: 13, color: totalChars >= 50 ? "#090" : "#c00" }}>
          총 {totalChars}자 / 커버리지 {coveragePct.toFixed(0)}%
          {totalChars < 50 && " (50자 이상 필요)"}
          {coveragePct < 30 && " (30% 이상 필요)"}
        </span>
      </div>

      <div style={{ display: "grid", gap: 8 }}>
        {blocks.map((block, idx) => {
          const lines = block.text.split("\n");
          const maxLineLen = Math.max(...lines.map((l) => l.length), 0);
          const warn = maxLineLen > MAX_CHARS_PER_LINE;
          return (
            <div
              key={idx}
              style={{
                background: warn ? "#fff3e0" : "#f5f5f5",
                padding: 10,
                borderRadius: 6,
                display: "grid",
                gridTemplateColumns: "auto auto 1fr auto auto auto",
                gap: 8,
                alignItems: "center",
              }}
            >
              <input
                type="number"
                value={block.start}
                onChange={(e) => updateBlock(idx, { start: Number(e.target.value) })}
                step={0.5}
                min={0}
                max={maxDuration}
                style={{ width: 60, padding: 4 }}
                title="시작 초"
              />
              <span>→</span>
              <textarea
                value={block.text}
                onChange={(e) => updateBlock(idx, { text: e.target.value })}
                style={{
                  width: "100%",
                  minHeight: 50,
                  padding: 6,
                  fontFamily: "inherit",
                  fontSize: 14,
                  border: warn ? "2px solid #f57c00" : "1px solid #ccc",
                }}
              />
              <input
                type="number"
                value={block.end}
                onChange={(e) => updateBlock(idx, { end: Number(e.target.value) })}
                step={0.5}
                min={block.start}
                max={maxDuration}
                style={{ width: 60, padding: 4 }}
                title="종료 초"
              />
              <select
                value={block.style || "medium"}
                onChange={(e) => updateBlock(idx, { style: e.target.value as any })}
                style={{ padding: 4 }}
              >
                <option value="high">강</option>
                <option value="medium">중</option>
                <option value="low">약</option>
              </select>
              <button
                onClick={() => removeBlock(idx)}
                style={{ padding: "4px 10px", background: "#cc0000", color: "#fff", border: "none", borderRadius: 4 }}
              >
                삭제
              </button>
            </div>
          );
        })}
      </div>

      <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
        <textarea
          value={newText}
          onChange={(e) => setNewText(e.target.value)}
          placeholder="새 자막 블록 추가 (한 줄 15자 이내 권장)"
          style={{ flex: 1, padding: 6, minHeight: 60 }}
        />
        <button
          onClick={addBlock}
          style={{ padding: "0 20px", background: "#0066cc", color: "#fff", border: "none", borderRadius: 4 }}
        >
          + 추가
        </button>
      </div>
    </div>
  );
}
