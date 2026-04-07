import { NextRequest } from "next/server";
import { spawn } from "child_process";
import { writeFile, mkdir } from "fs/promises";
import { join } from "path";
import { v4 as uuid } from "uuid";

const ROOT = process.cwd();
export const maxDuration = 300;

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
  const enc = new TextEncoder();

  const stream = new ReadableStream({
    async start(ctrl) {
      const send = (type: string, data: any) => ctrl.enqueue(enc.encode(`data: ${JSON.stringify({type,...data})}\n\n`));
      try {
        let rawPath: string;

        if (mode === "url") {
          const urlVal = fd.get("url") as string;
          if (!urlVal) { send("error",{message:"URL을 입력해주세요"}); ctrl.close(); return; }
          send("progress",{message:`🔗 URL에서 콘텐츠 추출 중...`});
          const r = JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from src.scraper.url_scraper import extract_from_url
from src.scraper.manual_input import save_post
post=extract_from_url('''${urlVal}''')
s=save_post(post)
print(json.dumps({"path":str(s),"title":post.title,"comments":len(post.comments)}))`));
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
          send("progress",{message:`📸 텍스트 추출 중... (${imgs.length}장)`});
          const r = JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.scraper.image_extractor import extract_from_images
from src.scraper.manual_input import save_post
post=extract_from_images([Path(p) for p in ${JSON.stringify(paths)}])
s=save_post(post)
print(json.dumps({"path":str(s),"title":post.title,"comments":len(post.comments)}))`));
          send("progress",{message:`✅ "${r.title}" (댓글 ${r.comments}개)`});
          rawPath = r.path;
        } else if (mode === "topic") {
          const topic = fd.get("topic") as string;
          const contentStyle = (fd.get("contentStyle") as string) || "narration";
          const tone = (fd.get("tone") as string) || "";
          const details = (fd.get("details") as string) || "";
          if (!topic || topic.length < 5) { send("error",{message:"주제를 5자 이상 입력해주세요"}); ctrl.close(); return; }
          send("progress",{message:"📝 주제 저장 중..."});
          const r = JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from src.scraper.topic_input import TopicInput,save_topic
ti=TopicInput(topic=${JSON.stringify(topic)},style=${JSON.stringify(contentStyle)},tone=${JSON.stringify(tone)},details=${JSON.stringify(details)})
p=save_topic(ti)
print(json.dumps({"path":str(p),"topic":ti.topic}))`));
          send("progress",{message:`✅ "${r.topic}"`});
          rawPath = r.path;
        } else {
          const t=fd.get("title") as string, b=fd.get("body") as string, c=fd.get("comments") as string||"[]";
          if(!t||!b){send("error",{message:"제목과 본문 필수"});ctrl.close();return;}
          send("progress",{message:"📝 저장 중..."});
          const r=JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from src.scraper.models import BlindPost,Comment
from src.scraper.manual_input import save_post
cs=tuple(Comment(text=x,likes=0) for x in json.loads('''${c}''') if x.strip())
post=BlindPost(title=${JSON.stringify(t)},author="",body=${JSON.stringify(b)},comments=cs)
print(json.dumps({"path":str(save_post(post)),"title":post.title}))`));
          send("progress",{message:`✅ "${r.title}"`});
          rawPath=r.path;
        }

        const imageStyle = (fd.get("imageStyle") as string) || "webtoon";

        // Analysis: topic mode uses analyze_topic, others use analyze
        send("progress",{message:"📝 AI 분석 중..."});
        let a: any;
        if (mode === "topic") {
          const contentStyle = (fd.get("contentStyle") as string) || "narration";
          const tone = (fd.get("tone") as string) || "";
          const details = (fd.get("details") as string) || "";
          a = JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from src.scraper.topic_input import TopicInput
from src.analyzer.claude_analyzer import analyze_topic
ti=TopicInput(topic=${JSON.stringify(fd.get("topic") as string)},style=${JSON.stringify(contentStyle)},tone=${JSON.stringify(tone)},details=${JSON.stringify(details)})
s,sp=analyze_topic(ti)
print(json.dumps({"title":s.metadata.title,"emotion":s.metadata.emotion_type,"duration":s.metadata.duration,"scenes":len(s.scenes),"sp":str(sp)}))`));
        } else {
          a = JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.scraper.models import BlindPost
from src.analyzer.claude_analyzer import analyze
post=BlindPost.from_dict(json.loads(Path('''${rawPath}''').read_text()))
s,sp=analyze(post)
print(json.dumps({"title":s.metadata.title,"emotion":s.metadata.emotion_type,"duration":s.metadata.duration,"scenes":len(s.scenes),"sp":str(sp)}))`));
        }
        send("progress",{message:`✅ ${a.emotion} | ${a.scenes}씬 | ${a.duration}초`});

        // Apply custom title if provided
        const finalTitle = customTitle || a.title;
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

        const visualMode = (fd.get("visualMode") as string) || "manga";
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
            // Check that the user has run `python3 -m src.main freepik_login` at least once
            const profileExists = JSON.parse(await py(`
import json
from src.config.settings import FREEPIK_PROFILE_DIR
print(json.dumps({"exists": FREEPIK_PROFILE_DIR.exists()}))`));
            if (!profileExists.exists) {
              send("error",{message:"Freepik 로그인 세션이 없습니다. 터미널에서 'python3 -m src.main freepik_login'을 먼저 실행해주세요."});
              ctrl.close(); return;
            }
          }

          const providerLabel = videoProvider === "deevid" ? "deevid.ai (Veo 3.1)" : videoProvider === "freepik" ? "Freepik" : "Seedance API";
          send("progress",{message:`🎥 ${providerLabel}로 영상 클립 생성 중 (${a.scenes}씬)...`});

          try {
            const vidResult = JSON.parse(await py(`
import sys,json,asyncio;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.analyzer.script_models import ShortsScript
from src.video_gen.factory import create_generator
from src.config.settings import DATA_VIDEOS_DIR
s=ShortsScript.load('''${a.sp}''')
gen=create_generator('${videoProvider}')
results=[]
DATA_VIDEOS_DIR.mkdir(parents=True,exist_ok=True)
for scene in s.scenes:
 mp=scene.motion_prompt or scene.voice_text[:100]
 out=str(DATA_VIDEOS_DIR/f"scene_{scene.id:02d}.mp4")
 try:
  vr=asyncio.run(gen.generate_and_wait(prompt=mp,duration=5.0,output_path=out))
  results.append({"scene_id":scene.id,"video_path":vr.path})
 except Exception as e:
  results.append({"scene_id":scene.id,"video_path":"","error":str(e)})
print(json.dumps({"results":results,"cost":gen.estimate_cost()*len(s.scenes)}))`));
            for (const r of vidResult.results) {
              if (r.video_path) { generatedVideos.push({scene_id:r.scene_id,video_path:r.video_path}); vc++; }
              else send("progress",{message:`⚠️ 씬 ${r.scene_id} 영상 생성 실패 → 이미지 폴백`});
            }
            cost = vidResult.cost;
            send("progress",{message:`✅ AI 영상 ${vc}개 ($${cost.toFixed(3)})`});
          } catch(e:any) { send("progress",{message:`⚠️ 영상 생성 실패: ${e.message?.slice(0,100)}. 이미지 모드로 진행합니다.`}); }
        } else {
          const hasKey=!!process.env.OPENAI_API_KEY;
          if(hasKey){
            send("progress",{message:`🎨 만화 이미지 생성 중 (${a.scenes}씬)...`});
            const im=JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from src.analyzer.script_models import ShortsScript
from src.illustrator.image_generator import generate_scene_images
r=generate_scene_images(ShortsScript.load('''${a.sp}'''),image_style='''${imageStyle}''')
print(json.dumps({"c":len(r),"cost":len(r)*0.005,"images":[{"scene_id":x["scene_id"],"image_path":x["image_path"]} for x in r]}))`));
            ic=im.c;cost=im.cost;generatedImages=im.images||[];
            send("progress",{message:`✅ 만화 ${ic}장 ($${cost.toFixed(3)})`});
          } else send("progress",{message:"🎨 이미지 스킵 (OPENAI_API_KEY 미설정)"});

          send("progress",{message:"🎙️ 음성 생성 중 (타이밍 추출)..."});
          ttsResult=JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from src.analyzer.script_models import ShortsScript
from src.tts.edge_tts_generator import generate_voice_with_timing
ap,timings=generate_voice_with_timing(ShortsScript.load('''${a.sp}'''))
print(json.dumps({"audio_path":str(ap),"timings":timings}))`));
          send("progress",{message:`✅ 음성 완료 (${ttsResult!.timings.length}씬 타이밍)`});

          send("progress",{message:"🎬 렌더링 중..."});
          const imgJson=JSON.stringify(generatedImages);
          const vidJson=JSON.stringify(generatedVideos);
          const timingsJson=JSON.stringify(ttsResult!.timings);
          const rr=JSON.parse(await py(`
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
print(json.dumps({"path":str(o),"size":round(o.stat().st_size/(1024*1024),1)}))`));
          send("progress",{message:`✅ 렌더링 완료 (${rr.size}MB)`});
          videoPath = rr.path;

          let ytUrl="";
          if(useYt){
            send("progress",{message:"📺 YouTube 업로드 중..."});
            try{
              const yt=JSON.parse(await py(`
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
 print(json.dumps({"url":url}))`));
              if(yt.error){send("progress",{message:`⚠️ ${yt.error}`})}
              else{ytUrl=yt.url;send("progress",{message:`✅ YouTube 업로드 완료: ${ytUrl}`})}
            }catch(e:any){send("progress",{message:`⚠️ YouTube 업로드 실패: ${e.message?.slice(0,100)}`})}
          }

          let ttStatus="";
          if(useTt){
            send("progress",{message:"🎵 TikTok Draft 업로드 중..."});
            try{
              const tt=JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.upload.tiktok_uploader import upload_video, is_authenticated
if not is_authenticated():
 print(json.dumps({"error":"TikTok 인증 필요. python3 -m src.main tiktok-auth 실행"}))
else:
 pid=upload_video(Path('''${rr.path}'''),"[블라인드] ${a.title}")
 print(json.dumps({"publish_id":pid}))`));
              if(tt.error){send("progress",{message:`⚠️ ${tt.error}`})}
              else{ttStatus=tt.publish_id;send("progress",{message:`✅ TikTok Draft 업로드 완료 (TikTok 앱에서 게시하세요)`})}
            }catch(e:any){send("progress",{message:`⚠️ TikTok 업로드 실패: ${e.message?.slice(0,100)}`})}
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
