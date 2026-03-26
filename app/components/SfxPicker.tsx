"use client";
import { useState, useRef } from "react";

interface SfxEffect {
  name: string;
  category: string;
  filename: string;
  duration_ms: number;
  description: string;
}

interface SfxCategory {
  id: string;
  label: string;
}

const CATEGORIES: SfxCategory[] = [
  { id: "all", label: "전체" },
  { id: "surprise", label: "놀람" },
  { id: "laugh", label: "웃음" },
  { id: "touching", label: "감동" },
  { id: "emphasis", label: "강조" },
  { id: "ui", label: "UI" },
];

const SFX_EFFECTS: SfxEffect[] = [
  { name: "surprise_ding", category: "surprise", filename: "surprise_ding.mp3", duration_ms: 1200, description: "띠링" },
  { name: "surprise_boom", category: "surprise", filename: "surprise_boom.mp3", duration_ms: 1500, description: "두둥" },
  { name: "surprise_huh", category: "surprise", filename: "surprise_huh.mp3", duration_ms: 800, description: "어!?" },
  { name: "laugh_haha", category: "laugh", filename: "laugh_haha.mp3", duration_ms: 2000, description: "하하하" },
  { name: "laugh_kkk", category: "laugh", filename: "laugh_kkk.mp3", duration_ms: 1500, description: "크크크" },
  { name: "laugh_burst", category: "laugh", filename: "laugh_burst.mp3", duration_ms: 1800, description: "빵터짐" },
  { name: "touching_bell", category: "touching", filename: "touching_bell.mp3", duration_ms: 2500, description: "잔잔한 종소리" },
  { name: "touching_warm", category: "touching", filename: "touching_warm.mp3", duration_ms: 2000, description: "훈훈한 효과음" },
  { name: "emphasis_drumroll", category: "emphasis", filename: "emphasis_drumroll.mp3", duration_ms: 2000, description: "두구두구" },
  { name: "emphasis_tada", category: "emphasis", filename: "emphasis_tada.mp3", duration_ms: 1500, description: "짜잔" },
  { name: "emphasis_reveal", category: "emphasis", filename: "emphasis_reveal.mp3", duration_ms: 1200, description: "타다" },
  { name: "ui_transition", category: "ui", filename: "ui_transition.mp3", duration_ms: 600, description: "전환 효과음" },
  { name: "ui_click", category: "ui", filename: "ui_click.mp3", duration_ms: 300, description: "클릭" },
];

interface SfxConfig {
  name: string;
  category: string;
  offset_ms: number;
  volume: number;
}

interface Props {
  sceneId: number;
  currentSfx: SfxConfig[];
  onSfxChange: (sfx: SfxConfig[]) => void;
  onClose: () => void;
}

export function SfxPicker({ sceneId, currentSfx, onSfxChange, onClose }: Props) {
  const [category, setCategory] = useState("all");
  const [selected, setSelected] = useState<SfxConfig[]>(currentSfx);
  const [volume, setVolume] = useState(0.2);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const filtered = SFX_EFFECTS.filter(
    (e) => category === "all" || e.category === category
  );

  const handlePreview = (effect: SfxEffect) => {
    // Audio preview would need actual MP3 files in /data/sfx/
    // For now, just show a visual indicator
    console.log("Preview:", effect.filename);
  };

  const handleAdd = (effect: SfxEffect) => {
    const newSfx: SfxConfig = {
      name: effect.name,
      category: effect.category,
      offset_ms: 0,
      volume,
    };
    setSelected([...selected, newSfx]);
  };

  const handleRemove = (idx: number) => {
    setSelected(selected.filter((_, i) => i !== idx));
  };

  const handleSave = () => {
    onSfxChange(selected);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-xl w-full max-w-md max-h-[80vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h3 className="font-medium">효과음 (씬 {sceneId})</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-lg">✕</button>
        </div>

        {/* Category filter */}
        <div className="flex gap-1 p-3 border-b border-gray-800 overflow-x-auto">
          {CATEGORIES.map((c) => (
            <button
              key={c.id}
              onClick={() => setCategory(c.id)}
              className={`px-3 py-1 rounded text-xs font-medium whitespace-nowrap transition ${
                category === c.id
                  ? "bg-blue-600 text-white"
                  : "bg-gray-800 text-gray-400 hover:text-white"
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        {/* Effect list */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          {filtered.map((effect) => {
            const isAdded = selected.some((s) => s.name === effect.name);
            return (
              <div
                key={effect.name}
                className="flex items-center gap-3 p-2.5 bg-gray-800 rounded-lg"
              >
                <button
                  onClick={() => handlePreview(effect)}
                  className="w-8 h-8 flex items-center justify-center bg-gray-700 hover:bg-gray-600 rounded-full text-sm"
                >
                  ▶
                </button>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium">{effect.description}</div>
                  <div className="text-[10px] text-gray-500">
                    {(effect.duration_ms / 1000).toFixed(1)}s
                  </div>
                </div>
                <button
                  onClick={() => isAdded ? undefined : handleAdd(effect)}
                  className={`px-3 py-1 rounded text-xs font-medium transition ${
                    isAdded
                      ? "bg-green-700 text-green-200 cursor-default"
                      : "bg-blue-600 hover:bg-blue-500"
                  }`}
                >
                  {isAdded ? "추가됨" : "+ 추가"}
                </button>
              </div>
            );
          })}
        </div>

        {/* Selected effects */}
        {selected.length > 0 && (
          <div className="p-3 border-t border-gray-800">
            <div className="text-xs text-gray-400 mb-2">선택된 효과음 ({selected.length})</div>
            <div className="space-y-1">
              {selected.map((sfx, i) => {
                const effect = SFX_EFFECTS.find((e) => e.name === sfx.name);
                return (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <span className="flex-1">{effect?.description || sfx.name}</span>
                    <button
                      onClick={() => handleRemove(i)}
                      className="text-red-400 hover:text-red-300"
                    >
                      ✕
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Volume + save */}
        <div className="p-4 border-t border-gray-700 space-y-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">
              볼륨: {Math.round(volume * 100)}%
            </label>
            <input
              type="range"
              min={0}
              max={50}
              value={Math.round(volume * 100)}
              onChange={(e) => setVolume(Number(e.target.value) / 100)}
              className="w-full"
            />
          </div>
          <button
            onClick={handleSave}
            className="w-full py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-medium transition"
          >
            적용
          </button>
        </div>
      </div>
    </div>
  );
}
