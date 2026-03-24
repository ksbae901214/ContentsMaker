"use client";

interface Props {
  messages: string[];
}

const STEP_ICONS: Record<string, string> = {
  "텍스트 추출": "📸",
  "AI 분석": "📝",
  "만화 이미지": "🎨",
  "음성 생성": "🎙️",
  "영상 렌더링": "🎬",
};

function getIcon(message: string): string {
  for (const [key, icon] of Object.entries(STEP_ICONS)) {
    if (message.includes(key)) return icon;
  }
  return "⏳";
}

export function ProgressTracker({ messages }: Props) {
  const latestMessage = messages[messages.length - 1] || "준비 중...";

  return (
    <div className="space-y-4">
      <div className="text-center py-8">
        <div className="text-5xl mb-4 animate-bounce">{getIcon(latestMessage)}</div>
        <h2 className="text-xl font-bold mb-2">영상 생성 중...</h2>
        <p className="text-gray-400">{latestMessage}</p>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-gray-800 rounded-full h-2">
        <div
          className="bg-blue-600 h-2 rounded-full transition-all duration-500"
          style={{ width: `${Math.min((messages.length / 7) * 100, 95)}%` }}
        />
      </div>

      {/* Log */}
      <div className="bg-gray-900 rounded-lg p-4 max-h-64 overflow-y-auto">
        {messages.map((msg, i) => (
          <div key={i} className="flex items-start gap-2 py-1 text-sm">
            <span className="text-green-400 mt-0.5">✓</span>
            <span className="text-gray-300">{msg}</span>
          </div>
        ))}
        <div className="flex items-start gap-2 py-1 text-sm">
          <span className="text-yellow-400 animate-pulse mt-0.5">●</span>
          <span className="text-gray-500">처리 중...</span>
        </div>
      </div>
    </div>
  );
}
