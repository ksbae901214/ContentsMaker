"use client";
import { useState, useEffect } from "react";
import { SceneEditor } from "./components/SceneEditor";
import { ScriptReviewer } from "./components/ScriptReviewer";

type Status = "idle" | "processing" | "reviewing" | "done" | "error";
interface SceneImage { scene_id: number; image_path: string; prompt: string; }
interface SceneData { id: number; timestamp: number; duration: number; type: string; text: string; voice_text: string; emphasis: string; }
interface JobResult { videoPath: string; title: string; emotion: string; duration: number; imageCount: number; videoCount?: number; cost: number; visualMode?: string; imageStyle?: string; sourceType?: string; youtubeUrl?: string; tiktokStatus?: string; summary?: string; hashtags?: string; scriptPath?: string; audioPath?: string; sceneImages?: SceneImage[]; sceneVideos?: {scene_id:number;video_path:string}[]; scenes?: SceneData[]; dryRun?: boolean; }
// Phase 1 (analyze-only) result held during the reviewing state.
interface ReviewPayload {
  phase: "analyzed";
  title: string;
  emotion: string;
  duration: number;
  scriptPath: string;
  scenes: SceneData[];
  sourceType?: string;
}
interface Stats { imageCount: number; videoCount: number; audioCount: number; scriptCount: number; imageCost: number; videoSizeMB: number; }
const EL: Record<string, string> = { funny: "😂 재밌음", touching: "🥹 감동", angry: "😤 분노", relatable: "🤝 공감" };

export default function Home() {
  const [tab, setTab] = useState<"image"|"manual"|"url"|"topic">("image");
  const [topicText, setTopicText] = useState("");
  const [contentStyle, setContentStyle] = useState<"narration"|"skit"|"review">("narration");
  const [tone, setTone] = useState("");
  const [details, setDetails] = useState("");
  const [imageStyle, setImageStyle] = useState<"webtoon"|"3d_pixar"|"realistic"|"anime">("realistic");
  // Default = video mode (Kling 2.5 + Premium+ unlimited). User-confirmed default.
  const [visualMode, setVisualMode] = useState<"manga"|"video">("video");
  const [videoProvider, setVideoProvider] = useState<"seedance"|"deevid"|"freepik">("freepik");
  const [imageProvider, setImageProvider] = useState<"freepik"|"gpt">("freepik");
  const [status, setStatus] = useState<Status>("idle");
  const [progress, setProgress] = useState<string[]>([]);
  const [result, setResult] = useState<JobResult|null>(null);
  const [review, setReview] = useState<ReviewPayload|null>(null);
  // "analyze" during Phase 1 (input → Claude) or "render" during Phase 2
  // (script → images/videos/TTS/render). Drives the processing header.
  const [phase, setPhase] = useState<"analyze"|"render">("analyze");
  // Visual/upload/bgm options from Phase 1 form are persisted here so
  // Phase 2 (mode=script) can resubmit with the same settings.
  const [phase2Opts, setPhase2Opts] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [comments, setComments] = useState([""]);
  const [stats, setStats] = useState<Stats|null>(null);
  const [bgm, setBgm] = useState(true);
  const [ytUpload, setYtUpload] = useState(false);
  const [ttUpload, setTtUpload] = useState(false);
  const [urlInput, setUrlInput] = useState("");
  const [customTitle, setCustomTitle] = useState("");

  const loadStats = () => { fetch("/api/stats").then(r=>r.json()).then(setStats).catch(()=>{}); };
  useEffect(()=>{ loadStats(); }, []);

  const generate = async (fd: FormData) => {
    setStatus("processing"); setProgress([]); setResult(null); setReview(null); setError("");
    try {
      const res = await fetch("/api/generate", { method: "POST", body: fd });
      const reader = res.body?.getReader();
      if (!reader) throw new Error("스트림 열기 실패");
      const dec = new TextDecoder();
      // Buffer partial lines across TCP chunk boundaries. Large "done"
      // events (full scenes array ≈ 3-5 KB) can be split mid-line and
      // would otherwise silently fail to parse, leaving the UI stuck
      // in "processing" forever.
      let buf = "";
      const processLine = (line: string) => {
        if (!line.startsWith("data: ")) return;
        let d: any;
        try { d = JSON.parse(line.slice(6)); }
        catch { return; } // incomplete / corrupt line, skip
        if (d.type === "progress") setProgress(p => {
          const msg: string = d.message || "";
          // Heartbeat messages (⏳ prefix) replace the previous heartbeat so
          // the log stays readable during multi-minute operations. Completion
          // (✅), start (⏳ ... 시작), and error (❌/⚠️) messages all append.
          const isHeartbeat = msg.startsWith("⏳") && msg.includes("진행 중");
          if (isHeartbeat && p.length > 0) {
            const last = p[p.length-1];
            if (last.startsWith("⏳") && last.includes("진행 중")) {
              return [...p.slice(0, -1), msg];
            }
          }
          return [...p, msg];
        });
        else if (d.type === "done") {
          // Phase 1 analyze-only result carries phase==="analyzed"
          // and no videoPath — show the review screen instead of done.
          if (d.result?.phase === "analyzed") {
            setReview(d.result as ReviewPayload);
            setStatus("reviewing");
          } else {
            setResult(d.result);
            setStatus("done");
          }
        }
        else if (d.type === "error") throw new Error(d.message);
      };
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          // Flush any final buffered line (in case stream ended without
          // a trailing newline).
          if (buf.trim()) processLine(buf);
          break;
        }
        buf += dec.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? ""; // last element may be a partial line
        for (const line of lines) processLine(line);
      }
    } catch (e: any) { setError(e.message); setStatus("error"); }
  };

  // Kick off Phase 1 (analyze-only). Stores the visual/upload options so
  // Phase 2 (generateFromScript) can resubmit with the same settings.
  const startAnalyze = (fd: FormData) => {
    fd.set("stopAfter", "analyze");
    const opts: Record<string, string> = {};
    ["visualMode","imageStyle","videoProvider","imageProvider","bgm","yt","tt"].forEach(k => {
      const v = fd.get(k);
      if (typeof v === "string") opts[k] = v;
    });
    setPhase2Opts(opts);
    setPhase("analyze");
    generate(fd);
  };

  // Phase 2: from the reviewed script → images/videos/TTS/render.
  const generateFromScript = () => {
    if (!review) return;
    const fd = new FormData();
    fd.set("mode", "script");
    fd.set("scriptPath", review.scriptPath);
    Object.entries(phase2Opts).forEach(([k, v]) => fd.set(k, v));
    setPhase("render");
    generate(fd);
  };

  const reset = () => { setStatus("idle"); setResult(null); setReview(null); setProgress([]); setFiles([]); setError(""); };

  if (status === "processing") return (
    <main className="max-w-2xl mx-auto px-4 py-8">
      <div className="text-center py-8">
        <div className="text-5xl mb-4 animate-bounce">🎬</div>
        <h2 className="text-xl font-bold mb-2">{phase==="render"?"영상 생성 중...":"스크립트 분석 중..."}</h2>
        <p className="text-gray-400">{progress[progress.length-1]||"준비 중..."}</p>
      </div>
      <div className="w-full bg-gray-800 rounded-full h-2 mb-4">
        <div className="bg-blue-600 h-2 rounded-full transition-all duration-500" style={{width:`${Math.min((progress.length/8)*100,95)}%`}}/>
      </div>
      <div className="bg-gray-900 rounded-lg p-4 max-h-64 overflow-y-auto">
        {progress.map((m,i)=>(<div key={i} className="flex gap-2 py-1 text-sm"><span className="text-green-400">✓</span><span className="text-gray-300">{m}</span></div>))}
        <div className="flex gap-2 py-1 text-sm"><span className="text-yellow-400 animate-pulse">●</span><span className="text-gray-500">처리 중...</span></div>
      </div>
    </main>
  );

  if (status === "reviewing" && review) return (
    <ScriptReviewer
      title={review.title}
      scenes={review.scenes}
      scriptPath={review.scriptPath}
      emotion={review.emotion}
      duration={review.duration}
      imageStyle={imageStyle}
      onTitleChange={(t) => setReview({...review, title: t})}
      onScenesChange={(s) => setReview({...review, scenes: s})}
      onGenerate={generateFromScript}
      onCancel={reset}
    />
  );

  if (status === "done" && result) {
    const url = `/api/download?path=${encodeURIComponent(result.videoPath)}`;
    return (
      <main className="max-w-2xl mx-auto px-4 py-8">
        <div className="text-center mb-6"><div className="text-5xl mb-3">{result.dryRun?"🧪":"🎉"}</div><h2 className="text-2xl font-bold">{result.dryRun?"파이프라인 테스트 완료!":"영상 생성 완료!"}</h2>{result.dryRun&&<p className="text-yellow-400 text-sm mt-1">이미지 생성 / 음성 / 렌더링 / 업로드를 건너뛰었습니다</p>}</div>
        {result.videoPath ? (
          <div className="bg-gray-900 rounded-xl overflow-hidden flex justify-center mb-6">
            <video key={result.videoPath} src={url} controls className="max-h-[500px]" style={{aspectRatio:"9/16",maxWidth:"300px"}}/>
          </div>
        ) : (
          <div className="bg-gray-900 rounded-xl p-6 text-center mb-6 text-gray-500">영상 미생성 (드라이런 모드)</div>
        )}
        <div className="bg-gray-800 rounded-lg p-4 space-y-2 text-sm mb-6">
          <div className="flex justify-between"><span className="text-gray-400">제목</span><span>{result.title}</span></div>
          <div className="flex justify-between"><span className="text-gray-400">감정</span><span>{EL[result.emotion]||result.emotion}</span></div>
          <div className="flex justify-between"><span className="text-gray-400">길이</span><span>{result.duration}초</span></div>
          {result.imageCount>0&&<div className="flex justify-between"><span className="text-gray-400">이미지</span><span>{result.imageCount}장</span></div>}
          {(result.videoCount||0)>0&&<div className="flex justify-between"><span className="text-gray-400">영상 클립</span><span>{result.videoCount}개</span></div>}
          {result.imageStyle&&result.imageStyle!=="webtoon"&&<div className="flex justify-between"><span className="text-gray-400">스타일</span><span>{result.imageStyle}</span></div>}
          <div className="flex justify-between"><span className="text-gray-400">GPT API 비용</span><span className="text-green-400">${result.cost.toFixed(3)}</span></div>
          {result.youtubeUrl&&<div className="flex justify-between"><span className="text-gray-400">YouTube</span><a href={result.youtubeUrl} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">{result.youtubeUrl}</a></div>}
          {result.tiktokStatus&&<div className="flex justify-between"><span className="text-gray-400">TikTok</span><span className="text-purple-400">{result.tiktokStatus}</span></div>}
        </div>
        {result.scenes && result.scriptPath && (
          <div className="mb-6">
            <SceneEditor
              title={result.title}
              scenes={result.scenes}
              sceneImages={result.sceneImages || []}
              scriptPath={result.scriptPath}
              useBgm={bgm}
              emotionType={result.emotion}
              audioPath={result.audioPath}
              sceneVideos={result.visualMode === "video" ? (result.sceneVideos || []) : undefined}
              onTitleChange={(title) => setResult({...result, title})}
              onScenesChange={(scenes) => setResult({...result, scenes})}
              onImagesChange={(images) => setResult({...result, sceneImages: images})}
              onVideoUpdate={(videoPath) => setResult({...result, videoPath})}
              onVideosChange={(sv) => setResult({...result, sceneVideos: sv})}
            />
          </div>
        )}
        {result.summary&&(
          <div className="bg-gray-800 rounded-lg p-4 mb-6">
            <div className="text-sm font-medium text-gray-400 mb-2">📋 3줄 요약 (복사용)</div>
            <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">{result.summary}</p>
          </div>
        )}
        {result.hashtags&&(
          <div className="bg-gray-800 rounded-lg p-4 mb-6">
            <div className="text-sm font-medium text-gray-400 mb-2"># 해시태그 (복사용)</div>
            <p className="text-sm text-blue-400 leading-relaxed select-all cursor-pointer">{result.hashtags}</p>
          </div>
        )}
        <div className="flex gap-3">
          {result.videoPath && <a href={url} download className="flex-1 py-3 bg-blue-600 hover:bg-blue-500 rounded-lg font-medium text-center transition">⬇️ 다운로드</a>}
          {result.scriptPath && (
            <button
              onClick={async () => {
                const res = await fetch("/api/project/save", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    name: result.title,
                    script_path: result.scriptPath,
                    image_paths: Object.fromEntries((result.sceneImages || []).map(i => [i.scene_id, i.image_path])),
                    output_path: result.videoPath || null,
                  }),
                });
                if (res.ok) { const d = await res.json(); alert(`프로젝트 저장 완료 (ID: ${d.project_id})`); }
              }}
              className="py-3 px-4 bg-green-600 hover:bg-green-500 rounded-lg font-medium transition"
            >
              💾 저장
            </button>
          )}
          <button onClick={reset} className="flex-1 py-3 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium transition">🔄 새로 만들기</button>
        </div>
      </main>
    );
  }

  return (
    <main className="max-w-2xl mx-auto px-4 py-8">
      <header className="text-center mb-8">
        <h1 className="text-3xl font-bold mb-2">ContentsMaker</h1>
        <p className="text-gray-400">인기글/자유주제 → 만화 쇼츠 자동 생성</p>
      </header>
      <div className="flex gap-2 mb-6">
        {(["image","manual","url","topic"] as const).map(t=>(
          <button key={t} onClick={()=>setTab(t)} className={`flex-1 py-3 rounded-lg font-medium transition text-sm ${tab===t?"bg-blue-600":"bg-gray-800 text-gray-400 hover:bg-gray-700"}`}>
            {t==="image"?"📸 스크린샷":t==="manual"?"✏️ 직접 입력":t==="url"?"🔗 URL":"💡 주제 입력"}
          </button>
        ))}
      </div>

      {/* Visual mode toggle */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-300 mb-2">비주얼 모드</label>
        <div className="grid grid-cols-2 gap-2">
          <button onClick={()=>setVisualMode("manga")} className={`py-2 rounded-lg text-sm transition ${visualMode==="manga"?"bg-blue-600 ring-2 ring-blue-400":"bg-gray-800 text-gray-400 hover:bg-gray-700"}`}>🖼️ 이미지 쇼츠 ~$0.005/씬</button>
          <button onClick={()=>setVisualMode("video")} className={`py-2 rounded-lg text-sm transition ${visualMode==="video"?"bg-purple-600 ring-2 ring-purple-400":"bg-gray-800 text-gray-400 hover:bg-gray-700"}`}>🎥 영상 쇼츠 ~$0.05/씬</button>
        </div>
      </div>

      {/* Image style selector (manga mode only) */}
      {visualMode==="manga"&&<div className="mb-4">
        <label className="block text-sm font-medium text-gray-300 mb-2">이미지 스타일</label>
        <div className="grid grid-cols-4 gap-2">
          {([["webtoon","🎨 웹툰"],["3d_pixar","🧊 3D Pixar"],["realistic","📷 실사풍"],["anime","✨ 애니메"]] as const).map(([val,label])=>(
            <button key={val} onClick={()=>setImageStyle(val)} className={`py-2 rounded-lg text-xs transition ${imageStyle===val?"bg-indigo-600 ring-2 ring-indigo-400":"bg-gray-800 text-gray-400 hover:bg-gray-700"}`}>{label}</button>
          ))}
        </div>
      </div>}

      {/* Video provider selector (video mode only) */}
      {visualMode==="video"&&<div className="mb-4">
        <label className="block text-sm font-medium text-gray-300 mb-2">영상 생성 제공업체</label>
        <div className="grid grid-cols-3 gap-2">
          <button onClick={()=>setVideoProvider("freepik")} className={`py-2 rounded-lg text-xs transition ${videoProvider==="freepik"?"bg-indigo-600 ring-2 ring-indigo-400":"bg-gray-800 text-gray-400 hover:bg-gray-700"}`}>🎨 Freepik (구독)</button>
          <button onClick={()=>setVideoProvider("deevid")} className={`py-2 rounded-lg text-xs transition ${videoProvider==="deevid"?"bg-indigo-600 ring-2 ring-indigo-400":"bg-gray-800 text-gray-400 hover:bg-gray-700"}`}>🌐 deevid.ai (무료)</button>
          <button onClick={()=>setVideoProvider("seedance")} className={`py-2 rounded-lg text-xs transition ${videoProvider==="seedance"?"bg-indigo-600 ring-2 ring-indigo-400":"bg-gray-800 text-gray-400 hover:bg-gray-700"}`}>⚡ Seedance API</button>
        </div>
        {videoProvider==="freepik"&&<p className="mt-2 text-xs text-gray-500">⚠️ 사전에 터미널에서 <code className="text-yellow-400">python3 -m src.main freepik_login</code> 실행 필요</p>}
        {videoProvider==="deevid"&&<p className="mt-2 text-xs text-gray-500">⚠️ 사전에 터미널에서 <code className="text-yellow-400">python3 -m src.main deevid_login</code> 실행 필요</p>}
      </div>}

      {/* Image provider selector (manga mode only) */}
      {visualMode==="manga"&&<div className="mb-4">
        <label className="block text-sm font-medium text-gray-300 mb-2">이미지 생성 제공업체</label>
        <div className="grid grid-cols-2 gap-2">
          <button onClick={()=>setImageProvider("freepik")} className={`py-2 rounded-lg text-xs transition ${imageProvider==="freepik"?"bg-indigo-600 ring-2 ring-indigo-400":"bg-gray-800 text-gray-400 hover:bg-gray-700"}`}>🎨 Freepik 무제한 (Premium+)</button>
          <button onClick={()=>setImageProvider("gpt")} className={`py-2 rounded-lg text-xs transition ${imageProvider==="gpt"?"bg-indigo-600 ring-2 ring-indigo-400":"bg-gray-800 text-gray-400 hover:bg-gray-700"}`}>💎 GPT Image ($0.005/씬)</button>
        </div>
        {imageProvider==="freepik"&&<p className="mt-2 text-xs text-gray-500">⚠️ 사전에 터미널에서 <code className="text-yellow-400">python3 -m src.main freepik_login</code> 실행 필요. 실패 시 GPT로 자동 폴백</p>}
        {imageProvider==="gpt"&&<p className="mt-2 text-xs text-gray-500">💡 레퍼런스 이미지 지원 (일관된 캐릭터/스타일). <code className="text-yellow-400">OPENAI_API_KEY</code> 필요</p>}
      </div>}

      {/* Common title field for image/url tabs */}
      {(tab==="image"||tab==="url")&&(
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-300 mb-1">영상 제목 (선택)</label>
          <input value={customTitle} onChange={e=>setCustomTitle(e.target.value)} placeholder="비워두면 AI가 자동 생성" className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"/>
        </div>
      )}

      {/* Image tab */}
      <div className="space-y-4" style={{display:tab==="image"?"block":"none"}}>
        <div onDragOver={e=>{e.preventDefault();setDragOver(true)}} onDragLeave={()=>setDragOver(false)}
          onDrop={e=>{e.preventDefault();setDragOver(false);setFiles(p=>[...p,...Array.from(e.dataTransfer.files).filter(f=>f.type.startsWith("image/"))])}}
          onClick={()=>document.getElementById("fi")?.click()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition ${dragOver?"border-blue-500 bg-blue-500/10":"border-gray-600 hover:border-gray-500"}`}>
          <div className="text-4xl mb-3">📸</div>
          <p className="text-lg font-medium mb-1">블라인드 스크린샷을 드래그하세요</p>
          <p className="text-gray-500 text-sm">또는 클릭하여 파일 선택 (여러 장 가능)</p>
          <input id="fi" type="file" accept="image/*" multiple onChange={e=>{if(e.target.files)setFiles(p=>[...p,...Array.from(e.target.files!)])}} className="hidden"/>
        </div>
        {files.length>0&&(
          <div className="space-y-2">
            {files.map((f,i)=>(<div key={i} className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-2">
              <span className="text-sm truncate">{f.name}</span>
              <button onClick={()=>setFiles(files.filter((_,j)=>j!==i))} className="text-red-400 ml-2">✕</button>
            </div>))}
          </div>
        )}
        <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={bgm} onChange={e=>setBgm(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🎵 배경음악 넣기</span></label>
        <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={ytUpload} onChange={e=>setYtUpload(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">📺 YouTube 업로드</span></label>
        <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={ttUpload} onChange={e=>setTtUpload(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🎵 TikTok 업로드 (Draft)</span></label>
        <div className="flex gap-2">
          <button onClick={()=>{if(!files.length)return;const fd=new FormData();fd.set("mode","image");fd.set("bgm",bgm?"on":"off");fd.set("yt",ytUpload?"on":"off");fd.set("tt",ttUpload?"on":"off");fd.set("visualMode",visualMode);fd.set("imageStyle",imageStyle);fd.set("videoProvider",videoProvider);fd.set("imageProvider",imageProvider);if(customTitle.trim())fd.set("customTitle",customTitle.trim());files.forEach(f=>fd.append("images",f));startAnalyze(fd)}}
            disabled={!files.length} className={`flex-1 py-3 rounded-lg font-medium transition ${files.length?"bg-blue-600 hover:bg-blue-500":"bg-gray-700 text-gray-500 cursor-not-allowed"}`}>
            🎬 영상 생성 {files.length>0?`(${files.length}장)`:""}
          </button>
          <button onClick={()=>{if(!files.length)return;const fd=new FormData();fd.set("mode","image");fd.set("bgm","off");fd.set("yt","off");fd.set("tt","off");fd.set("dryRun","on");if(customTitle.trim())fd.set("customTitle",customTitle.trim());files.forEach(f=>fd.append("images",f));generate(fd)}}
            disabled={!files.length} className={`py-3 px-4 rounded-lg font-medium transition ${files.length?"bg-yellow-600 hover:bg-yellow-500":"bg-gray-700 text-gray-500 cursor-not-allowed"}`}>
            🧪 테스트
          </button>
        </div>
      </div>

      {/* Manual tab */}
      <div className="space-y-4" style={{display:tab==="manual"?"block":"none"}}>
        <div><label className="block text-sm font-medium text-gray-300 mb-1">제목 *</label>
          <input value={title} onChange={e=>setTitle(e.target.value)} placeholder="블라인드 게시글 제목" className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"/></div>
        <div><label className="block text-sm font-medium text-gray-300 mb-1">본문 *</label>
          <textarea value={body} onChange={e=>setBody(e.target.value)} placeholder="본문 내용" rows={8} className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none resize-y"/></div>
        <div><label className="block text-sm font-medium text-gray-300 mb-1">댓글 (선택)</label>
          {comments.map((c,i)=>(<div key={i} className="flex gap-2 mb-2">
            <input value={c} onChange={e=>{const u=[...comments];u[i]=e.target.value;setComments(u)}} placeholder={`댓글 ${i+1}`} className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none text-sm"/>
            {comments.length>1&&<button onClick={()=>setComments(comments.filter((_,j)=>j!==i))} className="text-red-400 px-2">✕</button>}
          </div>))}
          <button onClick={()=>setComments([...comments,""])} className="text-sm text-blue-400">+ 댓글 추가</button></div>
        <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={bgm} onChange={e=>setBgm(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🎵 배경음악 넣기</span></label>
        <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={ytUpload} onChange={e=>setYtUpload(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">📺 YouTube 업로드</span></label>
        <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={ttUpload} onChange={e=>setTtUpload(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🎵 TikTok 업로드 (Draft)</span></label>
        <div className="flex gap-2">
          <button onClick={()=>{if(!title.trim()||!body.trim())return;const fd=new FormData();fd.set("mode","manual");fd.set("bgm",bgm?"on":"off");fd.set("yt",ytUpload?"on":"off");fd.set("tt",ttUpload?"on":"off");fd.set("visualMode",visualMode);fd.set("imageStyle",imageStyle);fd.set("videoProvider",videoProvider);fd.set("imageProvider",imageProvider);fd.set("title",title);fd.set("body",body);fd.set("comments",JSON.stringify(comments.filter(c=>c.trim())));startAnalyze(fd)}}
            disabled={!title.trim()||!body.trim()} className={`flex-1 py-3 rounded-lg font-medium transition ${title.trim()&&body.trim()?"bg-blue-600 hover:bg-blue-500":"bg-gray-700 text-gray-500 cursor-not-allowed"}`}>
            🎬 영상 생성
          </button>
          <button onClick={()=>{if(!title.trim()||!body.trim())return;const fd=new FormData();fd.set("mode","manual");fd.set("bgm","off");fd.set("yt","off");fd.set("tt","off");fd.set("dryRun","on");fd.set("title",title);fd.set("body",body);fd.set("comments",JSON.stringify(comments.filter(c=>c.trim())));generate(fd)}}
            disabled={!title.trim()||!body.trim()} className={`py-3 px-4 rounded-lg font-medium transition ${title.trim()&&body.trim()?"bg-yellow-600 hover:bg-yellow-500":"bg-gray-700 text-gray-500 cursor-not-allowed"}`}>
            🧪 테스트
          </button>
        </div>
      </div>

      {/* URL tab */}
      <div className="space-y-4" style={{display:tab==="url"?"block":"none"}}>
        <div><label className="block text-sm font-medium text-gray-300 mb-1">게시글 URL *</label>
          <input value={urlInput} onChange={e=>setUrlInput(e.target.value)} placeholder="https://gall.dcinside.com/... 또는 cafe.naver.com/..." className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"/>
          <p className="text-gray-500 text-xs mt-1">지원: 디시인사이드, 네이트판, 네이버 카페</p>
        </div>
        <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={bgm} onChange={e=>setBgm(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🎵 배경음악 넣기</span></label>
        <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={ytUpload} onChange={e=>setYtUpload(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">📺 YouTube 업로드</span></label>
        <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={ttUpload} onChange={e=>setTtUpload(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🎵 TikTok 업로드 (Draft)</span></label>
        <div className="flex gap-2">
          <button onClick={()=>{if(!urlInput.trim())return;const fd=new FormData();fd.set("mode","url");fd.set("bgm",bgm?"on":"off");fd.set("yt",ytUpload?"on":"off");fd.set("tt",ttUpload?"on":"off");fd.set("visualMode",visualMode);fd.set("imageStyle",imageStyle);fd.set("videoProvider",videoProvider);fd.set("imageProvider",imageProvider);fd.set("url",urlInput.trim());if(customTitle.trim())fd.set("customTitle",customTitle.trim());startAnalyze(fd)}}
            disabled={!urlInput.trim()} className={`flex-1 py-3 rounded-lg font-medium transition ${urlInput.trim()?"bg-blue-600 hover:bg-blue-500":"bg-gray-700 text-gray-500 cursor-not-allowed"}`}>
            🎬 영상 생성
          </button>
          <button onClick={()=>{if(!urlInput.trim())return;const fd=new FormData();fd.set("mode","url");fd.set("bgm","off");fd.set("yt","off");fd.set("tt","off");fd.set("dryRun","on");fd.set("url",urlInput.trim());if(customTitle.trim())fd.set("customTitle",customTitle.trim());generate(fd)}}
            disabled={!urlInput.trim()} className={`py-3 px-4 rounded-lg font-medium transition ${urlInput.trim()?"bg-yellow-600 hover:bg-yellow-500":"bg-gray-700 text-gray-500 cursor-not-allowed"}`}>
            🧪 테스트
          </button>
        </div>
      </div>
      {/* Topic tab */}
      <div className="space-y-4" style={{display:tab==="topic"?"block":"none"}}>
        <div><label className="block text-sm font-medium text-gray-300 mb-1">주제 * (5자 이상)</label>
          <input value={topicText} onChange={e=>setTopicText(e.target.value)} placeholder="예: 즐겨 먹던 과자들의 배신" className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"/></div>
        <div><label className="block text-sm font-medium text-gray-300 mb-1">콘텐츠 스타일</label>
          <div className="flex gap-2">
            {([["narration","🎙️ 나레이션"],["skit","🎭 스킷/콩트"],["review","📝 리뷰"]] as const).map(([val,label])=>(
              <button key={val} onClick={()=>setContentStyle(val)} className={`flex-1 py-2 rounded-lg text-sm transition ${contentStyle===val?"bg-purple-600":"bg-gray-800 text-gray-400 hover:bg-gray-700"}`}>{label}</button>
            ))}
          </div>
        </div>
        <div><label className="block text-sm font-medium text-gray-300 mb-1">톤/분위기 (선택)</label>
          <input value={tone} onChange={e=>setTone(e.target.value)} placeholder="예: 재밌게, 심각하게, 감성적으로" className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"/></div>
        <div><label className="block text-sm font-medium text-gray-300 mb-1">추가 설명 (선택)</label>
          <textarea value={details} onChange={e=>setDetails(e.target.value)} placeholder="AI에게 전달할 추가 정보" rows={3} className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none resize-y"/></div>
        <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={bgm} onChange={e=>setBgm(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🎵 배경음악 넣기</span></label>
        <div className="flex gap-2">
          <button onClick={()=>{if(topicText.trim().length<5)return;const fd=new FormData();fd.set("mode","topic");fd.set("bgm",bgm?"on":"off");fd.set("yt","off");fd.set("tt","off");fd.set("visualMode",visualMode);fd.set("imageStyle",imageStyle);fd.set("videoProvider",videoProvider);fd.set("imageProvider",imageProvider);fd.set("topic",topicText.trim());fd.set("contentStyle",contentStyle);fd.set("tone",tone);fd.set("details",details);startAnalyze(fd)}}
            disabled={topicText.trim().length<5} className={`flex-1 py-3 rounded-lg font-medium transition ${topicText.trim().length>=5?"bg-blue-600 hover:bg-blue-500":"bg-gray-700 text-gray-500 cursor-not-allowed"}`}>
            🎬 영상 생성
          </button>
          <button onClick={()=>{if(topicText.trim().length<5)return;const fd=new FormData();fd.set("mode","topic");fd.set("bgm","off");fd.set("yt","off");fd.set("tt","off");fd.set("dryRun","on");fd.set("topic",topicText.trim());fd.set("contentStyle",contentStyle);fd.set("tone",tone);fd.set("details",details);generate(fd)}}
            disabled={topicText.trim().length<5} className={`py-3 px-4 rounded-lg font-medium transition ${topicText.trim().length>=5?"bg-yellow-600 hover:bg-yellow-500":"bg-gray-700 text-gray-500 cursor-not-allowed"}`}>
            🧪 테스트
          </button>
        </div>
      </div>
      {error&&<div className="mt-4 p-4 bg-red-900/50 border border-red-500 rounded-lg text-red-200">{error}</div>}
    </main>
  );
}
