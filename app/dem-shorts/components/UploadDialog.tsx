// T094: 업로드 최종 확정 다이얼로그 (FR-037)
"use client";

import { useState } from "react";

interface UploadDialogProps {
  draftId: number;
  defaultTitle: string;
  defaultDescription: string;
  defaultTags: string[];
  open: boolean;
  onClose: () => void;
  onUploaded: (youtubeUrl: string) => void;
}

export function UploadDialog({
  draftId,
  defaultTitle,
  defaultDescription,
  defaultTags,
  open,
  onClose,
  onUploaded,
}: UploadDialogProps) {
  const [title, setTitle] = useState(defaultTitle);
  const [description, setDescription] = useState(defaultDescription);
  const [tags, setTags] = useState(defaultTags.join(", "));
  const [scheduled, setScheduled] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  if (!open) return null;

  // FR-029 검증: NATV 출처 + 팩트 링크 ≥2개
  const hasNatvLabel = description.includes("NATV 국회방송");
  const urlMatches = description.match(/https?:\/\/[^\s\n]+/g) || [];
  const factLinksOk = urlMatches.length >= 2;
  const canUpload = confirmed && hasNatvLabel && factLinksOk && title.trim().length > 0;

  const doUpload = async () => {
    if (!canUpload) return;
    setUploading(true);
    setError("");
    try {
      const res = await fetch(`/api/dem-shorts/drafts/${draftId}/upload`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          description,
          tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
          scheduled_publish_at: scheduled || null,
          operator_confirmed: true,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || `HTTP ${res.status}`);
      }
      onUploaded(data.youtube_url);
      onClose();
    } catch (e: any) {
      setError(e.message || "업로드 실패");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "#fff",
          borderRadius: 8,
          padding: 24,
          width: "90%",
          maxWidth: 720,
          maxHeight: "90vh",
          overflow: "auto",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 style={{ margin: "0 0 16px 0" }}>YouTube 최종 업로드</h2>

        <label style={{ display: "block", marginBottom: 12 }}>
          제목 ({title.length}/100)
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value.slice(0, 100))}
            style={{ width: "100%", padding: 8, marginTop: 4 }}
          />
        </label>

        <label style={{ display: "block", marginBottom: 12 }}>
          설명 (NATV 출처 + 팩트 링크 2개 필수)
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={10}
            style={{ width: "100%", padding: 8, marginTop: 4, fontFamily: "monospace", fontSize: 13 }}
          />
          <div style={{ fontSize: 12, marginTop: 4 }}>
            <span style={{ color: hasNatvLabel ? "#090" : "#c00" }}>
              {hasNatvLabel ? "✅" : "❌"} "NATV 국회방송" 포함
            </span>
            {" · "}
            <span style={{ color: factLinksOk ? "#090" : "#c00" }}>
              {factLinksOk ? "✅" : "❌"} 팩트 링크 {urlMatches.length}/2개
            </span>
          </div>
        </label>

        <label style={{ display: "block", marginBottom: 12 }}>
          태그 (쉼표 구분)
          <input
            type="text"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            style={{ width: "100%", padding: 8, marginTop: 4 }}
          />
        </label>

        <label style={{ display: "block", marginBottom: 16 }}>
          예약 공개 (선택, ISO 8601)
          <input
            type="datetime-local"
            value={scheduled}
            onChange={(e) => setScheduled(e.target.value)}
            style={{ padding: 8, marginTop: 4 }}
          />
        </label>

        <label style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, padding: 10, background: "#fff3e0", borderRadius: 4 }}>
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
          />
          <span>⚠️ 위 내용을 최종 확인했고 YouTube에 공개합니다 (FR-037)</span>
        </label>

        {error && <div style={{ color: "#c00", marginBottom: 12 }}>{error}</div>}

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button
            onClick={onClose}
            disabled={uploading}
            style={{ padding: "8px 20px", background: "#999", color: "#fff", border: "none", borderRadius: 4 }}
          >
            취소
          </button>
          <button
            onClick={doUpload}
            disabled={!canUpload || uploading}
            style={{
              padding: "8px 20px",
              background: canUpload ? "#cc0000" : "#ccc",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              cursor: canUpload ? "pointer" : "not-allowed",
            }}
          >
            {uploading ? "업로드 중..." : "🚀 업로드"}
          </button>
        </div>
      </div>
    </div>
  );
}
