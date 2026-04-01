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

        send("progress",{message:"📝 AI 분석 중..."});
        const a=JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.scraper.models import BlindPost
from src.analyzer.claude_analyzer import analyze
post=BlindPost.from_dict(json.loads(Path('''${rawPath}''').read_text()))
s,sp=analyze(post)
print(json.dumps({"title":s.metadata.title,"emotion":s.metadata.emotion_type,"duration":s.metadata.duration,"scenes":len(s.scenes),"sp":str(sp)}))`));
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

        let ic=0,cost=0;
        let generatedImages: {scene_id:number,image_path:string}[] = [];
        let videoPath = "";
        let ttsResult: {audio_path:string,timings:any[]}|null = null;

        if (dryRun) {
          send("progress",{message:"🎨 [드라이런] 이미지 생성 스킵"});
          send("progress",{message:"🎙️ [드라이런] 음성 생성 스킵"});
          send("progress",{message:"🎬 [드라이런] 렌더링 스킵"});
        } else {
          const hasKey=!!process.env.OPENAI_API_KEY;
          if(hasKey){
            send("progress",{message:`🎨 만화 이미지 생성 중 (${a.scenes}씬)...`});
            const im=JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from src.analyzer.script_models import ShortsScript
from src.illustrator.image_generator import generate_scene_images
r=generate_scene_images(ShortsScript.load('''${a.sp}'''))
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
          const timingsJson=JSON.stringify(ttsResult!.timings);
          const rr=JSON.parse(await py(`
import sys,json;sys.path.insert(0,'${ROOT}')
from pathlib import Path
from src.analyzer.script_models import ShortsScript
from src.video.renderer import render_video
s=ShortsScript.load('''${a.sp}''')
ap=Path('''${ttsResult!.audio_path}''')
si=json.loads('''${imgJson}''') if '''${imgJson}'''!='[]' else None
timings=json.loads('''${timingsJson}''')
o=render_video(s,audio_path=ap,scene_images=si,use_bgm=${useBgm ? "True" : "False"},scene_timings=timings)
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

        send("done",{result:{videoPath,title:finalTitle,emotion:a.emotion,duration:a.duration,imageCount:ic,cost,summary:meta.summary,hashtags:meta.hashtags,scriptPath:a.sp,audioPath:ttsResult?.audio_path||"",sceneImages:generatedImages,scenes:scriptData.scenes,dryRun}});
      } catch(e:any){ send("error",{message:e.message||"오류"}); }
      ctrl.close();
    }
  });

  return new Response(stream, { headers: {"Content-Type":"text/event-stream","Cache-Control":"no-cache, no-transform",Connection:"keep-alive","X-Accel-Buffering":"no","CF-Cache-Status":"DYNAMIC"} });
}
