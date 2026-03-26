"use client";
import { useState } from "react";

interface BatchItem {
  input_type: "url" | "file";
  input_data: string;
}

interface JobStatus {
  index: number;
  status: "pending" | "processing" | "completed" | "failed";
  title?: string;
  error?: string;
}

interface Props {
  onClose: () => void;
}

export function BatchQueue({ onClose }: Props) {
  const [urls, setUrls] = useState("");
  const [running, setRunning] = useState(false);
  const [jobs, setJobs] = useState<JobStatus[]>([]);
  const [completed, setCompleted] = useState(false);

  const handleStart = async () => {
    const lines = urls
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.length > 0);

    if (lines.length === 0) return;

    const items: BatchItem[] = lines.map((url) => ({
      input_type: "url",
      input_data: url,
    }));

    setRunning(true);
    setJobs(
      items.map((_, i) => ({ index: i, status: "pending" as const }))
    );

    try {
      const res = await fetch("/api/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items }),
      });

      const reader = res.body?.getReader();
      if (!reader) return;

      const dec = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        for (const line of dec
          .decode(value)
          .split("\n")
          .filter((l) => l.startsWith("data: "))) {
          try {
            const d = JSON.parse(line.slice(6));
            if (d.type === "job_update") {
              setJobs((prev) =>
                prev.map((j) =>
                  j.index === d.job_index
                    ? {
                        ...j,
                        status: d.status,
                        title: d.title,
                        error: d.error,
                      }
                    : j
                )
              );
            } else if (d.type === "complete") {
              setCompleted(true);
            }
          } catch {
            // ignore parse errors
          }
        }
      }
    } catch (e: any) {
      console.error("Batch error:", e);
    } finally {
      setRunning(false);
    }
  };

  const statusIcon = (s: string) => {
    switch (s) {
      case "completed":
        return "✅";
      case "failed":
        return "❌";
      case "processing":
        return "⏳";
      default:
        return "⏸";
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-xl w-full max-w-lg max-h-[80vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h3 className="font-medium">일괄 생성</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-lg"
          >
            ✕
          </button>
        </div>

        <div className="p-4 flex-1 overflow-y-auto space-y-4">
          {!running && !completed && (
            <>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">
                  URL 목록 (한 줄에 하나)
                </label>
                <textarea
                  value={urls}
                  onChange={(e) => setUrls(e.target.value)}
                  rows={6}
                  placeholder={
                    "https://gall.dcinside.com/...\nhttps://cafe.naver.com/...\nhttps://..."
                  }
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-sm focus:border-blue-500 focus:outline-none resize-y"
                />
              </div>
              <button
                onClick={handleStart}
                disabled={urls.trim().length === 0}
                className={`w-full py-2.5 rounded-lg font-medium transition ${
                  urls.trim()
                    ? "bg-blue-600 hover:bg-blue-500"
                    : "bg-gray-700 text-gray-500 cursor-not-allowed"
                }`}
              >
                일괄 생성 시작 (
                {urls.split("\n").filter((l) => l.trim()).length}개)
              </button>
            </>
          )}

          {(running || completed) && (
            <div className="space-y-2">
              {jobs.map((job) => (
                <div
                  key={job.index}
                  className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg"
                >
                  <span className="text-lg">{statusIcon(job.status)}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm truncate">
                      {job.title || `작업 ${job.index + 1}`}
                    </div>
                    {job.error && (
                      <div className="text-xs text-red-400 truncate">
                        {job.error}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {completed && (
            <div className="text-center text-sm text-green-400 py-2">
              {jobs.filter((j) => j.status === "completed").length}/
              {jobs.length}개 완료
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
