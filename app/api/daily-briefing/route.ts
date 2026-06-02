import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import { readFileSync, existsSync } from "fs";
import path from "path";

const ROOT = process.cwd();
const BRIEFING_DIR = path.join(ROOT, "data", "daily_briefing");

// Up to 10 min — collection + clustering + 5 issues * (transcript + 3-plan Claude)
export const maxDuration = 600;

/**
 * GET /api/daily-briefing?date=YYYY-MM-DD
 * 저장된 브리핑 결과 로드. date 미지정 시 가장 최근.
 */
export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  let date = url.searchParams.get("date");

  if (!date) {
    // 가장 최근 브리핑 디렉토리 찾기
    if (!existsSync(BRIEFING_DIR)) {
      return NextResponse.json({ error: "no briefing yet" }, { status: 404 });
    }
    const { readdirSync } = await import("fs");
    const dates = readdirSync(BRIEFING_DIR)
      .filter((d) => /^\d{4}-\d{2}-\d{2}$/.test(d))
      .sort()
      .reverse();
    if (dates.length === 0) {
      return NextResponse.json({ error: "no briefing yet" }, { status: 404 });
    }
    date = dates[0];
  }

  const issuesPath = path.join(BRIEFING_DIR, date, "issues.json");
  if (!existsSync(issuesPath)) {
    return NextResponse.json({ error: `not found: ${date}` }, { status: 404 });
  }

  const data = JSON.parse(readFileSync(issuesPath, "utf-8"));

  // plans 디렉토리도 함께 — 각 rank의 plans.json 또는 manual_required.json 첨부
  const plansDir = path.join(BRIEFING_DIR, date, "plans");
  const plansByRank: Record<number, unknown> = {};
  if (existsSync(plansDir)) {
    const { readdirSync, statSync } = await import("fs");
    for (const entry of readdirSync(plansDir)) {
      const m = entry.match(/^(\d{2})/);
      if (!m) continue;
      const rank = parseInt(m[1], 10);
      const full = path.join(plansDir, entry);
      const stat = statSync(full);
      if (stat.isFile() && entry.endsWith(".json")) {
        plansByRank[rank] = JSON.parse(readFileSync(full, "utf-8"));
      } else if (stat.isDirectory()) {
        const plansFile = path.join(full, "plans.json");
        if (existsSync(plansFile)) {
          plansByRank[rank] = JSON.parse(readFileSync(plansFile, "utf-8"));
        }
      }
    }
  }

  return NextResponse.json({ briefing: data, plans_by_rank: plansByRank });
}

/**
 * POST /api/daily-briefing { top?: number, date?: string }
 * 새 브리핑 실행. Python 서브프로세스로 cmd_daily_briefing 호출.
 */
export async function POST(req: NextRequest) {
  let top = 5;
  let date: string | undefined;
  try {
    const body = await req.json();
    if (typeof body.top === "number") top = body.top;
    if (typeof body.date === "string") date = body.date;
  } catch {
    // body 없음 — default 사용
  }

  const args = ["-m", "src.main", "daily-briefing", "--top", String(top)];
  if (date) args.push("--date", date);

  return new Promise<NextResponse>((resolve) => {
    const p = spawn("python3", args, { cwd: ROOT, env: { ...process.env } });
    let stdout = "", stderr = "";
    p.stdout.on("data", (d) => { stdout += d; });
    p.stderr.on("data", (d) => { stderr += d; });
    p.on("close", (code) => {
      if (code !== 0) {
        resolve(NextResponse.json(
          { error: stderr.slice(-2000) || `exit ${code}` },
          { status: 500 },
        ));
        return;
      }
      // 결과는 파일에 저장됨 — GET을 다시 호출하지 않고 stderr 진행 로그만 반환
      resolve(NextResponse.json({
        ok: true,
        log: stderr.slice(-2000),
      }));
    });
  });
}
