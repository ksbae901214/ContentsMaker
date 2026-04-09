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
  const useYt = (fd.get("yt") as string) === "on";
  const useTt = (fd.get("tt") as string) === "on";
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

  const stream = new ReadableStream({
    async start(ctrl) {
      const send = (type: string, data: any) => ctrl.enqueue(enc.encode(`data: ${JSON.stringify({type,...data})}\n\n`));

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
        // mode==="script" (Phase 2 entry already loaded the script above).
        if (mode !== "script") {
          if (mode === "topic") {
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
          send("done", {result: {
            phase: "analyzed",
            title: finalTitle,
            emotion: a.emotion,
            duration: a.duration,
            scriptPath: a.sp,
            scenes: scriptRaw.scenes,
            sourceType: mode === "topic" ? "topic" : "blind",
          }});
          ctrl.close();
          return;
        }

        // Default = video (Kling 2.5 image-to-video, unlimited on Premium+).
        const visualMode = (fd.get("visualMode") as string) || "video";
        let ic=0,vc=0,cost=0;
        let generatedImages: {scene_id:number,image_path:string}[] = [];
        let generatedVideos: {scene_id:number,video_path:string}[] = [];
        let videoPath = "";
        let ttsResult: {audio_path:string,timings:any[]}|null = null;

        if (dryRun) {
          send("progress",{message:"🎨 [드라이런] 이미지/영상 생성 스킵"});
          send("progress",{message:"🎙️ [드라이런] 음성 생성 스킵"});
          send("progress",{message:"🎬 [드라이런] 렌더링 스킵"});
        } else if (visualMode === "video") {
          // AI Video clip mode — provider selectable
          const videoProvider = (fd.get("videoProvider") as string) || "seedance";

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
from src.config.settings import DATA_VIDEOS_DIR
s=ShortsScript.load('''${a.sp}''')
gen=create_generator('${videoProvider}')
results=[]
DATA_VIDEOS_DIR.mkdir(parents=True,exist_ok=True)
for scene in s.scenes:
 mp=build_motion_prompt(scene)
 out=str(DATA_VIDEOS_DIR/f"scene_{scene.id:02d}.mp4")
 try:
  vr=asyncio.run(gen.generate_and_wait(prompt=mp,duration=5.0,output_path=out))
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
          // Manga (image) mode — provider selectable (gpt | freepik)
          const imageProvider = (fd.get("imageProvider") as string) || "freepik";

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
        }

        // ───── Common pipeline for BOTH video and manga modes ─────
        // Previously TTS/render/upload lived only inside the manga-mode
        // else branch, so the video mode produced clips but never
        // rendered the final mp4. Hoisted out so both modes finish properly.
        if (!dryRun) {
          ttsResult = await withStage(
            "edge-tts 음성 + 씬 타이밍",
            30,
            async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from src.analyzer.script_models import ShortsScript
from src.tts.edge_tts_generator import generate_voice_with_timing
ap,timings=generate_voice_with_timing(ShortsScript.load('''${a.sp}'''))
print(json.dumps({"audio_path":str(ap),"timings":timings}))`))
          );
          send("progress",{message:`✅ 음성 완료 (${ttsResult!.timings.length}씬 타이밍)`});

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
o=render_video(s,audio_path=ap,scene_images=si,scene_videos=sv,use_bgm=${useBgm ? "True" : "False"},scene_timings=timings)
print(json.dumps({"path":str(o),"size":round(o.stat().st_size/(1024*1024),1)}))`))
          );
          send("progress",{message:`✅ 렌더링 완료 (${rr.size}MB)`});
          videoPath = rr.path;

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

        send("done",{result:{videoPath,title:finalTitle,emotion:a.emotion,duration:a.duration,imageCount:ic,videoCount:vc,cost,visualMode,imageStyle,sourceType:mode==="topic"?"topic":"blind",summary:meta.summary,hashtags:meta.hashtags,scriptPath:a.sp,audioPath:ttsResult?.audio_path||"",sceneImages:generatedImages,sceneVideos:generatedVideos,scenes:scriptData.scenes,dryRun}});
      } catch(e:any){ send("error",{message:e.message||"오류"}); }
      ctrl.close();
    }
  });

  return new Response(stream, { headers: {"Content-Type":"text/event-stream","Cache-Control":"no-cache, no-transform",Connection:"keep-alive","X-Accel-Buffering":"no","CF-Cache-Status":"DYNAMIC"} });
}
