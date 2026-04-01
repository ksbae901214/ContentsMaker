"use client";
import { useState } from "react";

export interface SubtitleStyle {
  font_family: string;
  font_size: number;
  font_weight: string;
  color: string;
  shadow: string;
  position_y: number;
  bg_color: string | null;
  bg_opacity: number;
}

const DEFAULT_STYLE: SubtitleStyle = {
  font_family: "Noto Sans KR",
  font_size: 55,
  font_weight: "bold",
  color: "#FFFFFF",
  shadow: "3px 3px 8px rgba(0,0,0,0.7)",
  position_y: 0.6,
  bg_color: null,
  bg_opacity: 0.0,
};

interface Preset {
  name: string;
  label: string;
  style: SubtitleStyle;
}

const PRESETS: Preset[] = [
  {
    name: "news",
    label: "뉴스형",
    style: {
      font_family: "Noto Sans KR",
      font_size: 48,
      font_weight: "bold",
      color: "#FFFFFF",
      shadow: "1px 1px 4px rgba(0,0,0,0.5)",
      position_y: 0.8,
      bg_color: "#000000",
      bg_opacity: 0.7,
    },
  },
  {
    name: "humor",
    label: "유머형",
    style: {
      font_family: "Noto Sans KR",
      font_size: 72,
      font_weight: "900",
      color: "#FFD700",
      shadow: "4px 4px 12px rgba(0,0,0,0.9)",
      position_y: 0.5,
      bg_color: null,
      bg_opacity: 0.0,
    },
  },
  {
    name: "emotional",
    label: "감성형",
    style: {
      font_family: "Noto Sans KR",
      font_size: 52,
      font_weight: "500",
      color: "#FFFFFF",
      shadow: "2px 2px 6px rgba(0,0,0,0.6)",
      position_y: 0.7,
      bg_color: "#1a1a2e",
      bg_opacity: 0.5,
    },
  },
];

interface Props {
  style: SubtitleStyle;
  sceneId: number;
  scriptPath: string;
  onStyleChange: (style: SubtitleStyle) => void;
  onClose: () => void;
}

export function SubtitleStyleEditor({
  style: initialStyle,
  sceneId,
  scriptPath,
  onStyleChange,
  onClose,
}: Props) {
  const [style, setStyle] = useState<SubtitleStyle>(initialStyle);
  const [saving, setSaving] = useState(false);

  const updateField = <K extends keyof SubtitleStyle>(
    field: K,
    value: SubtitleStyle[K]
  ) => {
    setStyle((prev) => ({ ...prev, [field]: value }));
  };

  const applyPreset = (preset: Preset) => {
    setStyle(preset.style);
  };

  const handleSave = async (applyAll: boolean) => {
    setSaving(true);
    try {
      const res = await fetch("/api/scene/style", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scene_id: sceneId,
          subtitle_style: style,
          script_path: scriptPath,
          apply_all: applyAll,
        }),
      });
      if (res.ok) {
        onStyleChange(style);
        onClose();
      }
    } catch (e) {
      console.error("Style save failed:", e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-xl w-full max-w-md max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h3 className="font-medium">자막 스타일 (씬 {sceneId})</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-lg"
          >
            ✕
          </button>
        </div>

        <div className="p-4 space-y-4">
          {/* Presets */}
          <div>
            <label className="text-xs text-gray-400 mb-2 block">
              프리셋
            </label>
            <div className="flex gap-2">
              {PRESETS.map((p) => (
                <button
                  key={p.name}
                  onClick={() => applyPreset(p)}
                  className="flex-1 py-2 px-3 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs font-medium transition"
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Preview */}
          <div
            className="relative h-32 rounded-lg overflow-hidden"
            style={{
              background:
                "linear-gradient(135deg, #4169E1, #1E90FF, #87CEEB)",
            }}
          >
            <div
              className="absolute left-0 right-0 text-center px-4"
              style={{
                top: `${style.position_y * 100}%`,
                transform: "translateY(-50%)",
              }}
            >
              {style.bg_color && style.bg_opacity > 0 && (
                <div
                  className="absolute inset-0 rounded-md -m-2"
                  style={{
                    backgroundColor: style.bg_color,
                    opacity: style.bg_opacity,
                  }}
                />
              )}
              <span
                className="relative"
                style={{
                  fontFamily: style.font_family,
                  fontSize: `${Math.min(style.font_size * 0.4, 28)}px`,
                  fontWeight: style.font_weight as any,
                  color: style.color,
                  textShadow: style.shadow,
                }}
              >
                미리보기 텍스트
              </span>
            </div>
          </div>

          {/* Font size */}
          <div>
            <label className="text-xs text-gray-400 mb-1 block">
              폰트 크기: {style.font_size}px
            </label>
            <input
              type="range"
              min={20}
              max={120}
              value={style.font_size}
              onChange={(e) =>
                updateField("font_size", Number(e.target.value))
              }
              className="w-full"
            />
          </div>

          {/* Font weight */}
          <div>
            <label className="text-xs text-gray-400 mb-1 block">
              굵기
            </label>
            <div className="flex gap-2">
              {["400", "500", "700", "900"].map((w) => (
                <button
                  key={w}
                  onClick={() => updateField("font_weight", w)}
                  className={`flex-1 py-1.5 rounded text-xs transition ${
                    style.font_weight === w
                      ? "bg-blue-600"
                      : "bg-gray-800 hover:bg-gray-700"
                  }`}
                >
                  {w === "400"
                    ? "보통"
                    : w === "500"
                      ? "중간"
                      : w === "700"
                        ? "굵게"
                        : "매우 굵게"}
                </button>
              ))}
            </div>
          </div>

          {/* Text color */}
          <div>
            <label className="text-xs text-gray-400 mb-1 block">
              텍스트 색상
            </label>
            <div className="flex gap-2 items-center">
              <input
                type="color"
                value={style.color}
                onChange={(e) => updateField("color", e.target.value)}
                className="w-8 h-8 rounded cursor-pointer"
              />
              <input
                value={style.color}
                onChange={(e) => updateField("color", e.target.value)}
                className="flex-1 px-2 py-1 bg-gray-800 border border-gray-600 rounded text-sm"
              />
            </div>
          </div>

          {/* Position */}
          <div>
            <label className="text-xs text-gray-400 mb-1 block">
              수직 위치: {Math.round(style.position_y * 100)}%
            </label>
            <input
              type="range"
              min={0}
              max={100}
              value={Math.round(style.position_y * 100)}
              onChange={(e) =>
                updateField("position_y", Number(e.target.value) / 100)
              }
              className="w-full"
            />
          </div>

          {/* Background */}
          <div>
            <label className="text-xs text-gray-400 mb-1 block">
              배경
            </label>
            <div className="flex gap-2 items-center">
              <label className="flex items-center gap-1 text-xs">
                <input
                  type="checkbox"
                  checked={style.bg_color !== null}
                  onChange={(e) =>
                    updateField(
                      "bg_color",
                      e.target.checked ? "#000000" : null
                    )
                  }
                />
                사용
              </label>
              {style.bg_color !== null && (
                <>
                  <input
                    type="color"
                    value={style.bg_color}
                    onChange={(e) => updateField("bg_color", e.target.value)}
                    className="w-8 h-8 rounded cursor-pointer"
                  />
                  <div className="flex-1">
                    <label className="text-[10px] text-gray-500">
                      투명도: {Math.round(style.bg_opacity * 100)}%
                    </label>
                    <input
                      type="range"
                      min={0}
                      max={100}
                      value={Math.round(style.bg_opacity * 100)}
                      onChange={(e) =>
                        updateField(
                          "bg_opacity",
                          Number(e.target.value) / 100
                        )
                      }
                      className="w-full"
                    />
                  </div>
                </>
              )}
            </div>
          </div>
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
