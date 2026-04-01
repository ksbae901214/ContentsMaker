"use client";
import { useState, useEffect } from "react";

interface ProjectSummary {
  id: string;
  name: string;
  updated_at: string;
  created_at: string;
  has_output: boolean;
}

interface Props {
  onLoad: (projectId: string) => void;
  onClose: () => void;
}

export function ProjectList({ onLoad, onClose }: Props) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/project/list");
      if (res.ok) {
        const data = await res.json();
        setProjects(data.projects || []);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("프로젝트를 삭제하시겠습니까?")) return;
    setDeleting(id);
    try {
      await fetch(`/api/project/delete?id=${id}`, { method: "DELETE" });
      setProjects(projects.filter((p) => p.id !== id));
    } catch {
      // ignore
    } finally {
      setDeleting(null);
    }
  };

  const formatDate = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString("ko-KR", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-xl w-full max-w-md max-h-[70vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h3 className="font-medium">프로젝트 불러오기</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-lg"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          {loading ? (
            <div className="text-center py-8 text-gray-500">로딩 중...</div>
          ) : projects.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              저장된 프로젝트가 없습니다
            </div>
          ) : (
            <div className="space-y-2">
              {projects.map((p) => (
                <div
                  key={p.id}
                  className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg hover:bg-gray-700 transition cursor-pointer"
                  onClick={() => onLoad(p.id)}
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">
                      {p.name}
                    </div>
                    <div className="text-xs text-gray-500">
                      {formatDate(p.updated_at)}
                      {p.has_output && (
                        <span className="ml-2 text-green-400">영상 있음</span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(p.id);
                    }}
                    disabled={deleting === p.id}
                    className="text-xs text-red-400 hover:text-red-300 px-2 py-1"
                  >
                    {deleting === p.id ? "..." : "삭제"}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
