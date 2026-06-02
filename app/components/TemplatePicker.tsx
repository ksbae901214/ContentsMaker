"use client";
import { useState, useEffect } from "react";

interface TemplateData {
  name: string;
  subtitle_style: Record<string, unknown>;
  transition: Record<string, unknown>;
  voice: string;
  bgm_enabled: boolean;
}

interface Props {
  onApply: (template: TemplateData) => void;
  onClose: () => void;
}

const BUILT_IN: TemplateData[] = [
  {
    name: "유머형",
    subtitle_style: { font_family: "Noto Sans KR", font_size: 72, font_weight: "900", color: "#FFD700", shadow: "4px 4px 12px rgba(0,0,0,0.9)", position_y: 0.5, bg_color: null, bg_opacity: 0 },
    transition: { type: "zoom", duration: 0.4 },
    voice: "ko-KR-SunHiNeural",
    bgm_enabled: true,
  },
  {
    name: "감성형",
    subtitle_style: { font_family: "Noto Sans KR", font_size: 52, font_weight: "500", color: "#FFFFFF", shadow: "2px 2px 6px rgba(0,0,0,0.6)", position_y: 0.7, bg_color: "#1a1a2e", bg_opacity: 0.5 },
    transition: { type: "dissolve", duration: 0.7 },
    voice: "ko-KR-JiMinNeural",
    bgm_enabled: true,
  },
  {
    name: "뉴스형",
    subtitle_style: { font_family: "Noto Sans KR", font_size: 48, font_weight: "bold", color: "#FFFFFF", shadow: "1px 1px 4px rgba(0,0,0,0.5)", position_y: 0.8, bg_color: "#000000", bg_opacity: 0.7 },
    transition: { type: "slide-left", duration: 0.5 },
    voice: "ko-KR-InJoonNeural",
    bgm_enabled: false,
  },
];

const STYLE_PREVIEW: Record<string, { bg: string; text: string }> = {
  "유머형": { bg: "from-orange-600 to-yellow-500", text: "text-yellow-300" },
  "감성형": { bg: "from-indigo-700 to-purple-600", text: "text-white" },
  "뉴스형": { bg: "from-gray-700 to-gray-900", text: "text-white" },
};

export function TemplatePicker({ onApply, onClose }: Props) {
  const [selected, setSelected] = useState<string | null>(null);

  const handleApply = () => {
    const template = BUILT_IN.find((t) => t.name === selected);
    if (template) {
      onApply(template);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-xl w-full max-w-md">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h3 className="font-medium">템플릿 선택</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-lg">
            ✕
          </button>
        </div>

        <div className="p-4 space-y-3">
          {BUILT_IN.map((t) => {
            const preview = STYLE_PREVIEW[t.name] || { bg: "from-gray-600 to-gray-800", text: "text-white" };
            const isSelected = selected === t.name;

            return (
              <button
                key={t.name}
                onClick={() => setSelected(t.name)}
                className={`w-full text-left rounded-lg overflow-hidden transition ${
                  isSelected ? "ring-2 ring-blue-500" : "ring-1 ring-gray-700"
                }`}
              >
                {/* Mini preview */}
                <div className={`h-16 bg-gradient-to-r ${preview.bg} flex items-center justify-center`}>
                  <span className={`text-lg font-bold ${preview.text}`}>
                    미리보기 텍스트
                  </span>
                </div>
                <div className="p-3 bg-gray-800">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{t.name}</span>
                    <div className="flex gap-1 text-[10px] text-gray-400">
                      <span>전환: {(t.transition as any).type}</span>
                      <span>|</span>
                      <span>{t.bgm_enabled ? "BGM ON" : "BGM OFF"}</span>
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        <div className="p-4 border-t border-gray-700">
          <button
            onClick={handleApply}
            disabled={!selected}
            className={`w-full py-2.5 rounded-lg font-medium transition ${
              selected
                ? "bg-blue-600 hover:bg-blue-500"
                : "bg-gray-700 text-gray-500 cursor-not-allowed"
            }`}
          >
            {selected ? `"${selected}" 적용` : "템플릿을 선택하세요"}
          </button>
        </div>
      </div>
    </div>
  );
}
