"use client";
import { useState } from "react";

type TransitionType =
  | "fade"
  | "slide-left"
  | "slide-up"
  | "zoom"
  | "dissolve"
  | "wipe";

interface TransitionConfig {
  type: TransitionType;
  duration: number;
}

const TRANSITION_OPTIONS: { type: TransitionType; label: string; icon: string }[] = [
  { type: "fade", label: "페이드", icon: "◐" },
  { type: "slide-left", label: "슬라이드 좌", icon: "◀" },
  { type: "slide-up", label: "슬라이드 상", icon: "▲" },
  { type: "zoom", label: "줌", icon: "◎" },
  { type: "dissolve", label: "디졸브", icon: "◑" },
  { type: "wipe", label: "와이프", icon: "▬" },
];

interface Props {
  transition: TransitionConfig;
  sceneId: number;
  scriptPath: string;
  onTransitionChange: (t: TransitionConfig) => void;
  onClose: () => void;
}

export function TransitionPicker({
  transition: initialTransition,
  sceneId,
  scriptPath,
  onTransitionChange,
  onClose,
}: Props) {
  const [config, setConfig] = useState<TransitionConfig>(initialTransition);
  const [saving, setSaving] = useState(false);

  const handleSave = async (applyAll: boolean) => {
    setSaving(true);
    try {
      const res = await fetch("/api/scene/transition", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scene_id: sceneId,
          transition: config,
          script_path: scriptPath,
          apply_all: applyAll,
        }),
      });
      if (res.ok) {
        onTransitionChange(config);
        onClose();
      }
    } catch (e) {
      console.error("Transition save failed:", e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-xl w-full max-w-sm">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h3 className="font-medium">트랜지션 (씬 {sceneId})</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-lg"
          >
            ✕
          </button>
        </div>

        <div className="p-4 space-y-4">
          {/* Effect grid */}
          <div className="grid grid-cols-3 gap-2">
            {TRANSITION_OPTIONS.map((opt) => (
              <button
                key={opt.type}
                onClick={() => setConfig({ ...config, type: opt.type })}
                className={`flex flex-col items-center gap-1 p-3 rounded-lg transition ${
                  config.type === opt.type
                    ? "bg-blue-600 text-white"
                    : "bg-gray-800 hover:bg-gray-700 text-gray-300"
                }`}
              >
                <span className="text-xl">{opt.icon}</span>
                <span className="text-[11px]">{opt.label}</span>
              </button>
            ))}
          </div>

          {/* Duration slider */}
          <div>
            <label className="text-xs text-gray-400 mb-1 block">
              전환 시간: {config.duration.toFixed(1)}초
            </label>
            <input
              type="range"
              min={30}
              max={100}
              value={Math.round(config.duration * 100)}
              onChange={(e) =>
                setConfig({
                  ...config,
                  duration: Number(e.target.value) / 100,
                })
              }
              className="w-full"
            />
            <div className="flex justify-between text-[10px] text-gray-500">
              <span>0.3s</span>
              <span>1.0s</span>
            </div>
          </div>

          {/* Remove transition */}
          <button
            onClick={() => {
              // Save null transition to remove it
              setSaving(true);
              fetch("/api/scene/transition", {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  scene_id: sceneId,
                  transition: null,
                  script_path: scriptPath,
                  apply_all: false,
                }),
              })
                .then(() => {
                  onTransitionChange({ type: "fade", duration: 0 });
                  onClose();
                })
                .finally(() => setSaving(false));
            }}
            className="w-full py-1.5 text-xs text-red-400 hover:text-red-300 transition"
          >
            트랜지션 제거
          </button>
        </div>

        {/* Actions */}
        <div className="p-4 border-t border-gray-700 flex gap-2">
          <button
            onClick={() => handleSave(false)}
            disabled={saving}
            className="flex-1 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 rounded-lg text-sm font-medium transition"
          >
            {saving ? "저장 중..." : "이 씬에 적용"}
          </button>
          <button
            onClick={() => handleSave(true)}
            disabled={saving}
            className="flex-1 py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 rounded-lg text-sm font-medium transition"
          >
            전체 적용
          </button>
        </div>
      </div>
    </div>
  );
}
