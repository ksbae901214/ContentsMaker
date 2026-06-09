import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import { readFile } from "fs/promises";
import path from "path";

const ROOT = process.cwd();

// V3 plans: Gemini + Claude × 3 ≈ 60~120s
export const maxDuration = 600;

function isValidYouTubeUrl(u: string): boolean {
  try {
    const parsed = new URL(u);
    const host = parsed.hostname.toLowerCase();
    return (
      host === "www.youtube.com" ||
      host === "youtube.com" ||
      host === "m.youtube.com" ||
      host === "youtu.be"
    );
  } catch {
    return false;
  }
}

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
 * POST /api/jpolitics/plans
 *
 * Body:
 *   - { sourceType: "youtube", youtubeUrl, videoTitle? }
 *   - { sourceType: "topic", topic, tone?, details? }
 *
 * Response 200:
 *   { ok: true, outputDir, videoTitle, videoDurationSec, plans: JpoliticsPlan[] }
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
    sourceType?: string;
    youtubeUrl?: string;
    videoTitle?: string;
    topic?: string;
    tone?: string;
    details?: string;
  };

  const args: string[] = ["--plans-only"];
  if (b.sourceType === "topic") {
    if (!b.topic) {
      return NextResponse.json(
        { ok: false, error: "invalid_input", message: "topic is required for topic mode" },
        { status: 400 }
      );
    }
    args.push("--source-type", "topic", "--topic", b.topic);
    if (b.tone) args.push("--tone", b.tone);
    if (b.details) args.push("--details", b.details);
  } else {
    if (!b.youtubeUrl || !isValidYouTubeUrl(b.youtubeUrl)) {
      return NextResponse.json(
        { ok: false, error: "invalid_input", message: "Valid YouTube URL required" },
        { status: 400 }
      );
    }
    args.push(b.youtubeUrl);
    if (b.videoTitle) args.push("--video-title", b.videoTitle);
  }

  const { stdout, stderr, code } = await runJpoliticsCli(args);
  if (code !== 0) {
    const errMsg = stderr.slice(-500) || `Python exited with ${code}`;
    return NextResponse.json(
      { ok: false, error: "planner_failure", message: errMsg },
      { status: 500 }
    );
  }

  // 마지막 줄 = JSON {ok, outputDir}
  const lines = stdout.trim().split("\n");
  const lastLine = lines[lines.length - 1];
  let cliResult: { ok: boolean; outputDir?: string; error?: string };
  try {
    cliResult = JSON.parse(lastLine);
  } catch {
    return NextResponse.json(
      { ok: false, error: "planner_failure", message: `Invalid CLI output: ${lastLine.slice(0, 200)}` },
      { status: 500 }
    );
  }

  if (!cliResult.ok || !cliResult.outputDir) {
    return NextResponse.json(
      { ok: false, error: "planner_failure", message: cliResult.error || "Unknown error" },
      { status: 500 }
    );
  }

  // plans.json 로드
  const plansPath = path.join(ROOT, cliResult.outputDir, "plans.json");
  try {
    const plansRaw = await readFile(plansPath, "utf-8");
    const plansData = JSON.parse(plansRaw) as {
      plans: unknown[];
      video_title?: string;
      video_duration_sec?: number;
    };
    return NextResponse.json({
      ok: true,
      outputDir: cliResult.outputDir,
      videoTitle: plansData.video_title,
      videoDurationSec: plansData.video_duration_sec,
      plans: plansData.plans,
    });
  } catch (e) {
    return NextResponse.json(
      {
        ok: false,
        error: "planner_failure",
        message: `Failed to read plans.json: ${String(e)}`,
      },
      { status: 500 }
    );
  }
}
