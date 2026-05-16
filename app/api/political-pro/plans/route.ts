import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";

const ROOT = process.cwd();

// Up to 5 min: download (~90s) + transcribe (~60s) + Claude 3-plan (~120s)
export const maxDuration = 600;

function py(code: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const p = spawn("python3", ["-c", code], { cwd: ROOT, env: { ...process.env } });
    let out = "", err = "";
    p.stdout.on("data", d => { out += d; });
    p.stderr.on("data", d => { err += d; });
    p.on("close", c => {
      if (c !== 0) {
        reject(new Error(err.slice(-1000) || `exit ${c}`));
      } else {
        const lines = out.trim().split("\n");
        resolve(lines[lines.length - 1]);
      }
    });
    p.on("error", e => reject(new Error(`Python: ${e.message}`)));
  });
}

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

/**
 * POST /api/political-pro/plans
 *
 * Body: { youtubeUrl: string }
 * Response: { plans: ShortsPlan[], videoPath, videoDurationSec,
 *             transcriptPath, videoTitle, generatedAt }
 *
 * See specs/009-political-pro-planner/contracts/api-political-pro-plans.md
 */
export async function POST(req: NextRequest) {
  let body: { youtubeUrl?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json(
      { error: "invalid_request", detail: "JSON body required" },
      { status: 400 },
    );
  }

  const youtubeUrl = (body.youtubeUrl || "").trim();
  if (!youtubeUrl || !isValidYouTubeUrl(youtubeUrl)) {
    return NextResponse.json(
      { error: "invalid_url", detail: "YouTube URL이 아닙니다", youtubeUrl },
      { status: 400 },
    );
  }

  // Step 1: download video + transcript (VTT → Whisper fallback)
  const escUrl = JSON.stringify(youtubeUrl);
  let dl: any;
  try {
    const raw = await py(`
import sys, json
sys.path.insert(0, '${ROOT}')
from pathlib import Path
from datetime import datetime
from src.config.settings import DATA_DIR
from src.scraper.youtube_downloader import (
    download_video, transcribe_video_or_fallback, TranscriptUnavailableError,
    get_video_metadata,
)
url = ${escUrl}
ts = datetime.now().strftime('%Y%m%d_%H%M%S')
out_dir = DATA_DIR / 'political_pro' / f'{ts}_session'
out_dir.mkdir(parents=True, exist_ok=True)
# Fetch real title + channel BEFORE download (for source attribution)
meta = get_video_metadata(url)
try:
    vp = download_video(url, out_dir)
except Exception as e:
    print(json.dumps({"error": "youtube_download_failed", "detail": str(e)[:300]}))
    sys.exit(0)
try:
    transcript = transcribe_video_or_fallback(url=url, video_path=vp, out_dir=out_dir)
except TranscriptUnavailableError as e:
    print(json.dumps({"error": "transcript_unavailable", "detail": str(e)[:300]}))
    sys.exit(0)
if not transcript:
    print(json.dumps({"error": "empty_transcript", "detail": "transcript 비어 있음"}))
    sys.exit(0)
import subprocess
probe = subprocess.run(
    ["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1", str(vp)],
    capture_output=True, text=True,
)
try:
    duration = float(probe.stdout.strip())
except Exception:
    duration = transcript[-1]["end"] if transcript else (meta.get("duration_sec") or 0.0)
# Save transcript JSON for traceability
tp = out_dir / 'transcript.json'
tp.write_text(json.dumps({"segments": transcript}, ensure_ascii=False, indent=2), encoding="utf-8")
# 출처 표시용: yt-dlp 메타데이터의 channel + title (없으면 video_id 폴백)
title = (meta.get("title") or "").strip() or vp.stem
channel = (meta.get("channel") or "").strip()
print(json.dumps({
  "videoPath": str(vp),
  "transcriptPath": str(tp),
  "videoDurationSec": duration,
  "videoTitle": title,
  "videoChannel": channel,
  "outDir": str(out_dir),
  "transcript": transcript,
}, ensure_ascii=False))
`);
    dl = JSON.parse(raw);
  } catch (e: any) {
    return NextResponse.json(
      { error: "youtube_download_failed", detail: (e?.message || String(e)).slice(0, 500), youtubeUrl },
      { status: 502 },
    );
  }

  if (dl.error === "transcript_unavailable") {
    return NextResponse.json(
      { error: "transcript_unavailable", detail: dl.detail, youtubeUrl },
      { status: 422 },
    );
  }
  if (dl.error === "empty_transcript") {
    return NextResponse.json(
      { error: "empty_transcript", detail: dl.detail, youtubeUrl },
      { status: 422 },
    );
  }
  if (dl.error === "youtube_download_failed") {
    return NextResponse.json(
      { error: "youtube_download_failed", detail: dl.detail, youtubeUrl },
      { status: 502 },
    );
  }

  // Step 2: generate 3 plans
  const escTranscript = JSON.stringify(JSON.stringify(dl.transcript));
  const escTitle = JSON.stringify(dl.videoTitle);
  const escChannel = JSON.stringify(dl.videoChannel || "");
  const escVideoPath = JSON.stringify(dl.videoPath);
  const escTranscriptPath = JSON.stringify(dl.transcriptPath);
  const escOutDir = JSON.stringify(dl.outDir);
  try {
    const raw = await py(`
import sys, json
sys.path.insert(0, '${ROOT}')
from pathlib import Path
from src.analyzer.political_planner import generate_three_plans, PoliticalPlannerError
transcript = json.loads(${escTranscript})
try:
    result = generate_three_plans(
        youtube_url=${escUrl},
        transcript=transcript,
        video_title=${escTitle},
        video_duration_sec=${dl.videoDurationSec},
        video_path=${escVideoPath},
        transcript_path=${escTranscriptPath},
        output_dir=Path(${escOutDir}),
        video_channel=${escChannel},
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
except PoliticalPlannerError as e:
    print(json.dumps({"error": "claude_plan_generation_failed", "detail": str(e)[:400]}))
`);
    const parsed = JSON.parse(raw);
    if (parsed.error === "claude_plan_generation_failed") {
      return NextResponse.json(
        { error: parsed.error, detail: parsed.detail, youtubeUrl },
        { status: 502 },
      );
    }
    return NextResponse.json(parsed, { status: 200 });
  } catch (e: any) {
    return NextResponse.json(
      {
        error: "claude_plan_generation_failed",
        detail: (e?.message || String(e)).slice(0, 500),
        youtubeUrl,
      },
      { status: 502 },
    );
  }
}
