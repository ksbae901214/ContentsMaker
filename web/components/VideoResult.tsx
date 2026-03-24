"use client";

interface JobResult {
  videoPath: string;
  title: string;
  emotion: string;
  duration: number;
  imageCount: number;
  cost: number;
}

interface Props {
  result: JobResult;
  onReset: () => void;
}

const EMOTION_LABELS: Record<string, string> = {
  funny: "😂 재밌음",
  touching: "🥹 감동",
  angry: "😤 분노",
  relatable: "🤝 공감",
};

export function VideoResult({ result, onReset }: Props) {
  const videoUrl = `/api/download?path=${encodeURIComponent(result.videoPath)}`;

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="text-5xl mb-3">🎉</div>
        <h2 className="text-2xl font-bold">영상 생성 완료!</h2>
      </div>

      {/* Video preview */}
      <div className="bg-gray-900 rounded-xl overflow-hidden">
        <video
          src={videoUrl}
          controls
          className="w-full max-h-[500px] mx-auto"
          style={{ aspectRatio: "9/16", maxWidth: "300px", margin: "0 auto", display: "block" }}
        />
      </div>

      {/* Info */}
      <div className="bg-gray-800 rounded-lg p-4 space-y-2">
        <div className="flex justify-between">
          <span className="text-gray-400">제목</span>
          <span className="font-medium">{result.title}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">감정</span>
          <span>{EMOTION_LABELS[result.emotion] || result.emotion}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">길이</span>
          <span>{result.duration}초</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">만화 이미지</span>
          <span>{result.imageCount}장</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">GPT API 비용</span>
          <span className="text-green-400">${result.cost.toFixed(3)}</span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <a
          href={videoUrl}
          download
          className="flex-1 py-3 bg-blue-600 hover:bg-blue-500 rounded-lg font-medium text-center transition"
        >
          ⬇️ MP4 다운로드
        </a>
        <button
          onClick={onReset}
          className="flex-1 py-3 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium transition"
        >
          🔄 새로 만들기
        </button>
      </div>
    </div>
  );
}
