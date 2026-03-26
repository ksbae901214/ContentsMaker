"use client";
import { useState, useRef } from "react";

interface VoiceInfo {
  name: string;
  gender: string;
  tone: string;
  description: string;
}

const KOREAN_VOICES: VoiceInfo[] = [
  { name: "ko-KR-SunHiNeural", gender: "female", tone: "bright", description: "밝고 활기찬 여성 음성 (기본값)" },
  { name: "ko-KR-InJoonNeural", gender: "male", tone: "calm", description: "차분하고 신뢰감 있는 남성 음성" },
  { name: "ko-KR-BongJinNeural", gender: "male", tone: "deep", description: "깊고 무게감 있는 남성 음성" },
  { name: "ko-KR-GookMinNeural", gender: "male", tone: "neutral", description: "중립적이고 안정감 있는 남성 음성" },
  { name: "ko-KR-JiMinNeural", gender: "female", tone: "soft", description: "부드럽고 감성적인 여성 음성" },
  { name: "ko-KR-SeoHyeonNeural", gender: "female", tone: "professional", description: "전문적이고 또렷한 여성 음성" },
  { name: "ko-KR-SoonBokNeural", gender: "female", tone: "warm", description: "따뜻하고 친근한 여성 음성" },
  { name: "ko-KR-YuJinNeural", gender: "female", tone: "clear", description: "맑고 깨끗한 여성 음성" },
];

interface Props {
  currentVoice: string;
  scriptPath: string;
  onVoiceChange: (voice: string) => void;
  onClose: () => void;
}

export function VoicePicker({
  currentVoice,
  scriptPath,
  onVoiceChange,
  onClose,
}: Props) {
  const [selectedVoice, setSelectedVoice] = useState(currentVoice);
  const [genderFilter, setGenderFilter] = useState<"all" | "male" | "female">("all");
  const [previewLoading, setPreviewLoading] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const filtered = KOREAN_VOICES.filter(
    (v) => genderFilter === "all" || v.gender === genderFilter
  );

  const handlePreview = async (voice: string) => {
    if (previewLoading) return;
    setPreviewLoading(voice);

    try {
      // Stop any currently playing audio
      if (audioRef.current) {
        audioRef.current.pause();
        URL.revokeObjectURL(audioRef.current.src);
      }

      const res = await fetch("/api/tts/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ voice }),
      });

      if (!res.ok) throw new Error("Preview failed");

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.play();
      audio.onended = () => URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Preview error:", e);
    } finally {
      setPreviewLoading(null);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // Update voice in script JSON
      const res = await fetch("/api/scene/script", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scriptPath, voice: selectedVoice }),
      });
      if (res.ok) {
        onVoiceChange(selectedVoice);
        onClose();
      }
    } catch (e) {
      console.error("Voice save failed:", e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-xl w-full max-w-md max-h-[80vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h3 className="font-medium">음성 선택</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-lg"
          >
            ✕
          </button>
        </div>

        {/* Gender filter */}
        <div className="flex gap-1 p-3 border-b border-gray-800">
          {(["all", "female", "male"] as const).map((g) => (
            <button
              key={g}
              onClick={() => setGenderFilter(g)}
              className={`flex-1 py-1.5 rounded text-xs font-medium transition ${
                genderFilter === g
                  ? "bg-blue-600 text-white"
                  : "bg-gray-800 text-gray-400 hover:text-white"
              }`}
            >
              {g === "all" ? "전체" : g === "female" ? "여성" : "남성"}
            </button>
          ))}
        </div>

        {/* Voice list */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          {filtered.map((voice) => {
            const isSelected = selectedVoice === voice.name;
            const isCurrent = currentVoice === voice.name;
            const isLoading = previewLoading === voice.name;

            return (
              <div
                key={voice.name}
                onClick={() => setSelectedVoice(voice.name)}
                className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition ${
                  isSelected
                    ? "bg-blue-600/20 ring-1 ring-blue-500"
                    : "bg-gray-800 hover:bg-gray-700"
                }`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">
                      {voice.name.replace("ko-KR-", "").replace("Neural", "")}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-700 text-gray-400">
                      {voice.gender === "female" ? "여" : "남"}
                    </span>
                    {isCurrent && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-700 text-green-200">
                        현재
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    {voice.description}
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handlePreview(voice.name);
                  }}
                  disabled={isLoading}
                  className="w-8 h-8 flex items-center justify-center bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 rounded-full text-sm transition"
                >
                  {isLoading ? "..." : "▶"}
                </button>
              </div>
            );
          })}
        </div>

        {/* Save */}
        <div className="p-4 border-t border-gray-700">
          <button
            onClick={handleSave}
            disabled={saving || selectedVoice === currentVoice}
            className={`w-full py-2.5 rounded-lg text-sm font-medium transition ${
              selectedVoice !== currentVoice && !saving
                ? "bg-blue-600 hover:bg-blue-500"
                : "bg-gray-700 text-gray-500 cursor-not-allowed"
            }`}
          >
            {saving
              ? "적용 중..."
              : selectedVoice === currentVoice
                ? "변경사항 없음"
                : "음성 적용"}
          </button>
        </div>
      </div>
    </div>
  );
}
