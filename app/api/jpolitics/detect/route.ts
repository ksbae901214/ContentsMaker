import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";

const ROOT = process.cwd();

// download (~90s) + Gemini multimodal detect (~120s) + transcript fallback (~60s)
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

function runScript(args: string[]): Promise<string> {
  return new Promise((resolve, reject) => {
    const p = spawn("python3", args, { cwd: ROOT, env: { ...process.env } });
    let out = "";
    let err = "";
    p.stdout.on("data", (d) => { out += d; });
    p.stderr.on("data", (d) => { err += d; });
    p.on("close", (code) => {
      if (code !== 0) {
        reject(new Error(err.slice(-1000) || `exit ${code}`));
      } else {
        const lines = out.trim().split("\n");
        resolve(lines[lines.length - 1]);
      }
    });
    p.on("error", (e) => reject(new Error(`Python: ${e.message}`)));
  });
}

/**
 * POST /api/jpolitics/detect
 *
 * Body: { url: string, noMultimodal?: boolean }
 * Response: { workDir, moments, channel, videoTitle }
 */
export async function POST(req: NextRequest) {
  let body: { url?: string; noMultimodal?: boolean };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json(
      { error: "invalid_request", detail: "JSON body required" },
      { status: 400 },
    );
  }

  const url = (body.url || "").trim();
  if (!url || !isValidYouTubeUrl(url)) {
    return NextResponse.json(
      { error: "invalid_url", detail: "YouTube URL이 아닙니다", url },
      { status: 400 },
    );
  }

  const scriptArgs = ["-m", "src.jpolitics.main", "detect", url];
  if (body.noMultimodal) {
    scriptArgs.push("--no-multimodal");
  }

  // We need to capture the full stdout (progress lines are on stderr, JSON summary on stdout)
  // The main.py writes progress to stderr and returns 0 on success.
  // We call via python -c to capture the work_dir path from moments.json output.
  const pyCode = `
import sys, json, subprocess, os
sys.path.insert(0, '${ROOT}')
from pathlib import Path
from datetime import datetime
import re

url = ${JSON.stringify(url)}
no_multimodal = ${body.noMultimodal ? "True" : "False"}

from src.jpolitics.constants import JPOLITICS_DATA_DIR
from src.scraper.youtube_downloader import (
    download_video,
    get_video_metadata,
    transcribe_video_or_fallback,
    TranscriptUnavailableError,
)
from src.jpolitics.analyzer.moment_detector import (
    MomentDetectError,
    detect_moments_from_transcript,
    detect_moments_from_video,
)
from src.jpolitics.models.moment import MomentDetectionResult

def slugify(title, max_len=24):
    slug = re.sub(r'[^\\w가-힣]+', '_', title).strip('_')
    return slug[:max_len] or 'video'

try:
    meta = get_video_metadata(url)
except Exception as e:
    print(json.dumps({"error": "metadata_failed", "detail": str(e)[:300]}))
    sys.exit(0)

title = meta.get("title") or "untitled"
channel = meta.get("channel") or meta.get("uploader") or ""
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
work_dir = JPOLITICS_DATA_DIR / f"{ts}_{slugify(title)}"
work_dir.mkdir(parents=True, exist_ok=True)

try:
    video_path = download_video(url, work_dir)
except Exception as e:
    print(json.dumps({"error": "download_failed", "detail": str(e)[:300]}))
    sys.exit(0)

moments = []
detector = ""
if not no_multimodal:
    try:
        moments = detect_moments_from_video(video_path)
        detector = "gemini_multimodal"
    except MomentDetectError:
        pass

if not moments:
    try:
        segments = transcribe_video_or_fallback(url=url, video_path=video_path, out_dir=work_dir)
    except TranscriptUnavailableError as e:
        print(json.dumps({"error": "transcript_failed", "detail": str(e)[:300]}))
        sys.exit(0)
    try:
        moments = detect_moments_from_transcript(segments)
        detector = "transcript"
    except MomentDetectError as e:
        print(json.dumps({"error": "detect_failed", "detail": str(e)[:300]}))
        sys.exit(0)

result = MomentDetectionResult(
    source_url=url,
    video_title=title,
    channel=channel,
    detector=detector,
    moments=tuple(moments),
)
result.save(work_dir / "moments.json")

top = list(result.top(5))
print(json.dumps({
    "workDir": str(work_dir),
    "videoTitle": title,
    "channel": channel,
    "detector": detector,
    "moments": [m.to_dict() for m in top],
}, ensure_ascii=False))
`;

  try {
    const raw = await runScript(["-c", pyCode]);
    const parsed = JSON.parse(raw);
    if (parsed.error) {
      return NextResponse.json(
        { error: parsed.error, detail: parsed.detail, url },
        { status: 502 },
      );
    }
    return NextResponse.json(parsed, { status: 200 });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json(
      { error: "detect_failed", detail: msg.slice(0, 500), url },
      { status: 502 },
    );
  }
}
