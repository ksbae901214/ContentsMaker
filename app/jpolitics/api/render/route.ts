import { NextRequest, NextResponse } from "next/server";
import { writeFile, readFile, mkdir } from "fs/promises";
import { spawn } from "child_process";
import path from "path";
import { existsSync } from "fs";

const ROOT = process.cwd();
export const maxDuration = 600;

function runJpoliticsCli(args: string[]): Promise<{ stdout: string; stderr: string; code: number }> {
  return new Promise((resolve) => {
    const p = spawn("python3", ["-m", "src.jpolitics.main", ...args], {
      cwd: ROOT,
      env: { ...process.env },
    });
    let stdout = "";
    let stderr = "";
    p.stdout.on("data", (d) => {
      stdout += d.toString();
    });
    p.stderr.on("data", (d) => {
      stderr += d.toString();
    });
    p.on("close", (code) => {
      resolve({ stdout, stderr, code: code ?? -1 });
    });
    p.on("error", (e) => {
      resolve({ stdout: "", stderr: e.message, code: -1 });
    });
  });
}

/**
 * POST /api/jpolitics/render
 *
 * Body: { outputDir, selectedPlanRank: 1|2|3, scriptOverrides?: Partial<Plan> }
 *
 * Response 200: { ok, videoPath, videoDurationSec, summary }
 */
export async function POST(req: NextRequest) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json(
      { ok: false, error: "invalid_input", message: "Invalid JSON body" },
      { status: 400 }
    );
  }

  const b = body as {
    outputDir?: string;
    selectedPlanRank?: number;
    scriptOverrides?: Record<string, unknown>;
  };

  if (!b.outputDir || !b.selectedPlanRank || ![1, 2, 3].includes(b.selectedPlanRank)) {
    return NextResponse.json(
      {
        ok: false,
        error: "invalid_input",
        message: "outputDir and selectedPlanRank (1/2/3) required",
      },
      { status: 400 }
    );
  }

  const outputDirAbs = path.isAbsolute(b.outputDir)
    ? b.outputDir
    : path.join(ROOT, b.outputDir);

  if (!existsSync(outputDirAbs)) {
    return NextResponse.json(
      {
        ok: false,
        error: "plans_not_found",
        message: `outputDir does not exist: ${b.outputDir}`,
      },
      { status: 404 }
    );
  }

  // 사용자 검수 결과(overrides)를 script_overrides.json에 보존
  if (b.scriptOverrides) {
    const overridesPath = path.join(outputDirAbs, "script_overrides.json");
    await writeFile(
      overridesPath,
      JSON.stringify(b.scriptOverrides, null, 2),
      "utf-8"
    );
  }

  // CLI 호출 (전체 파이프라인 — 후속 T041에서 통합 강화)
  const { stdout, stderr, code } = await runJpoliticsCli([
    "--render-only",
    "--script-file",
    path.join(outputDirAbs, "plans.json"),
    "--select-plan",
    String(b.selectedPlanRank),
    "--output-dir",
    outputDirAbs,
  ]);

  // 현재 main.py는 full pipeline 미지원 → 명시적 안내
  if (code !== 0) {
    return NextResponse.json(
      {
        ok: false,
        error: "render_failure",
        message: stderr.slice(-500) || `Python exit ${code}. Full render pipeline is integrated in T041; current API returns plan selection metadata.`,
      },
      { status: 500 }
    );
  }

  // summary.txt가 있으면 로드
  const summaryPath = path.join(outputDirAbs, "summary.txt");
  let summary: { lines: string[]; hashtags: string[] } | undefined;
  if (existsSync(summaryPath)) {
    try {
      const text = await readFile(summaryPath, "utf-8");
      const json = JSON.parse(text) as { lines: string[]; hashtags: string[] };
      summary = json;
    } catch {
      // ignore
    }
  }

  return NextResponse.json({
    ok: true,
    videoPath: path.join(outputDirAbs, "video.mp4"),
    videoDurationSec: 60,
    summary,
  });
}
