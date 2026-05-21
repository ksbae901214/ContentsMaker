import { NextRequest } from "next/server";
import { spawn } from "child_process";
import { writeFile, mkdir } from "fs/promises";
import { join } from "path";
import { v4 as uuid } from "uuid";

const ROOT = process.cwd();
// Next.js Route Handler max duration. The full pipeline can take a LONG time:
//   - Claude CLI 분석 (5~10분)
//   - Freepik 이미지 6장 생성 (각 30~120초 = 3~12분)
//   - Kling 2.5 영상 6개 생성 (각 60~120초 = 6~12분)
//   - Remotion 렌더 (1~2분)
// 총합: 30~40분 정도 걸릴 수 있어 3600초 (60분)로 설정.
export const maxDuration = 3600;

// Format seconds as "Xm Ys" / "Xs" for progress messages.
function fmtTime(sec: number): string {
  if (sec < 60) return `${sec}초`;
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return s > 0 ? `${m}분 ${s}초` : `${m}분`;
}

function py(code: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const p = spawn("python3", ["-c", code], { cwd: ROOT, env: { ...process.env } });
    let out = "", err = "";
    p.stdout.on("data", d => { out += d; });
    p.stderr.on("data", d => { err += d; });
    p.on("close", c => { if (c !== 0) reject(new Error(err.slice(-500)||`exit ${c}`)); else { const l = out.trim().split("\n"); resolve(l[l.length-1]); } });
    p.on("error", e => reject(new Error(`Python: ${e.message}`)));
  });
}

export async function POST(req: NextRequest) {
  const fd = await req.formData();
  const mode = fd.get("mode") as string;
  const useBgm = (fd.get("bgm") as string) !== "off";
  // Default on: only explicit "off" disables scene transitions / SFX.
  const useTransitions = (fd.get("transitions") as string) !== "off";
  const useSfx = (fd.get("sfx") as string) !== "off";
  // Feature 009 — FR-020: political_pro mode (and Phase 2 with politicalProMeta)
  // MUST never auto-upload, even if the client misbehaves.
  const _isPoliticalPro = (fd.get("mode") as string) === "political_pro"
    || !!(fd.get("politicalProMeta") as string);
  const useYt = !_isPoliticalPro && (fd.get("yt") as string) === "on";
  const useTt = !_isPoliticalPro && (fd.get("tt") as string) === "on";
  const dryRun = (fd.get("dryRun") as string) === "on";
  const customTitle = (fd.get("customTitle") as string) || "";
  // 2-phase flow support:
  //  - stopAfter="analyze": run until Claude analysis completes, then emit
  //    "done" with the script data so the UI can show a review screen.
  //  - mode="script": skip all input-capture + analyze stages, use an
  //    existing scriptPath (from the prior analyze phase). Downstream
  //    (image/video/TTS/render) proceeds normally.
  const stopAfter = (fd.get("stopAfter") as string) || "";
  const existingScriptPath = (fd.get("scriptPath") as string) || "";
  const enc = new TextEncoder();

  let _ctrlClosed = false;
  const stream = new ReadableStream({
    cancel() { _ctrlClosed = true; },
    async start(ctrl) {
      const send = (type: string, data: any) => {
        if (_ctrlClosed) return;
        try {
          ctrl.enqueue(enc.encode(`data: ${JSON.stringify({type,...data})}\n\n`));
        } catch { _ctrlClosed = true; }
      };

      // withStage wraps a long-running operation with:
      //  1. An initial "시작" message showing expected duration
      //  2. A 5-second heartbeat showing elapsed / remaining time — this
      //     keeps the SSE stream alive so browsers (esp. Safari) don't
      //     drop the fetch with "Load failed" during multi-minute operations.
      //  3. Error wrapping with the stage name + elapsed time so the user
      //     sees exactly which step failed.
      async function withStage<T>(name: string, expectedSec: number, fn: () => Promise<T>): Promise<T> {
        const start = Date.now();
        send("progress", {message: `⏳ [${name}] 시작 (예상 소요: ${fmtTime(expectedSec)})`});
        const interval = setInterval(() => {
          const elapsed = Math.floor((Date.now() - start) / 1000);
          const remaining = expectedSec - elapsed;
          const msg = remaining > 0
            ? `⏳ [${name}] 진행 중 · 경과 ${fmtTime(elapsed)} · 약 ${fmtTime(remaining)} 남음`
            : `⏳ [${name}] 진행 중 · 경과 ${fmtTime(elapsed)} · 예상 시간 초과, 계속 대기 중`;
          send("progress", {message: msg});
        }, 5000);
        try {
          return await fn();
        } catch (e: any) {
          const elapsed = Math.floor((Date.now() - start) / 1000);
          const orig = e?.message || String(e) || "알 수 없는 오류";
          throw new Error(`❌ [${name}] 실패 (${fmtTime(elapsed)} 경과): ${orig}`);
        } finally {
          clearInterval(interval);
        }
      }

      try {
        // ── Celebrity mode (Phase 9) ───────────────────────────────
        // This mode shells out to the `celebrity` CLI so the full orchestration
        // (namuwiki → Claude → naver → freepik → TTS → render) lives in one
        // place. Upload to YouTube/TikTok is intentionally disabled here —
        // this mode is学습-use-only and the underlying Naver images +
        // Namuwiki text have third-party rights.
        // 2-phase 지원 (2026-04-21):
        //   stopAfter=analyze + mode=celebrity → --analyze-only
        //   mode=script + celebritySource=on   → --from-script (편집된 script로 렌더)
        //   mode=celebrity (위 둘 아님)        → end-to-end (하위호환)
        const isCelebrityScript =
          mode === "script" && existingScriptPath && (fd.get("celebritySource") as string) === "on";
        if (mode === "celebrity" || isCelebrityScript) {
          const name = ((fd.get("celebrityName") as string) || "").trim();
          if (!name) {
            send("error", { message: "인물 이름을 입력하세요" });
            ctrl.close();
            return;
          }
          const noVideo = (fd.get("noVideo") as string) === "on";
          const noImages = (fd.get("noImages") as string) === "on";
          const symbolicImages = (fd.get("symbolicImages") as string) === "on";
          const analyzeOnly = stopAfter === "analyze" && mode === "celebrity";
          const qualifier = ((fd.get("celebrityQualifier") as string) || "").trim();
          const portraitPath = ((fd.get("portraitPath") as string) || "").trim();
          const sceneImagesJson = ((fd.get("sceneImagesJson") as string) || "").trim();

          // sceneImagesJson이 있으면 tempfile에 저장해서 CLI에 경로로 전달
          let sceneImagesJsonPath = "";
          if (sceneImagesJson) {
            const tmpDir = join(ROOT, "data", "tmp");
            await mkdir(tmpDir, { recursive: true });
            sceneImagesJsonPath = join(tmpDir, `scene_images_${uuid()}.json`);
            await writeFile(sceneImagesJsonPath, sceneImagesJson, "utf-8");
          }

          const args = ["-m", "src.main", "celebrity", name];
          if (qualifier) args.push("--qualifier", qualifier);
          if (analyzeOnly) args.push("--analyze-only");
          if (isCelebrityScript) args.push("--from-script", existingScriptPath);
          if (sceneImagesJsonPath) args.push("--scene-images-json", sceneImagesJsonPath);
          else if (portraitPath) args.push("--portrait-path", portraitPath);
          if (noVideo) args.push("--no-video");
          if (noImages) args.push("--no-images");
          if (symbolicImages) args.push("--symbolic-images");
          if (!useBgm) args.push("--no-bgm");
          if (!useTransitions) args.push("--no-transitions");
          if (!useSfx) args.push("--no-sfx");

          const phaseLabel = analyzeOnly
            ? `📝 Phase 1: 대본 생성 (씬 미리보기)`
            : isCelebrityScript
              ? `🎬 Phase 2: 편집된 대본으로 영상 렌더`
              : `🎬 유명인 end-to-end 파이프라인`;
          send("progress", { message: `${phaseLabel}: ${name}` });

          let videoOutputPath = "";
          let sourceUrl = "";
          let analyzeResult: any = null;
          let renderResult: any = null;

          await new Promise<void>((resolve, reject) => {
            const p = spawn("python3", ["-u", ...args], { cwd: ROOT, env: { ...process.env, PYTHONUNBUFFERED: "1" } });
            // Heartbeat: Freepik 영상 변환 등 Python 침묵 구간(60~120초)에
            // Safari가 SSE 스트림을 "Load failed"로 끊지 않도록 5초마다 진행 메시지 전송
            const pStart = Date.now();
            const heartbeat = setInterval(() => {
              const elapsed = Math.floor((Date.now() - pStart) / 1000);
              send("progress", { message: `⏳ [유명인 파이프라인] 진행 중 · 경과 ${fmtTime(elapsed)}` });
            }, 5000);
            let stdoutBuf = "";
            p.stdout.on("data", d => {
              stdoutBuf += d.toString();
              const lines = stdoutBuf.split("\n");
              stdoutBuf = lines.pop() ?? "";
              for (const line of lines) {
                const trimmed = line.trimEnd();
                if (!trimmed) continue;
                if (trimmed.startsWith("ANALYZE_DONE ")) {
                  try {
                    analyzeResult = JSON.parse(trimmed.slice("ANALYZE_DONE ".length));
                  } catch { /* ignore parse errors */ }
                  continue;
                }
                if (trimmed.startsWith("RENDER_DONE ")) {
                  try {
                    renderResult = JSON.parse(trimmed.slice("RENDER_DONE ".length));
                  } catch { /* ignore */ }
                  continue;
                }
                send("progress", { message: trimmed });
                const videoMatch = trimmed.match(/^\s*영상:\s*(.+)$/);
                if (videoMatch) videoOutputPath = videoMatch[1].trim();
                const sourceMatch = trimmed.match(/^\s*출처:\s*(https?:\/\/\S+)/);
                if (sourceMatch) sourceUrl = sourceMatch[1].trim();
              }
            });
            p.stderr.on("data", d => {
              const msg = d.toString().trim();
              if (msg) send("progress", { message: `⚠️ ${msg.slice(-300)}` });
            });
            p.on("close", c => {
              clearInterval(heartbeat);
              if (c === 0) resolve();
              else reject(new Error(`celebrity 파이프라인 실패 (exit ${c})`));
            });
            p.on("error", e => { clearInterval(heartbeat); reject(new Error(`Python 실행 실패: ${e.message}`)); });
          });

          // Phase 1 종료 → ScriptReviewer로 진입
          if (analyzeOnly && analyzeResult?.script_path) {
            const scriptRaw = JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
s=json.loads(Path('''${analyzeResult.script_path}''').read_text())
print(json.dumps({"scenes":s["scenes"]}))`));
            send("done", {
              result: {
                phase: "analyzed",
                title: analyzeResult.title,
                emotion: analyzeResult.emotion,
                duration: analyzeResult.duration,
                scriptPath: analyzeResult.script_path,
                scenes: scriptRaw.scenes,
                sourceType: "celebrity",
                celebrityName: name,
                sourceUrl: analyzeResult.source_url,
                portraitCandidates: analyzeResult.portrait_candidates || [],
                sceneImages: analyzeResult.scene_images || [],
              },
            });
            ctrl.close();
            return;
          }

          // Phase 2 혹은 end-to-end: 렌더 결과
          // scriptPath로 metadata_generator 호출해 3줄 summary + 해시태그 복원
          const scriptPathForMeta = renderResult?.script_path || existingScriptPath || "";
          let celebMeta: any = { summary: "", hashtags: "", scenes: [] };
          if (scriptPathForMeta) {
            try {
              celebMeta = JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.analyzer.script_models import ShortsScript
from src.upload.metadata_generator import generate_metadata
s = ShortsScript.load(Path('''${scriptPathForMeta}'''))
m = generate_metadata(s)
print(json.dumps({
  "summary": m.get("summary",""),
  "hashtags": m.get("hashtags",""),
  "scenes": [sc.to_dict() for sc in s.scenes],
}, ensure_ascii=False))`));
            } catch (e) {
              // 메타 생성 실패해도 렌더 결과는 전달
            }
          }
          const fallbackSummary = sourceUrl ? `출처: ${sourceUrl}` : "학습 목적 전용";
          send("done", {
            result: {
              videoPath: videoOutputPath,
              title: name,
              emotion: "relatable",
              duration: 0,
              imageCount: (renderResult?.scene_images || []).length,
              videoCount: (renderResult?.scene_videos || []).length,
              cost: 0,
              sourceType: "celebrity",
              summary: celebMeta.summary || fallbackSummary,
              hashtags: celebMeta.hashtags || "",
              scriptPath: scriptPathForMeta,
              audioPath: renderResult?.audio_path || "",
              scenes: celebMeta.scenes || [],
              sceneImages: renderResult?.scene_images || [],
              sceneVideos: renderResult?.scene_videos || [],
              sourceUrl,
              celebrityName: name,
            },
          });
          ctrl.close();
          return;
        }

        let rawPath: string;
        // Holds the analyzer result: {title, emotion, duration, scenes, sp}.
        // When mode==="script", we bypass Claude and synthesize this object
        // by loading metadata directly from the provided scriptPath.
        let a: any;

        if (mode === "script") {
          // ── Phase 2 entry: skip input capture + analysis ─────────
          if (!existingScriptPath) {
            send("error", {message:"scriptPath가 필요합니다 (mode=script)"});
            ctrl.close(); return;
          }
          a = await withStage("수정된 스크립트 로드", 5, async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from src.analyzer.script_models import ShortsScript
sp='''${existingScriptPath}'''
s=ShortsScript.load(sp)
print(json.dumps({"title":s.metadata.title,"emotion":s.metadata.emotion_type,"duration":s.metadata.duration,"scenes":len(s.scenes),"sp":sp}))`)));
          rawPath = "";
          send("progress",{message:`✅ 스크립트 로드됨 (${a.scenes}씬)`});
        } else if (mode === "url") {
          const urlVal = fd.get("url") as string;
          if (!urlVal) { send("error",{message:"URL을 입력해주세요"}); ctrl.close(); return; }
          const r = await withStage("URL 콘텐츠 추출", 45, async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from src.scraper.url_scraper import extract_from_url
from src.scraper.manual_input import save_post
post=extract_from_url('''${urlVal}''')
s=save_post(post)
print(json.dumps({"path":str(s),"title":post.title,"comments":len(post.comments)}))`)));
          send("progress",{message:`✅ "${r.title}" (댓글 ${r.comments}개)`});
          rawPath = r.path;
        } else if (mode === "image") {
          const imgs = fd.getAll("images") as File[];
          if (!imgs.length) { send("error",{message:"이미지를 업로드해주세요"}); ctrl.close(); return; }
          const tmp = join(ROOT,"data","temp",uuid());
          await mkdir(tmp,{recursive:true});
          const paths: string[] = [];
          for (const img of imgs) {
            const buf = Buffer.from(await img.arrayBuffer());
            const fp = join(tmp, img.name.replace(/[^a-zA-Z0-9._-]/g,"_"));
            await writeFile(fp, buf);
            paths.push(fp);
          }
          const r = await withStage(`OCR 텍스트 추출 (${imgs.length}장)`, imgs.length * 15, async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.scraper.image_extractor import extract_from_images
from src.scraper.manual_input import save_post
post=extract_from_images([Path(p) for p in ${JSON.stringify(paths)}])
s=save_post(post)
print(json.dumps({"path":str(s),"title":post.title,"comments":len(post.comments)}))`)));
          send("progress",{message:`✅ "${r.title}" (댓글 ${r.comments}개)`});
          rawPath = r.path;
        } else if (mode === "topic") {
          const topic = fd.get("topic") as string;
          const contentStyle = (fd.get("contentStyle") as string) || "narration";
          const tone = (fd.get("tone") as string) || "";
          const details = (fd.get("details") as string) || "";
          if (!topic || topic.length < 5) { send("error",{message:"주제를 5자 이상 입력해주세요"}); ctrl.close(); return; }
          const r = await withStage("주제 저장", 5, async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from src.scraper.topic_input import TopicInput,save_topic
ti=TopicInput(topic=${JSON.stringify(topic)},style=${JSON.stringify(contentStyle)},tone=${JSON.stringify(tone)},details=${JSON.stringify(details)})
p=save_topic(ti)
print(json.dumps({"path":str(p),"topic":ti.topic}))`)));
          send("progress",{message:`✅ "${r.topic}"`});
          rawPath = r.path;
        } else if (mode === "political") {
          const ytUrl = fd.get("youtubeUrl") as string;
          const clipStartRaw = parseFloat((fd.get("clipStart") as string) || "0") || 0;
          const clipEndRaw = parseFloat((fd.get("clipEnd") as string) || "0") || 0;
          const polTone = (fd.get("politicalTone") as string) || "";
          const polDetails = (fd.get("politicalDetails") as string) || "";
          if (!ytUrl) { send("error",{message:"YouTube URL을 입력해주세요"}); ctrl.close(); return; }
          const r = await withStage("정치 입력 저장", 5, async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from src.scraper.political_input import PoliticalInput,save_political
pi=PoliticalInput(youtube_url=${JSON.stringify(ytUrl)},clip_start=${clipStartRaw},clip_end=${clipEndRaw},tone=${JSON.stringify(polTone)},details=${JSON.stringify(polDetails)})
p=save_political(pi)
print(json.dumps({"path":str(p),"url":pi.youtube_url}))`)));
          send("progress",{message:`✅ "${r.url}"`});
          rawPath = r.path;
        } else if (mode === "natv_clip") {
          const ytUrl = fd.get("youtubeUrl") as string;
          if (!ytUrl) { send("error",{message:"NATV YouTube URL을 입력해주세요"}); ctrl.close(); return; }
          rawPath = "";
          send("progress",{message:`🔗 NATV URL: ${ytUrl}`});
        } else if (mode === "political_pro") {
          // Feature 009: pre-generated plans flow.
          // Plans are produced by POST /api/political-pro/plans BEFORE we hit
          // this endpoint. Here we receive the selected plan index + cached
          // metadata and convert that plan into a ShortsScript.
          const planIdxRaw = fd.get("selectedPlanIdx") as string;
          const plansJson = fd.get("plansJson") as string;
          const ytUrl = (fd.get("youtubeUrl") as string) || "";
          const videoPath = (fd.get("videoPath") as string) || "";
          const videoDurationSec = parseFloat((fd.get("videoDurationSec") as string) || "0") || 0;
          // Feature 009: 출처 표시용 채널/영상 제목 (Phase 1 plans API 응답에서 전달)
          const sourceChannel = (fd.get("videoChannel") as string) || "";
          const sourceTitle = (fd.get("videoTitle") as string) || "";
          if (!plansJson || planIdxRaw === null || planIdxRaw === undefined) {
            send("error", {message: "정치 기획안 정보가 없습니다 (plansJson / selectedPlanIdx 필수)"});
            ctrl.close(); return;
          }
          rawPath = "";
          send("progress", {message: `🏛️ 기획안 #${parseInt(planIdxRaw)+1} 선택`});

          a = await withStage("기획안 → 스크립트 변환", 10, async () => JSON.parse(await py(`
import sys,json
sys.path.insert(0,'${ROOT}')
from src.analyzer.political_plan_models import ShortsPlan
from src.analyzer.political_planner import plan_to_script
plans=json.loads(r"""${plansJson}""")
idx=int(${parseInt(planIdxRaw)})
plan=ShortsPlan.from_dict(plans[idx])
script=plan_to_script(
  plan,
  video_title=${JSON.stringify(sourceTitle || "political_pro")},
  video_duration_sec=${videoDurationSec},
  youtube_url=${JSON.stringify(ytUrl)},
  source_channel=${JSON.stringify(sourceChannel)},
  source_title=${JSON.stringify(sourceTitle)},
)
# Resolve the saved path back from the most recent file matching slug
from src.config.settings import DATA_SCRIPTS_DIR
saved=sorted(DATA_SCRIPTS_DIR.glob("*_political_pro.json"), key=lambda p: p.stat().st_mtime)[-1]
print(json.dumps({
  "title": script.metadata.title,
  "emotion": script.metadata.emotion_type,
  "duration": script.metadata.duration,
  "scenes": len(script.scenes),
  "sp": str(saved),
  "clip_start": float(plan.clip_start_sec),
  "clip_end": min(float(plan.clip_end_sec), ${videoDurationSec}),
  "video_path": ${JSON.stringify(videoPath)},
  "youtube_url": ${JSON.stringify(ytUrl)},
}))`)));
          send("progress", {message: `✅ 스크립트 변환 완료 (${a.scenes}씬, ${a.duration}초)`});
        } else {
          const t=fd.get("title") as string, b=fd.get("body") as string, c=fd.get("comments") as string||"[]";
          if(!t||!b){send("error",{message:"제목과 본문 필수"});ctrl.close();return;}
          const r = await withStage("글 저장", 5, async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from src.scraper.models import BlindPost,Comment
from src.scraper.manual_input import save_post
cs=tuple(Comment(text=x,likes=0) for x in json.loads('''${c}''') if x.strip())
post=BlindPost(title=${JSON.stringify(t)},author="",body=${JSON.stringify(b)},comments=cs)
print(json.dumps({"path":str(save_post(post)),"title":post.title}))`)));
          send("progress",{message:`✅ "${r.title}"`});
          rawPath=r.path;
        }

        const imageStyle = (fd.get("imageStyle") as string) || "webtoon";

        // Claude CLI analysis — typically 30s–5min. Skipped entirely when
        // mode==="script" (Phase 2 entry already loaded the script above) or
        // mode==="political_pro" (Feature 009; plan→script already produced
        // `a` and the script JSON above).
        if (mode !== "script" && mode !== "political_pro") {
          if (mode === "political") {
            // Political mode: download video + subtitles, then analyze
            const ytUrl = fd.get("youtubeUrl") as string;
            const clipStart = parseFloat((fd.get("clipStart") as string) || "0") || 0;
            const clipEnd = parseFloat((fd.get("clipEnd") as string) || "0") || 0;
            const polTone = (fd.get("politicalTone") as string) || "";
            const polDetails = (fd.get("politicalDetails") as string) || "";

            // Step 1: Download video + subtitles
            const dl = await withStage("YouTube 영상 다운로드", 120, async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.config.settings import DATA_POLITICAL_DIR
from src.scraper.youtube_downloader import download_video,download_subtitles,parse_vtt_subtitles,extract_clip,extract_audio
DATA_POLITICAL_DIR.mkdir(parents=True,exist_ok=True)
url=${JSON.stringify(ytUrl)}
vp=download_video(url,DATA_POLITICAL_DIR)
vtt=download_subtitles(url,DATA_POLITICAL_DIR)
transcript=parse_vtt_subtitles(vtt) if vtt else []
cs=${clipStart};ce=${clipEnd}
if ce<=cs: ce=min(cs+60,120)
cp=extract_clip(vp,cs,ce,DATA_POLITICAL_DIR/"clip.mp4")
ca=extract_audio(cp,DATA_POLITICAL_DIR/"clip_audio.mp3")
print(json.dumps({"video":str(vp),"clip":str(cp),"clip_audio":str(ca),"transcript":transcript,"sub_count":len(transcript),"clip_start":cs,"clip_end":ce}))`)));
            send("progress",{message:`✅ 다운로드 완료 (자막 ${dl.sub_count}줄, 클립 ${dl.clip_start}-${dl.clip_end}초)`});

            // Step 2: Claude analysis with transcript
            a = await withStage("Claude 정치 해설 분석", 180, async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from src.scraper.political_input import PoliticalInput
from src.analyzer.claude_analyzer import analyze_political
pi=PoliticalInput(youtube_url=${JSON.stringify(ytUrl)},clip_start=${dl.clip_start},clip_end=${dl.clip_end},tone=${JSON.stringify(polTone)},details=${JSON.stringify(polDetails)})
transcript=json.loads('''${JSON.stringify(dl.transcript)}''')
s,sp=analyze_political(pi,transcript)
print(json.dumps({"title":s.metadata.title,"emotion":s.metadata.emotion_type,"duration":s.metadata.duration,"scenes":len(s.scenes),"sp":str(sp),"clip":'''${dl.clip}''',"clip_audio":'''${dl.clip_audio}'''}))`)));
          } else if (mode === "topic") {
            const contentStyle = (fd.get("contentStyle") as string) || "narration";
            const tone = (fd.get("tone") as string) || "";
            const details = (fd.get("details") as string) || "";
            a = await withStage("Claude 주제 분석 (쇼츠 스크립트 생성)", 180, async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from src.scraper.topic_input import TopicInput
from src.analyzer.claude_analyzer import analyze_topic
ti=TopicInput(topic=${JSON.stringify(fd.get("topic") as string)},style=${JSON.stringify(contentStyle)},tone=${JSON.stringify(tone)},details=${JSON.stringify(details)})
s,sp=analyze_topic(ti)
print(json.dumps({"title":s.metadata.title,"emotion":s.metadata.emotion_type,"duration":s.metadata.duration,"scenes":len(s.scenes),"sp":str(sp)}))`)));
          } else if (mode === "natv_clip") {
            const ytUrl = fd.get("youtubeUrl") as string;
            const natvTone = (fd.get("tone") as string) || "angry";

            // Step 1: Download video + transcript (VTT 우선, 없으면 Whisper STT 폴백)
            // 환각 방지 bugfix (2026-04-20): 과거엔 자막 없을 때 빈 transcript로
            // analyze_topic(topic="")을 호출 → Claude가 details 힌트만 보고 엉뚱한
            // 내용 생성. transcribe_video_or_fallback이 Whisper로 안전 폴백하고,
            // 그마저 실패하면 TranscriptUnavailableError로 명시 실패.
            const dl = await withStage("NATV 영상 다운로드 + 자막/STT 확보", 900, async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.config.settings import DATA_DIR
from src.scraper.youtube_downloader import (
  download_video, transcribe_video_or_fallback, TranscriptUnavailableError,
)
natv_dir=DATA_DIR/"natv_clips"
natv_dir.mkdir(parents=True,exist_ok=True)
url=${JSON.stringify(ytUrl)}
vp=download_video(url,natv_dir)
try:
  transcript = transcribe_video_or_fallback(url=url, video_path=vp, out_dir=natv_dir)
  print(json.dumps({"video":str(vp),"transcript":transcript,"sub_count":len(transcript),"natv_dir":str(natv_dir)}))
except TranscriptUnavailableError as exc:
  print(json.dumps({"error":"transcript_unavailable","detail":str(exc)[:300]}))`)));
            if ((dl as any).error === "transcript_unavailable") {
              send("error", {message: `자막/STT 확보 실패: ${(dl as any).detail}`});
              ctrl.close();
              return;
            }
            send("progress",{message:`✅ 다운로드 완료 (transcript ${dl.sub_count}줄)`});

            // Step 2: Auto-select best clip + generate script from subtitle content
            const dlTranscript = JSON.stringify(dl.transcript);
            a = await withStage("임팩트 구간 분석 + 스크립트 생성", 180, async () => JSON.parse(await py(`
import sys,json,re;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.analyzer.clip_selector import select_best_clip
from src.scraper.topic_input import TopicInput
from src.analyzer.claude_analyzer import analyze_topic
transcript=json.loads(r"""${dlTranscript}""")
start_sec,end_sec=select_best_clip(transcript,max_duration=55.0)
clip_segs=[s for s in transcript if s["start"]>=start_sec-2 and s["end"]<=end_sec+2]
clip_text=" ".join(s["text"] for s in clip_segs)
clip_text=re.sub(r"(\\S+) \\1",r"\\1",clip_text)[:2000]
# 환각 방지 (bugfix 2026-04-20): 발췌된 clip_text가 비어 있으면 analyze_topic은
# details 힌트만 보고 환각 컨텐츠를 생성하므로 명시적으로 차단한다.
if not clip_text.strip():
  print(json.dumps({"error":"empty_clip_text","detail":"NATV 영상에서 의미 있는 발언 구간을 찾지 못했습니다. 자막 품질이 낮거나 무음 구간일 수 있습니다."}))
else:
  ti=TopicInput(topic=clip_text,style="narration",tone=${JSON.stringify(natvTone)},details="NATV 국회방송 영상 내용 기반 — 실제 발언을 그대로 활용")
  s,sp=analyze_topic(ti)
  print(json.dumps({"title":s.metadata.title,"emotion":s.metadata.emotion_type,"duration":s.metadata.duration,"scenes":len(s.scenes),"sp":str(sp),"natv_video":${JSON.stringify(dl.video)},"clip_start":start_sec,"clip_end":end_sec,"natv_dir":${JSON.stringify(dl.natv_dir)}}))`)));
            if ((a as any).error === "empty_clip_text") {
              send("error", {message: `NATV 클립 생성 실패: ${(a as any).detail}`});
              ctrl.close();
              return;
            }
            send("progress",{message:`✅ "${a.title}" (${a.scenes}씬, 클립 ${a.clip_start?.toFixed(0)}~${a.clip_end?.toFixed(0)}초)`});
          } else {
            a = await withStage("Claude 분석 (쇼츠 스크립트 생성)", 180, async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.scraper.models import BlindPost
from src.analyzer.claude_analyzer import analyze
post=BlindPost.from_dict(json.loads(Path('''${rawPath}''').read_text()))
s,sp=analyze(post)
print(json.dumps({"title":s.metadata.title,"emotion":s.metadata.emotion_type,"duration":s.metadata.duration,"scenes":len(s.scenes),"sp":str(sp)}))`)));
          }
          send("progress",{message:`✅ ${a.emotion} | ${a.scenes}씬 | ${a.duration}초`});

          // Apply custom title if provided (only in phase 1; phase 2 already
          // has any user edits baked into the script via /api/scene/script).
          if (customTitle) {
            await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
s=json.loads(Path('''${a.sp}''').read_text())
s["metadata"]["title"]=${JSON.stringify(customTitle)}
Path('''${a.sp}''').write_text(json.dumps(s,ensure_ascii=False,indent=2))
print("ok")`);
            send("progress",{message:`✅ 제목 설정: ${customTitle}`});
          }
        }

        const finalTitle = customTitle || a.title;

        // ── Phase 1 exit: stopAfter=analyze ────────────────────────
        // Stream is closed here with a "done" event carrying only the
        // script metadata + scenes so the UI can render the review screen.
        // The user edits title/scene text, then re-submits with mode=script.
        if (stopAfter === "analyze") {
          const scriptRaw = JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
s=json.loads(Path('''${a.sp}''').read_text())
print(json.dumps({"scenes":s["scenes"]}))`));
          const reviewSourceType = mode === "topic" ? "topic"
            : mode === "political_pro" ? "political_pro"
            : "blind";
          const reviewPayload: any = {
            phase: "analyzed",
            title: finalTitle,
            emotion: a.emotion,
            duration: a.duration,
            scriptPath: a.sp,
            scenes: scriptRaw.scenes,
            sourceType: reviewSourceType,
          };
          if (mode === "political_pro") {
            reviewPayload.politicalProMeta = {
              videoPath: a.video_path,
              clipStartSec: a.clip_start,
              clipEndSec: a.clip_end,
              youtubeUrl: a.youtube_url,
            };
          }
          send("done", {result: reviewPayload});
          ctrl.close();
          return;
        }

        // Default = video (Kling 2.5 image-to-video, unlimited on Premium+).
        const visualMode = (fd.get("visualMode") as string) || "video";
        let ic=0,vc=0,cost=0;
        let generatedImages: {scene_id:number,image_path:string}[] = [];
        let generatedVideos: {scene_id:number,video_path:string}[] = [];
        let videoPath = "";
        let thumbnailPath = "";
        let ttsResult: {audio_path:string,timings:any[]}|null = null;

        if (dryRun) {
          send("progress",{message:"🎨 [드라이런] 이미지/영상 생성 스킵"});
          send("progress",{message:"🎙️ [드라이런] 음성 생성 스킵"});
          send("progress",{message:"🎬 [드라이런] 렌더링 스킵"});
        } else if (mode === "natv_clip" && a.natv_video && a.clip_start !== undefined) {
          // ── NATV 클립 모드: TTS(optional) + 씬 클립 분할 + 렌더 ──
          // 쇼츠 디폴트는 TTS off — 원본 발언 + BGM/SFX 만으로 임팩트 살림.
          // 사용자가 명시적으로 "on" 보낼 때만 TTS 활성화.
          const natvUseTts = (fd.get("tts") as string) === "on";

          if (natvUseTts) {
            ttsResult = await withStage("Gemini TTS 음성 + 씬 타이밍 (edge-tts 폴백)", 30, async () => JSON.parse(await py(`
import sys,json,os;sys.path.insert(0,'${ROOT}')
from src.analyzer.script_models import ShortsScript
s=ShortsScript.load('''${a.sp}''')
provider="edge"
ap=None;timings=None
if os.environ.get("GEMINI_API_KEY"):
  try:
    from src.tts.gemini_tts_generator import generate_voice_with_timing_gemini, GeminiTTSError
    ap,timings=generate_voice_with_timing_gemini(s)
    provider="gemini"
  except GeminiTTSError as e:
    print(f"[gemini-tts-fallback] {e}", file=sys.stderr)
if ap is None:
  from src.tts.edge_tts_generator import generate_voice_with_timing
  ap,timings=generate_voice_with_timing(s)
print(json.dumps({"audio_path":str(ap),"timings":timings,"provider":provider}))`)));
            const natvProvider = (ttsResult as any).provider === "gemini" ? "Gemini (Google AI Studio)" : "edge-tts (폴백)";
            send("progress",{message:`✅ 음성 완료 — ${natvProvider} · ${ttsResult!.timings.length}씬`});
          } else {
            // No TTS: build synthetic timings from script scene durations
            ttsResult = await withStage("씬 타이밍 계산 (TTS 없음)", 5, async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from src.analyzer.script_models import ShortsScript
s=ShortsScript.load('''${a.sp}''')
t=0.0;timings=[]
for sc in s.scenes:
  dur=sc.duration or 4.0
  timings.append({"scene_id":sc.id,"start_ms":int(t*1000),"end_ms":int((t+dur)*1000)})
  t+=dur
timings.append({"scene_id":-1,"start_ms":int(t*1000),"end_ms":int((t+4)*1000)})
print(json.dumps({"audio_path":"","timings":timings}))`)));
            send("progress",{message:`✅ 씬 타이밍 계산 완료 (TTS 없음)`});
          }

          // Cut NATV clip into per-scene 9:16 clips
          const timingsJson2 = JSON.stringify(ttsResult!.timings);
          const sceneClips = await withStage(`NATV 씬 클립 분할 (9:16 변환, ${a.scenes}씬)`, 60, async () => JSON.parse(await py(`
import sys,json,time;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.dem_shorts.editor.segment_cutter import cut_segment
natv_video=Path(${JSON.stringify(a.natv_video)})
natv_dir=Path(${JSON.stringify(a.natv_dir)})
clip_start=${a.clip_start}
clip_end=${a.clip_end}
clip_duration=clip_end-clip_start
timings=[t for t in json.loads(r"""${timingsJson2}""") if t["scene_id"]!=-1]
tts_total_ms=max(t["end_ms"] for t in timings)
ts=int(time.time())
clips=[]
for t in timings:
  sid=t["scene_id"]
  ns=clip_start+(t["start_ms"]/tts_total_ms)*clip_duration
  ne=clip_start+(t["end_ms"]/tts_total_ms)*clip_duration
  out=natv_dir/f"scene_{ts}_{sid:02d}.mp4"
  cut_segment(input_path=natv_video,output_path=out,start_sec=ns,end_sec=ne)
  clips.append({"scene_id":sid,"video_path":str(out)})
print(json.dumps(clips))`)));
          generatedVideos = sceneClips;
          vc = sceneClips.length;
          send("progress",{message:`✅ 씬 클립 ${vc}개 분할 완료`});

          // Render
          const imgJson0 = JSON.stringify(generatedImages);
          const vidJson0 = JSON.stringify(generatedVideos);
          const timingsJson3 = JSON.stringify(ttsResult!.timings);
          const audioArg = natvUseTts ? `Path('''${ttsResult!.audio_path}''')` : "None";
          const rr0 = await withStage("Remotion 최종 렌더", Math.max(60, a.scenes * 10), async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.analyzer.script_models import ShortsScript
from src.video.renderer import render_video
s=ShortsScript.load('''${a.sp}''')
sv=json.loads(r"""${vidJson0}""") or None
timings=json.loads(r"""${timingsJson3}""")
o=render_video(s,audio_path=${audioArg},scene_videos=sv,use_bgm=${useBgm?"True":"False"},scene_timings=timings,enable_transitions=${useTransitions?"True":"False"},enable_sfx=${useSfx?"True":"False"})
t=o.parent/(o.stem+".thumb.png")
print(json.dumps({"path":str(o),"size":round(o.stat().st_size/(1024*1024),1),"thumbnailPath":str(t) if t.exists() else ""}))`)));
          send("progress",{message:`✅ 렌더링 완료 (${rr0.size}MB)`});
          videoPath = rr0.path;
          thumbnailPath = rr0.thumbnailPath || "";
        } else if (
          mode === "script" &&
          (fd.get("politicalProMeta") as string)
        ) {
          // ── Feature 009 political_pro Phase 2 ──
          // Cut original YouTube clip into per-scene 9:16 segments + use
          // Gemini TTS Charon (fast newscaster tone, neutral delivery).
          // NOTE 2026-05-13: 초기에 "British RP newscaster" 지시했으나, 한국어 본문
          // + 영국식 RP 액센트 조합이 finish_reason=OTHER로 차단됨. 단순 newscaster
          // 톤으로 변경 — 한국어는 voice "Charon" 기본 발음대로 출력.
          let meta: { videoPath: string; clipStartSec: number; clipEndSec: number; youtubeUrl: string };
          try {
            meta = JSON.parse(fd.get("politicalProMeta") as string);
          } catch {
            send("error", {message:"politicalProMeta JSON 파싱 실패"});
            ctrl.close(); return;
          }
          if (!meta.videoPath) {
            send("error", {message:"politicalProMeta.videoPath 누락 — Phase 1 결과를 확인하세요"});
            ctrl.close(); return;
          }

          // Step 1: Gemini TTS with Charon voice + newscaster style
          try {
            ttsResult = await withStage("Gemini TTS (Charon, 영국식 RP 아나운서 톤)", 30, async () => JSON.parse(await py(`
import sys,json,os;sys.path.insert(0,'${ROOT}')
from src.analyzer.script_models import ShortsScript
from src.tts.gemini_tts_generator import generate_voice_with_timing_gemini, GeminiTTSError
if not os.environ.get("GEMINI_API_KEY"):
  print(json.dumps({"error":"tts_failed","detail":"GEMINI_API_KEY 환경변수가 설정되지 않았습니다 (정치 모드는 Gemini TTS 필수)."}))
else:
  try:
    s = ShortsScript.load('''${a.sp}''')
    ap, timings = generate_voice_with_timing_gemini(
      s,
      voice_name="Charon",
      style_prompt="Read in a fast, clear newscaster tone with neutral political delivery:",
      temperature=0.5,
      include_outro=False,
    )
    print(json.dumps({"audio_path": str(ap), "timings": timings}))
  except GeminiTTSError as e:
    print(json.dumps({"error":"tts_failed","detail":str(e)[:300]}))
`)));
          } catch (e: any) {
            send("error", {message: `Gemini TTS 실패: ${(e?.message || String(e)).slice(0, 300)}`});
            ctrl.close(); return;
          }
          if ((ttsResult as any).error === "tts_failed") {
            send("error", {message: (ttsResult as any).detail || "Gemini TTS 실패"});
            ctrl.close(); return;
          }
          send("progress", {message:`✅ Gemini TTS 합성 완료 (${ttsResult!.timings.length}씬)`});

          // Step 2: Cut original YouTube video into per-scene 9:16 clips
          const timingsJsonPP = JSON.stringify(ttsResult!.timings);
          const sceneClipsPP = await withStage(`정치 클립 분할 (9:16 변환, ${a.scenes}씬)`, 60, async () => JSON.parse(await py(`
import sys,json,time;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.dem_shorts.editor.segment_cutter import cut_segment
src_video=Path(${JSON.stringify(meta.videoPath)})
clip_start=${meta.clipStartSec}
clip_end=${meta.clipEndSec}
clip_duration=max(0.1, clip_end - clip_start)
out_dir=src_video.parent
timings=[t for t in json.loads(r"""${timingsJsonPP}""") if t["scene_id"]!=-1]
if not timings:
  print(json.dumps([]))
else:
  tts_total_ms=max(t["end_ms"] for t in timings)
  ts=int(time.time())
  clips=[]
  for t in timings:
    sid=t["scene_id"]
    ns=clip_start+(t["start_ms"]/tts_total_ms)*clip_duration
    ne=clip_start+(t["end_ms"]/tts_total_ms)*clip_duration
    out=out_dir/f"scene_{ts}_{sid:02d}.mp4"
    # political_pro: TTS가 메인 음성이므로 영상 음성은 mute (중첩·에코 방지)
    cut_segment(input_path=src_video, output_path=out, start_sec=ns, end_sec=ne, mute=True)
    clips.append({"scene_id": sid, "video_path": str(out)})
  print(json.dumps(clips))
`)));
          generatedVideos = sceneClipsPP;
          vc = sceneClipsPP.length;
          send("progress", {message: `✅ 씬 클립 ${vc}개 분할 완료`});

          // Step 3: Remotion render
          const vidJsonPP = JSON.stringify(generatedVideos);
          const timingsJsonPP2 = JSON.stringify(ttsResult!.timings);
          const rrPP = await withStage("Remotion 최종 렌더", Math.max(60, a.scenes * 10), async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.analyzer.script_models import ShortsScript
from src.video.renderer import render_video
s=ShortsScript.load('''${a.sp}''')
sv=json.loads(r"""${vidJsonPP}""") or None
timings=json.loads(r"""${timingsJsonPP2}""")
o=render_video(s, audio_path=Path('''${ttsResult!.audio_path}'''), scene_videos=sv, use_bgm=${useBgm?"True":"False"}, scene_timings=timings, enable_transitions=False, enable_sfx=False)
t=o.parent/(o.stem+".thumb.png")
print(json.dumps({"path":str(o),"size":round(o.stat().st_size/(1024*1024),1),"thumbnailPath":str(t) if t.exists() else ""}))
`)));
          send("progress", {message:`✅ 렌더링 완료 (${rrPP.size}MB)`});
          videoPath = rrPP.path;
          thumbnailPath = rrPP.thumbnailPath || "";
        } else if (mode === "political" && a.clip && a.clip_audio) {
          // ── Political mode: audio stitching + scene clip extraction ──
          const polStitch = await withStage("오디오 스티칭 (원본+TTS)", 60, async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.analyzer.script_models import ShortsScript
from src.tts.audio_stitcher import stitch_political_audio
s=ShortsScript.load('''${a.sp}''')
ap,timings=stitch_political_audio(s,Path('''${a.clip_audio}'''))
print(json.dumps({"audio_path":str(ap),"timings":timings}))`)));
          ttsResult = polStitch;
          send("progress",{message:`✅ 오디오 스티칭 완료 (${polStitch.timings.length}씬)`});

          // Extract per-scene video clips for clip scenes
          const sceneClips = await withStage("씬 클립 추출", 30, async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.analyzer.script_models import ShortsScript
from src.scraper.youtube_downloader import extract_scene_clips
from src.config.settings import DATA_VIDEOS_DIR
s=ShortsScript.load('''${a.sp}''')
clips=extract_scene_clips(Path('''${a.clip}'''),list(s.scenes),DATA_VIDEOS_DIR)
print(json.dumps(clips))`)));
          generatedVideos = sceneClips;
          vc = sceneClips.length;
          send("progress",{message:`✅ 씬 클립 ${vc}개 추출`});

          // Render
          const imgJson=JSON.stringify(generatedImages);
          const vidJson=JSON.stringify(generatedVideos);
          const timingsJson=JSON.stringify(ttsResult!.timings);
          const rr = await withStage("Remotion 최종 렌더", Math.max(60, a.scenes * 10), async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.analyzer.script_models import ShortsScript
from src.video.renderer import render_video
s=ShortsScript.load('''${a.sp}''')
ap=Path('''${ttsResult!.audio_path}''')
sv=json.loads('''${vidJson}''') if '''${vidJson}'''!='[]' else None
timings=json.loads('''${timingsJson}''')
o=render_video(s,audio_path=ap,scene_videos=sv,use_bgm=${useBgm ? "True" : "False"},scene_timings=timings,enable_transitions=${useTransitions ? "True" : "False"},enable_sfx=${useSfx ? "True" : "False"})
t=o.parent/(o.stem+".thumb.png")
print(json.dumps({"path":str(o),"size":round(o.stat().st_size/(1024*1024),1),"thumbnailPath":str(t) if t.exists() else ""}))`)));
          send("progress",{message:`✅ 렌더링 완료 (${rr.size}MB)`});
          videoPath = rr.path;
          thumbnailPath = rr.thumbnailPath || "";
        } else if (visualMode === "video") {
          // AI Video clip mode — provider selectable
          const videoProvider = (fd.get("videoProvider") as string) || "deevid";

          // Provider-specific pre-checks
          if (videoProvider === "seedance" && !process.env.SEEDANCE_API_KEY) {
            send("error",{message:"SEEDANCE_API_KEY가 설정되지 않았습니다. deevid.ai를 선택하거나 이미지 모드를 사용해주세요."});
            ctrl.close(); return;
          }
          if (videoProvider === "deevid") {
            // Check that the user has run `python3 -m src.main deevid_login` at least once
            const profileExists = JSON.parse(await py(`
import json
from src.config.settings import DEEVID_PROFILE_DIR
print(json.dumps({"exists": DEEVID_PROFILE_DIR.exists()}))`));
            if (!profileExists.exists) {
              send("error",{message:"deevid.ai 로그인 세션이 없습니다. 터미널에서 'python3 -m src.main deevid_login'을 먼저 실행해주세요."});
              ctrl.close(); return;
            }
          }
          if (videoProvider === "freepik") {
            // Verify the persistent Chrome profile actually has session data.
            // Chrome may use "Default" or "Profile 1" depending on the installation.
            // We check for a Cookies file in any known profile subdirectory.
            const profileExists = JSON.parse(await py(`
import json
from src.config.settings import FREEPIK_PROFILE_DIR
def _has_session(d):
    if not d.exists(): return False
    for sub in ["Default","Profile 1","Profile 2","Profile 3"]:
        if (d / sub / "Cookies").exists(): return True
    return (d / "Local State").exists()
ok = _has_session(FREEPIK_PROFILE_DIR)
print(json.dumps({"ok":ok,"path":str(FREEPIK_PROFILE_DIR)}))`));
            if (!profileExists.ok) {
              send("error",{message:`Freepik 로그인 세션이 없습니다. 터미널에서 'python3 -m src.main freepik_login'을 먼저 실행해주세요. (path=${profileExists.path})`});
              ctrl.close(); return;
            }
          }

          const providerLabel = videoProvider === "deevid" ? "deevid.ai (Veo 3.1)" : videoProvider === "freepik" ? "Freepik Kling 2.5" : "Seedance API";
          // Kling 2.5 ≈ 90 seconds per clip on Premium+
          const videoExpectedSec = a.scenes * 90;

          try {
            const vidResult = await withStage(
              `${providerLabel} 영상 생성 (${a.scenes}씬)`,
              videoExpectedSec,
              async () => JSON.parse(await py(`
import sys,json,asyncio;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.analyzer.script_models import ShortsScript
from src.video_gen.factory import create_generator
from src.video_gen.motion_prompt_builder import build_motion_prompt
from src.config.settings import DATA_VIDEOS_DIR,DATA_DIR
DATA_IMAGES_DIR=DATA_DIR/"images"
s=ShortsScript.load('''${a.sp}''')
gen=create_generator('${videoProvider}')
results=[]
DATA_VIDEOS_DIR.mkdir(parents=True,exist_ok=True)
DATA_IMAGES_DIR.mkdir(parents=True,exist_ok=True)
# Freepik image-to-video: generate start frames first (free), then animate
src_images={}
if '${videoProvider}'=='freepik':
 from src.illustrator.freepik_image_gen import FreepikImageGenerator
 from src.illustrator.prompt_builder import build_image_prompts_simple
 img_gen=FreepikImageGenerator()
 scene_prompts=build_image_prompts_simple(s,'realistic')
 prompts=[{'scene_id':p['scene_id'],'prompt':p['prompt']} for p in scene_prompts]
 img_results=asyncio.run(img_gen.generate_scene_images(prompts,output_dir=DATA_IMAGES_DIR))
 src_images={r['scene_id']:r.get('image_path') for r in img_results if r.get('image_path')}
for scene in s.scenes:
 mp=build_motion_prompt(scene)
 out=str(DATA_VIDEOS_DIR/f"scene_{scene.id:02d}.mp4")
 src=src_images.get(scene.id)
 try:
  vr=asyncio.run(gen.generate_and_wait(prompt=mp,duration=5.0,output_path=out,source_image=src,allow_paid=False))
  results.append({"scene_id":scene.id,"video_path":vr.path})
 except Exception as e:
  results.append({"scene_id":scene.id,"video_path":"","error":str(e)})
print(json.dumps({"results":results,"cost":gen.estimate_cost()*len(s.scenes)}))`))
            );
            for (const r of vidResult.results) {
              if (r.video_path) { generatedVideos.push({scene_id:r.scene_id,video_path:r.video_path}); vc++; }
              else send("progress",{message:`⚠️ 씬 ${r.scene_id} 영상 생성 실패: ${r.error?.slice(0,80) || "원인 불명"} → 이미지 폴백`});
            }
            cost = vidResult.cost;
            send("progress",{message:`✅ AI 영상 ${vc}개 ($${cost.toFixed(3)})`});
          } catch(e:any) { send("progress",{message:`⚠️ ${e.message?.slice(0,200) || "영상 생성 실패"} → 이미지 모드로 진행`}); }
        } else {
          // Manga (image) mode — provider selectable (gemini | gpt | freepik)
          // 2026-05-19 Phase 2A: Imagen 4 (gemini.google.com) 활성화, 기본 gemini.
          const imageProvider = (fd.get("imageProvider") as string) || "gemini";

          // Gemini Imagen 4 branch (Phase 2A — Pro 구독 변동비 $0)
          if (imageProvider === "gemini") {
            const profileExists = JSON.parse(await py(`
import json
from src.config.settings import GEMINI_PROFILE_DIR
print(json.dumps({"ok": GEMINI_PROFILE_DIR.exists() and any(GEMINI_PROFILE_DIR.iterdir()),
                  "path": str(GEMINI_PROFILE_DIR)}))`));
            if (!profileExists.ok) {
              send("error",{message:`Gemini 세션 없음 (${profileExists.path}). 'python3 -m src.main gemini_login' 먼저 실행해주세요.`});
              ctrl.close(); return;
            }
            const im = await withStage(
              `Imagen 4 이미지 생성 (${a.scenes}씬, Gemini Pro)`,
              a.scenes * 40,
              async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from src.analyzer.script_models import ShortsScript
from src.illustrator.gemini_web_image_gen import generate_scene_images_sync
script = ShortsScript.load('''${a.sp}''')
prompts = [{"scene_id": s.id, "prompt": s.text} for s in script.scenes]
r = generate_scene_images_sync(prompts)
print(json.dumps({"c": len(r), "cost": 0.0, "images": r}))`))
            );
            ic = im.c; cost = im.cost; generatedImages = im.images || [];
            send("progress",{message:`✅ Imagen 4 이미지 ${ic}장 (Pro 구독, 변동비 $0)`});
            // skip the freepik/gpt blocks below
          } else {

          // Provider-specific pre-checks
          let canProceed = false;
          let providerLabel = "";
          if (imageProvider === "freepik") {
            const profileExists = JSON.parse(await py(`
import json
from src.config.settings import FREEPIK_PROFILE_DIR
def _has_session(d):
    if not d.exists(): return False
    for sub in ["Default","Profile 1","Profile 2","Profile 3"]:
        if (d / sub / "Cookies").exists(): return True
    return (d / "Local State").exists()
ok = _has_session(FREEPIK_PROFILE_DIR)
print(json.dumps({"ok":ok,"path":str(FREEPIK_PROFILE_DIR)}))`));
            if (!profileExists.ok) {
              send("progress",{message:`⚠️ Freepik 세션 없음 (${profileExists.path}) → GPT 이미지 API로 폴백`});
            } else {
              canProceed = true;
              providerLabel = "Freepik (Nano Banana Pro, 무제한)";
            }
          }

          // Fall back to GPT if freepik not set up, or if user chose gpt
          const useGpt = imageProvider === "gpt" || (imageProvider === "freepik" && !canProceed);
          const hasKey = !!process.env.OPENAI_API_KEY;
          // Nano Banana Pro ≈ 30s per image on Premium+
          const imageExpectedSec = a.scenes * 30;

          if (canProceed && imageProvider === "freepik") {
            const im = await withStage(
              `${providerLabel} 이미지 생성 (${a.scenes}씬)`,
              imageExpectedSec,
              async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from src.analyzer.script_models import ShortsScript
from src.illustrator.image_generator import generate_scene_images
r=generate_scene_images(ShortsScript.load('''${a.sp}'''),image_style='''${imageStyle}''',provider='freepik')
print(json.dumps({"c":len(r),"cost":0.0,"images":[{"scene_id":x["scene_id"],"image_path":x["image_path"]} for x in r]}))`))
            );
            ic = im.c; cost = im.cost; generatedImages = im.images || [];
            send("progress",{message:`✅ 이미지 ${ic}장 (Premium+ 무제한, 변동비 $0)`});
          } else if (useGpt && hasKey) {
            const im = await withStage(
              `GPT Image 생성 (${a.scenes}씬)`,
              imageExpectedSec,
              async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from src.analyzer.script_models import ShortsScript
from src.illustrator.image_generator import generate_scene_images
r=generate_scene_images(ShortsScript.load('''${a.sp}'''),image_style='''${imageStyle}''',provider='gpt')
print(json.dumps({"c":len(r),"cost":len(r)*0.005,"images":[{"scene_id":x["scene_id"],"image_path":x["image_path"]} for x in r]}))`))
            );
            ic = im.c; cost = im.cost; generatedImages = im.images || [];
            send("progress",{message:`✅ GPT 이미지 ${ic}장 ($${cost.toFixed(3)})`});
          } else {
            send("progress",{message:"🎨 이미지 스킵 (Freepik 세션 없음 + OPENAI_API_KEY 미설정)"});
          }
          }  // close else block from Phase 2A gemini branch
        }

        // ───── Common pipeline for BOTH video and manga modes ─────
        // Skipped for natv_clip and political, which have their own full pipelines above.
        if (!dryRun && mode !== "natv_clip" && mode !== "political") {
          ttsResult = await withStage(
            "Gemini TTS 음성 + 씬 타이밍 (edge-tts 폴백)",
            30,
            async () => JSON.parse(await py(`
import sys,json,os;sys.path.insert(0,'${ROOT}')
from src.analyzer.script_models import ShortsScript
s=ShortsScript.load('''${a.sp}''')
provider="edge"
ap=None;timings=None
if os.environ.get("GEMINI_API_KEY"):
  try:
    from src.tts.gemini_tts_generator import generate_voice_with_timing_gemini, GeminiTTSError
    ap,timings=generate_voice_with_timing_gemini(s)
    provider="gemini"
  except GeminiTTSError as e:
    print(f"[gemini-tts-fallback] {e}", file=sys.stderr)
if ap is None:
  from src.tts.edge_tts_generator import generate_voice_with_timing
  ap,timings=generate_voice_with_timing(s)
print(json.dumps({"audio_path":str(ap),"timings":timings,"provider":provider}))`))
          );
          const ttsProvider = (ttsResult as any).provider === "gemini" ? "Gemini (Google AI Studio)" : "edge-tts (폴백)";
          send("progress",{message:`✅ 음성 완료 — ${ttsProvider} · ${ttsResult!.timings.length}씬 타이밍`});

          const imgJson=JSON.stringify(generatedImages);
          const vidJson=JSON.stringify(generatedVideos);
          const timingsJson=JSON.stringify(ttsResult!.timings);
          const rr = await withStage(
            "Remotion 최종 렌더",
            Math.max(60, a.scenes * 10),
            async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.analyzer.script_models import ShortsScript
from src.video.renderer import render_video
s=ShortsScript.load('''${a.sp}''')
ap=Path('''${ttsResult!.audio_path}''')
si=json.loads('''${imgJson}''') if '''${imgJson}'''!='[]' else None
sv=json.loads('''${vidJson}''') if '''${vidJson}'''!='[]' else None
timings=json.loads('''${timingsJson}''')
o=render_video(s,audio_path=ap,scene_images=si,scene_videos=sv,use_bgm=${useBgm ? "True" : "False"},scene_timings=timings,enable_transitions=${useTransitions ? "True" : "False"},enable_sfx=${useSfx ? "True" : "False"})
t=o.parent/(o.stem+".thumb.png")
print(json.dumps({"path":str(o),"size":round(o.stat().st_size/(1024*1024),1),"thumbnailPath":str(t) if t.exists() else ""}))`))
          );
          send("progress",{message:`✅ 렌더링 완료 (${rr.size}MB)`});
          videoPath = rr.path;
          thumbnailPath = rr.thumbnailPath || "";

          if (useYt) {
            try {
              const yt = await withStage("YouTube 업로드", 120, async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.analyzer.script_models import ShortsScript
from src.upload.youtube_uploader import upload_video, is_authenticated
from src.upload.metadata_generator import generate_metadata
if not is_authenticated():
 print(json.dumps({"error":"YouTube 인증 필요. python3 -m src.main youtube-auth 실행"}))
else:
 s=ShortsScript.load('''${a.sp}''')
 m=generate_metadata(s)
 url=upload_video(Path('''${rr.path}'''),m["title"],m["description"],m["tags"])
 print(json.dumps({"url":url}))`)));
              if (yt.error) send("progress", {message:`⚠️ ${yt.error}`});
              else send("progress", {message:`✅ YouTube 업로드 완료: ${yt.url}`});
            } catch(e:any) { send("progress",{message:`⚠️ ${e.message?.slice(0,200) || "YouTube 업로드 실패"}`}); }
          }

          if (useTt) {
            try {
              const tt = await withStage("TikTok Draft 업로드", 120, async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.upload.tiktok_uploader import upload_video, is_authenticated
if not is_authenticated():
 print(json.dumps({"error":"TikTok 인증 필요. python3 -m src.main tiktok-auth 실행"}))
else:
 pid=upload_video(Path('''${rr.path}'''),"[블라인드] ${a.title}")
 print(json.dumps({"publish_id":pid}))`)));
              if (tt.error) send("progress", {message:`⚠️ ${tt.error}`});
              else send("progress", {message:`✅ TikTok Draft 업로드 완료 (TikTok 앱에서 게시하세요)`});
            } catch(e:any) { send("progress",{message:`⚠️ ${e.message?.slice(0,200) || "TikTok 업로드 실패"}`}); }
          }
        }

        // Generate summary + hashtags for display
        const meta=JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from src.analyzer.script_models import ShortsScript
from src.upload.metadata_generator import generate_metadata
s=ShortsScript.load('''${a.sp}''')
m=generate_metadata(s)
print(json.dumps({"summary":m["summary"],"hashtags":m["hashtags"]}))`));

        // Load scene data with TTS timing applied
        const scriptRaw=JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
s=json.loads(Path('''${a.sp}''').read_text())
print(json.dumps({"scenes":s["scenes"]}))`));
        // Apply TTS timing to scene data for UI display
        const ttsTimings = ttsResult?.timings ?? [];
        const ttsMap = Object.fromEntries(ttsTimings.filter((t:any)=>t.scene_id!==-1).map((t:any)=>[t.scene_id, t]));
        const scriptData = {scenes: scriptRaw.scenes.map((sc:any) => {
          const t = ttsMap[sc.id];
          if (t) return {...sc, timestamp: t.start_ms / 1000, duration: (t.end_ms - t.start_ms) / 1000};
          return sc;
        })};

        // Detect political_pro Phase 2 (mode=script with politicalProMeta) so
        // the result screen shows the FR-021 review-required warning and the
        // UI hides upload toggles.
        const finalSourceType =
          mode === "topic" ? "topic"
          : (mode === "script" && (fd.get("politicalProMeta") as string)) ? "political_pro"
          : "blind";
        send("done",{result:{videoPath,thumbnailPath,title:finalTitle,emotion:a.emotion,duration:a.duration,imageCount:ic,videoCount:vc,cost,visualMode,imageStyle,sourceType:finalSourceType,summary:meta.summary,hashtags:meta.hashtags,scriptPath:a.sp,audioPath:ttsResult?.audio_path||"",sceneImages:generatedImages,sceneVideos:generatedVideos,scenes:scriptData.scenes,dryRun}});
      } catch(e:any){ send("error",{message:e.message||"오류"}); }
      ctrl.close();
    }
  });

  return new Response(stream, { headers: {"Content-Type":"text/event-stream","Cache-Control":"no-cache, no-transform",Connection:"keep-alive","X-Accel-Buffering":"no","CF-Cache-Status":"DYNAMIC"} });
}
