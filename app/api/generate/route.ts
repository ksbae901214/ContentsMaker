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

            // Step 1: Download video + Korean subtitles
            const dl = await withStage("NATV 영상 다운로드", 120, async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.config.settings import DATA_DIR
from src.scraper.youtube_downloader import download_video,download_subtitles,parse_vtt_subtitles
natv_dir=DATA_DIR/"natv_clips"
natv_dir.mkdir(parents=True,exist_ok=True)
url=${JSON.stringify(ytUrl)}
vp=download_video(url,natv_dir)
vtt=download_subtitles(url,natv_dir)
transcript=parse_vtt_subtitles(vtt) if vtt else []
print(json.dumps({"video":str(vp),"transcript":transcript,"sub_count":len(transcript),"natv_dir":str(natv_dir)}))`)));
            send("progress",{message:`✅ 다운로드 완료 (자막 ${dl.sub_count}줄)`});

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
ti=TopicInput(topic=clip_text,style="narration",tone=${JSON.stringify(natvTone)},details="NATV 국회방송 영상 내용 기반 — 실제 발언을 그대로 활용")
s,sp=analyze_topic(ti)
print(json.dumps({"title":s.metadata.title,"emotion":s.metadata.emotion_type,"duration":s.metadata.duration,"scenes":len(s.scenes),"sp":str(sp),"natv_video":${JSON.stringify(dl.video)},"clip_start":start_sec,"clip_end":end_sec,"natv_dir":${JSON.stringify(dl.natv_dir)}}))`)));
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
        } else if (mode === "natv_clip" && a.natv_video && a.clip_start !== undefined) {
          // ── NATV 클립 모드: TTS(optional) + 씬 클립 분할 + 렌더 ──
          const natvUseTts = (fd.get("tts") as string) !== "off";

          if (natvUseTts) {
            ttsResult = await withStage("edge-tts 음성 + 씬 타이밍", 30, async () => JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from src.analyzer.script_models import ShortsScript
from src.tts.edge_tts_generator import generate_voice_with_timing
ap,timings=generate_voice_with_timing(ShortsScript.load('''${a.sp}'''))
print(json.dumps({"audio_path":str(ap),"timings":timings}))`)));
            send("progress",{message:`✅ 음성 완료 (${ttsResult!.timings.length}씬)`});
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
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.dem_shorts.editor.segment_cutter import cut_segment
natv_video=Path(${JSON.stringify(a.natv_video)})
natv_dir=Path(${JSON.stringify(a.natv_dir)})
clip_start=${a.clip_start}
clip_end=${a.clip_end}
clip_duration=clip_end-clip_start
timings=[t for t in json.loads(r"""${timingsJson2}""") if t["scene_id"]!=-1]
tts_total_ms=max(t["end_ms"] for t in timings)
clips=[]
for t in timings:
  sid=t["scene_id"]
  ns=clip_start+(t["start_ms"]/tts_total_ms)*clip_duration
  ne=clip_start+(t["end_ms"]/tts_total_ms)*clip_duration
  out=natv_dir/f"scene_{sid:02d}.mp4"
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
o=render_video(s,audio_path=${audioArg},scene_videos=sv,use_bgm=${useBgm?"True":"False"},scene_timings=timings)
print(json.dumps({"path":str(o),"size":round(o.stat().st_size/(1024*1024),1)}))`)));
          send("progress",{message:`✅ 렌더링 완료 (${rr0.size}MB)`});
          videoPath = rr0.path;
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
o=render_video(s,audio_path=ap,scene_videos=sv,use_bgm=${useBgm ? "True" : "False"},scene_timings=timings)
print(json.dumps({"path":str(o),"size":round(o.stat().st_size/(1024*1024),1)}))`)));
          send("progress",{message:`✅ 렌더링 완료 (${rr.size}MB)`});
          videoPath = rr.path;
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
        // Skipped for natv_clip and political, which have their own full pipelines above.
        if (!dryRun && mode !== "natv_clip" && mode !== "political") {
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
