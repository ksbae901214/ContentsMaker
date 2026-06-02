// T060: Whitelist 관리 UI — 정치인 CRUD + 등급/카테고리 편집 (FR-007, FR-011)
// tier='auto'는 랭킹 배치 전용 — UI에서 직접 설정 금지 (FR-009).
"use client";

import { useCallback, useEffect, useState } from "react";

type Tier = "pinned" | "auto" | "pending" | "blocked";
type Category = "fixed" | "female" | "youth" | "alliance";

interface Politician {
  id: number;
  name: string;
  party: string;
  role: string;
  bio: string;
  tone_guide: string;
  tier: Tier;
  category: Category;
  is_active: boolean;
  ranking_score: number | null;
}

const MANUAL_TIERS: Tier[] = ["pinned", "pending", "blocked"];
const CATEGORIES: Category[] = ["fixed", "female", "youth", "alliance"];

const TIER_LABEL: Record<Tier, string> = {
  pinned: "📌 고정",
  auto: "🤖 자동 (랭킹 배치)",
  pending: "⏳ 보류",
  blocked: "🚫 차단",
};
const CATEGORY_LABEL: Record<Category, string> = {
  fixed: "고정 인물",
  female: "여성",
  youth: "청년",
  alliance: "연합 (조국혁신당 등)",
};

export default function WhitelistPage() {
  const [politicians, setPoliticians] = useState<Politician[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterTier, setFilterTier] = useState<Tier | "">("");
  const [filterCategory, setFilterCategory] = useState<Category | "">("");

  const [showForm, setShowForm] = useState(false);
  const [newPolitician, setNewPolitician] = useState({
    name: "",
    party: "더불어민주당",
    role: "국회의원",
    tier: "pending" as Tier,
    category: "fixed" as Category,
    bio: "",
    tone_guide: "",
  });

  const fetchList = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (filterTier) params.set("tier", filterTier);
      if (filterCategory) params.set("category", filterCategory);
      const res = await fetch(`/api/dem-shorts/whitelist?${params}`);
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.error || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setPoliticians(data.politicians || []);
    } catch (e: any) {
      setError(e.message || "조회 실패");
    } finally {
      setLoading(false);
    }
  }, [filterTier, filterCategory]);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPolitician.name.trim()) {
      setError("이름을 입력하세요");
      return;
    }
    try {
      const res = await fetch("/api/dem-shorts/whitelist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newPolitician),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.error || `HTTP ${res.status}`);
      }
      setShowForm(false);
      setNewPolitician({
        name: "",
        party: "더불어민주당",
        role: "국회의원",
        tier: "pending",
        category: "fixed",
        bio: "",
        tone_guide: "",
      });
      fetchList();
    } catch (e: any) {
      setError(e.message || "등록 실패");
    }
  };

  const handleUpdate = async (id: number, patch: Partial<Politician>) => {
    try {
      const res = await fetch(`/api/dem-shorts/whitelist/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.error || `HTTP ${res.status}`);
      }
      fetchList();
    } catch (e: any) {
      setError(e.message || "업데이트 실패");
    }
  };

  const handleDelete = async (p: Politician) => {
    const warning = p.tier === "pinned"
      ? `📌 고정 등급 '${p.name}'를 삭제하시겠습니까? 고정 인물은 주간 목표 분포에 영향을 줍니다.`
      : `'${p.name}'를 삭제하시겠습니까?`;
    if (!confirm(warning)) return;
    try {
      const res = await fetch(`/api/dem-shorts/whitelist/${p.id}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.error || `HTTP ${res.status}`);
      }
      fetchList();
    } catch (e: any) {
      setError(e.message || "삭제 실패");
    }
  };

  return (
    <main style={{ maxWidth: 1100, margin: "0 auto", padding: "24px 16px" }}>
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, margin: 0 }}>
          Whitelist 정치인 관리
        </h1>
        <p style={{ color: "#666", marginTop: 4 }}>
          총 {politicians.length}명 — 📌 고정/🤖 자동(랭킹 배치)/⏳ 보류/🚫 차단
        </p>
        <p style={{ color: "#999", fontSize: 13, marginTop: 4 }}>
          ⚠️ auto 등급은 주간 랭킹 배치 결과로만 설정됩니다 (FR-009).
        </p>
      </header>

      {/* 필터 + 추가 버튼 */}
      <div style={{ display: "flex", gap: 12, marginBottom: 16, alignItems: "center", flexWrap: "wrap" }}>
        <select
          value={filterTier}
          onChange={(e) => setFilterTier(e.target.value as Tier | "")}
          style={{ padding: 6, borderRadius: 4 }}
        >
          <option value="">전체 등급</option>
          <option value="pinned">📌 고정</option>
          <option value="auto">🤖 자동</option>
          <option value="pending">⏳ 보류</option>
          <option value="blocked">🚫 차단</option>
        </select>
        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value as Category | "")}
          style={{ padding: 6, borderRadius: 4 }}
        >
          <option value="">전체 카테고리</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>{CATEGORY_LABEL[c]}</option>
          ))}
        </select>
        <button
          onClick={() => setShowForm((v) => !v)}
          style={{
            padding: "6px 14px",
            background: showForm ? "#ccc" : "#0066cc",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            cursor: "pointer",
          }}
        >
          {showForm ? "취소" : "+ 추가"}
        </button>
      </div>

      {/* 추가 폼 */}
      {showForm && (
        <form
          onSubmit={handleCreate}
          style={{
            background: "#f7f7f7",
            padding: 16,
            borderRadius: 8,
            marginBottom: 16,
            display: "grid",
            gridTemplateColumns: "repeat(2, 1fr)",
            gap: 12,
          }}
        >
          <label>이름
            <input
              type="text"
              value={newPolitician.name}
              onChange={(e) => setNewPolitician({ ...newPolitician, name: e.target.value })}
              required
              style={{ width: "100%", padding: 6, marginTop: 4 }}
            />
          </label>
          <label>정당
            <input
              type="text"
              value={newPolitician.party}
              onChange={(e) => setNewPolitician({ ...newPolitician, party: e.target.value })}
              style={{ width: "100%", padding: 6, marginTop: 4 }}
            />
          </label>
          <label>직책
            <input
              type="text"
              value={newPolitician.role}
              onChange={(e) => setNewPolitician({ ...newPolitician, role: e.target.value })}
              style={{ width: "100%", padding: 6, marginTop: 4 }}
            />
          </label>
          <label>등급 (auto는 배치 전용)
            <select
              value={newPolitician.tier}
              onChange={(e) => setNewPolitician({ ...newPolitician, tier: e.target.value as Tier })}
              style={{ width: "100%", padding: 6, marginTop: 4 }}
            >
              {MANUAL_TIERS.map((t) => (
                <option key={t} value={t}>{TIER_LABEL[t]}</option>
              ))}
            </select>
          </label>
          <label>카테고리
            <select
              value={newPolitician.category}
              onChange={(e) => setNewPolitician({ ...newPolitician, category: e.target.value as Category })}
              style={{ width: "100%", padding: 6, marginTop: 4 }}
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{CATEGORY_LABEL[c]}</option>
              ))}
            </select>
          </label>
          <label style={{ gridColumn: "1 / -1" }}>대표 이력
            <textarea
              value={newPolitician.bio}
              onChange={(e) => setNewPolitician({ ...newPolitician, bio: e.target.value })}
              style={{ width: "100%", padding: 6, marginTop: 4, minHeight: 60 }}
            />
          </label>
          <label style={{ gridColumn: "1 / -1" }}>톤앤매너 가이드
            <textarea
              value={newPolitician.tone_guide}
              onChange={(e) => setNewPolitician({ ...newPolitician, tone_guide: e.target.value })}
              style={{ width: "100%", padding: 6, marginTop: 4, minHeight: 60 }}
            />
          </label>
          <div style={{ gridColumn: "1 / -1" }}>
            <button
              type="submit"
              style={{ padding: "8px 20px", background: "#009900", color: "#fff", border: "none", borderRadius: 4 }}
            >
              등록
            </button>
          </div>
        </form>
      )}

      {error && (
        <div style={{ background: "#fee", border: "1px solid #f99", color: "#900", padding: 10, borderRadius: 4, marginBottom: 12 }}>
          {error}
        </div>
      )}
      {loading && <p>로딩 중...</p>}

      {/* 정치인 목록 */}
      <div style={{ display: "grid", gap: 8 }}>
        {politicians.map((p) => (
          <div
            key={p.id}
            style={{
              background: "#fff",
              border: "1px solid #e0e0e0",
              borderRadius: 6,
              padding: 12,
              display: "grid",
              gridTemplateColumns: "2fr 1fr 1fr auto auto",
              gap: 12,
              alignItems: "center",
            }}
          >
            <div>
              <div style={{ fontWeight: 600 }}>
                {p.name}
                {!p.is_active && <span style={{ color: "#999", fontSize: 12 }}> (비활성)</span>}
              </div>
              <div style={{ color: "#666", fontSize: 13 }}>{p.party} · {p.role}</div>
            </div>
            <select
              value={p.tier}
              onChange={(e) => handleUpdate(p.id, { tier: e.target.value as Tier })}
              style={{ padding: 4 }}
              disabled={p.tier === "auto"}
              title={p.tier === "auto" ? "auto 등급은 배치로만 변경됩니다" : ""}
            >
              {p.tier === "auto" && <option value="auto">🤖 자동 (배치)</option>}
              {MANUAL_TIERS.map((t) => (
                <option key={t} value={t}>{TIER_LABEL[t]}</option>
              ))}
            </select>
            <select
              value={p.category}
              onChange={(e) => handleUpdate(p.id, { category: e.target.value as Category })}
              style={{ padding: 4 }}
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{CATEGORY_LABEL[c]}</option>
              ))}
            </select>
            <label style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 4 }}>
              <input
                type="checkbox"
                checked={p.is_active}
                onChange={(e) => handleUpdate(p.id, { is_active: e.target.checked })}
              />
              활성
            </label>
            <button
              onClick={() => handleDelete(p)}
              style={{ padding: "4px 10px", background: "#cc0000", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}
            >
              삭제
            </button>
          </div>
        ))}
      </div>

      {politicians.length === 0 && !loading && (
        <p style={{ textAlign: "center", color: "#999", padding: 40 }}>
          조건에 맞는 정치인이 없습니다.
        </p>
      )}
    </main>
  );
}
