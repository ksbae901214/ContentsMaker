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
  const enc = new TextEncoder();
  const stream = new ReadableStream({
    async start(ctrl) {
      const send = (type: string, data: any) => ctrl.enqueue(enc.encode(`data: ${JSON.stringify({type,...data})}\n\n`));
      try {
        let rawPath: string;
        if (mode === "image") {
          const imgs = fd.getAll("images") as File[];
          if (!imgs.length) { send("error",{message:"이미지를 업로드해주세요"}); ctrl.close(); return; }
          const tmp = join(ROOT,"data","temp",uuid());
          await mkdir(tmp,{recursive:true});
          const paths: string[] = [];
          for (const img of imgs) { const buf = Buffer.from(await img.arrayBuffer()); const fp = join(tmp, img.name.replace(/[^a-zA-Z0-9._-]/g,"_")); await writeFile(fp, buf); paths.push(fp); }
          send("progress",{message:`📸 텍스트 추출 중... (${imgs.length}장)`});
          const r = JSON.parse(await py(`import sys,json;sys.path.insert(0,'${ROOT}')\nfrom pathlib import Path\nfrom src.scraper.image_extractor import extract_from_images\nfrom src.scraper.manual_input import save_post\npost=extract_from_images([Path(p) for p in ${JSON.stringify(paths)}])\ns=save_post(post)\nprint(json.dumps({"path":str(s),"title":post.title,"comments":len(post.comments)}))`));
          send("progress",{message:`✅ "${r.title}" (댓글 ${r.comments}개)`});
          rawPath = r.path;
        } else {
          const t=fd.get("title") as string, b=fd.get("body") as string, c=fd.get("comments") as string||"[]";
          if(!t||!b){send("error",{message:"제목과 본문 필수"});ctrl.close();return;}
          send("progress",{message:"📝 저장 중..."});
          const r=JSON.parse(await py(`import sys,json;sys.path.insert(0,'${ROOT}')\nfrom src.scraper.models import BlindPost,Comment\nfrom src.scraper.manual_input import save_post\ncs=tuple(Comment(text=x,likes=0) for x in json.loads('${c.replace(/'/g,"\\'")}') if x.strip())\npost=BlindPost(title="${t.replace(/"/g,'\\"')}",author="",body="""${b.replace(/"""/g,'\\"\\"\\""')}""",comments=cs)\nprint(json.dumps({"path":str(save_post(post)),"title":post.title}))`));
          send("progress",{message:`✅ "${r.title}"`}); rawPath=r.path;
        }
        send("progress",{message:"📝 AI 분석 중..."});
        const a=JSON.parse(await py(`import sys,json;sys.path.insert(0,'${ROOT}')\nfrom pathlib import Path\nfrom src.scraper.models import BlindPost\nfrom src.analyzer.claude_analyzer import analyze\npost=BlindPost.from_dict(json.loads(Path('${rawPath}').read_text()))\ns=analyze(post)\nsp=sorted(Path('${ROOT}/data/scripts').glob('*.json'))\nprint(json.dumps({"title":s.metadata.title,"emotion":s.metadata.emotion_type,"duration":s.metadata.duration,"scenes":len(s.scenes),"sp":str(sp[-1])}))`));
        send("progress",{message:`✅ ${a.emotion} | ${a.scenes}씬 | ${a.duration}초`});
        let ic=0,cost=0; const hk=!!process.env.OPENAI_API_KEY;
        if(hk){ send("progress",{message:`🎨 만화 생성 중 (${a.scenes}씬)...`});
          const im=JSON.parse(await py(`import sys,json;sys.path.insert(0,'${ROOT}')\nfrom src.analyzer.script_models import ShortsScript\nfrom src.illustrator.image_generator import generate_scene_images\nr=generate_scene_images(ShortsScript.load('${a.sp}'))\nprint(json.dumps({"c":len(r),"cost":len(r)*0.005}))`));
          ic=im.c;cost=im.cost; send("progress",{message:`✅ 만화 ${ic}장 ($${cost.toFixed(3)})`});
        } else send("progress",{message:"🎨 이미지 스킵"});
        send("progress",{message:"🎙️ 음성 생성 중..."});
        await py(`import sys;sys.path.insert(0,'${ROOT}')\nfrom src.analyzer.script_models import ShortsScript\nfrom src.tts.edge_tts_generator import generate_voice\ngenerate_voice(ShortsScript.load('${a.sp}'))\nprint("ok")`);
        send("progress",{message:"✅ 음성 완료"});
        send("progress",{message:"🎬 렌더링 중..."});
        const rr=JSON.parse(await py(`import sys,json;sys.path.insert(0,'${ROOT}')\nfrom pathlib import Path\nfrom src.analyzer.script_models import ShortsScript\nfrom src.video.renderer import render_video\ns=ShortsScript.load('${a.sp}')\naf=sorted(Path('${ROOT}/data/audio').glob('*.mp3'))\nap=af[-1] if af else None\nsi=None\nif ${hk?"True":"False"}:\n ifs=sorted(Path('${ROOT}/data/images').glob('*.png'))\n if ifs:\n  si=[]\n  for sc in s.scenes:\n   m=[f for f in ifs if f'scene_{sc.id:02d}' in f.name]\n   if m:si.append({"scene_id":sc.id,"image_path":str(m[-1])})\no=render_video(s,audio_path=ap,scene_images=si)\nprint(json.dumps({"path":str(o),"size":round(o.stat().st_size/(1024*1024),1)}))`));
        send("progress",{message:`✅ 완료 (${rr.size}MB)`});
        send("done",{result:{videoPath:rr.path,title:a.title,emotion:a.emotion,duration:a.duration,imageCount:ic,cost}});
      } catch(e:any){ send("error",{message:e.message||"오류"}); }
      ctrl.close();
    }
  });
  return new Response(stream, { headers: {"Content-Type":"text/event-stream","Cache-Control":"no-cache",Connection:"keep-alive"} });
}
