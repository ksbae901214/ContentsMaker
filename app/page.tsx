"use client";
import { useState, useEffect } from "react";
import { SceneEditor } from "./components/SceneEditor";
import { ScriptReviewer } from "./components/ScriptReviewer";

type Status = "idle" | "processing" | "reviewing" | "done" | "error";
interface SceneImage { scene_id: number; image_path: string; prompt: string; }
interface SceneData { id: number; timestamp: number; duration: number; type: string; text: string; voice_text: string; emphasis: string; }
interface JobResult { videoPath: string; thumbnailPath?: string; title: string; emotion: string; duration: number; imageCount: number; videoCount?: number; cost: number; visualMode?: string; imageStyle?: string; sourceType?: string; youtubeUrl?: string; tiktokStatus?: string; summary?: string; hashtags?: string; scriptPath?: string; audioPath?: string; sceneImages?: SceneImage[]; sceneVideos?: {scene_id:number;video_path:string}[]; scenes?: SceneData[]; dryRun?: boolean; }
// Phase 1 (analyze-only) result held during the reviewing state.
interface PortraitCandidate { path: string; filename: string }
interface ReviewPayload {
  phase: "analyzed";
  title: string;
  emotion: string;
  duration: number;
  scriptPath: string;
  scenes: SceneData[];
  sourceType?: string;
  celebrityName?: string;
  portraitCandidates?: PortraitCandidate[];
}
interface Stats { imageCount: number; videoCount: number; audioCount: number; scriptCount: number; imageCost: number; videoSizeMB: number; }
const EL: Record<string, string> = { funny: "😂 재밌음", touching: "🥹 감동", angry: "😤 분노", relatable: "🤝 공감" };

export default function Home() {
  const [tab, setTab] = useState<"image"|"manual"|"url"|"topic"|"political"|"natv_clip"|"celebrity">("image");
  const [natvClipUrl, setNavtClipUrl] = useState("");
  const [natvUseTts, setNavtUseTts] = useState(false);
  const [natvTone, setNavtTone] = useState<"angry"|"funny"|"touching"|"relatable">("angry");
  const [celebrityName, setCelebrityName] = useState("");
  const [celebrityQualifier, setCelebrityQualifier] = useState("");
  const [celebrityNoVideo, setCelebrityNoVideo] = useState(false);
  const [celebrityNoImages, setCelebrityNoImages] = useState(false);
  const [celebritySymbolicImages, setCelebritySymbolicImages] = useState(false);
  const [topicText, setTopicText] = useState("");
  const [contentStyle, setContentStyle] = useState<"narration"|"skit"|"review">("narration");
  const [politicalUrl, setPoliticalUrl] = useState("");
  const [clipStart, setClipStart] = useState("");
  const [clipEnd, setClipEnd] = useState("");
  const [politicalTone, setPoliticalTone] = useState("");
  const [politicalDetails, setPoliticalDetails] = useState("");
  // Lawmaker selection flow
  interface LawmakerItem { name: string; party: string; role: string; description: string; emoji: string; searchQuery: string; }
  interface VideoItem { title: string; url: string; duration_seconds: number; view_count: number; upload_date: string; channel: string; thumbnail: string; duration_label: string; date_label: string; }
  interface IdeaItem { title: string; hook: string; angle: string; natvKeywords: string; }
  const [lawmakers, setLawmakers] = useState<LawmakerItem[]>([]);
  const [selectedLawmaker, setSelectedLawmaker] = useState<LawmakerItem | null>(null);
  const [lawmakerVideos, setLawmakerVideos] = useState<VideoItem[]>([]);
  const [videosLoading, setVideosLoading] = useState(false);
  const [videosError, setVideosError] = useState("");
  const [selectedVideoTitle, setSelectedVideoTitle] = useState("");
  const [videoIdeas, setVideoIdeas] = useState<IdeaItem[]>([]);
  const [selectedIdea, setSelectedIdea] = useState<IdeaItem | null>(null);
  const [ideasLoading, setIdeasLoading] = useState(false);
  const [ideasError, setIdeasError] = useState("");
  const [natvVideos, setNavtvVideos] = useState<VideoItem[]>([]);
  const [natvLoading, setNavtvLoading] = useState(false);
  const [natvError, setNavtvError] = useState("");
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
  const [selectedPortraitPath, setSelectedPortraitPath] = useState<string>("");
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
  const [transitions, setTransitions] = useState(true);
  const [sfx, setSfx] = useState(true);
  const [ytUpload, setYtUpload] = useState(false);
  const [ttUpload, setTtUpload] = useState(false);
  const [urlInput, setUrlInput] = useState("");
  const [customTitle, setCustomTitle] = useState("");

  const loadStats = () => { fetch("/api/stats").then(r=>r.json()).then(setStats).catch(()=>{}); };
  useEffect(()=>{ loadStats(); }, []);
  useEffect(()=>{ fetch("/api/lawmaker/list").then(r=>r.json()).then(d=>setLawmakers(d.lawmakers||[])).catch(()=>{}); }, []);

  const selectLawmaker = async (lm: LawmakerItem) => {
    setSelectedLawmaker(lm);
    setLawmakerVideos([]);
    setVideosError("");
    setVideoIdeas([]);
    setSelectedIdea(null);
    setIdeasError("");
    setVideosLoading(true);
    setIdeasLoading(true);
    let titles: string[] = [];
    try {
      const r = await fetch(`/api/lawmaker/videos?name=${encodeURIComponent(lm.name)}&source=all&limit=10`);
      const d = await r.json();
      if (d.error) setVideosError(d.error);
      else {
        setLawmakerVideos(d.videos || []);
        titles = (d.videos || []).map((v: VideoItem) => v.title).filter(Boolean);
      }
    } catch { setVideosError("영상 검색 실패"); }
    finally { setVideosLoading(false); }

    if (titles.length === 0) { setIdeasLoading(false); return; }
    try {
      const r = await fetch("/api/lawmaker/ideas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: lm.name, titles }),
      });
      const d = await r.json();
      if (d.error) setIdeasError(d.error);
      else setVideoIdeas(d.ideas || []);
    } catch { setIdeasError("아이디어 생성 실패"); }
    finally { setIdeasLoading(false); }
  };

  const selectIdea = async (idea: IdeaItem) => {
    setSelectedIdea(idea);
    setNavtvVideos([]);
    setNavtvError("");
    setNavtvLoading(true);
    try {
      const r = await fetch(
        `/api/lawmaker/videos?name=${encodeURIComponent(selectedLawmaker?.name || "")}&natvOnly=true&keywords=${encodeURIComponent(idea.natvKeywords)}&limit=10`
      );
      const d = await r.json();
      if (d.error) setNavtvError(d.error);
      else setNavtvVideos(d.videos || []);
    } catch { setNavtvError("NATV 영상 검색 실패"); }
    finally { setNavtvLoading(false); }
  };

  const pickVideo = (v: VideoItem) => {
    setPoliticalUrl(v.url);
    setSelectedVideoTitle(v.title);
  };

  const resetPoliticalFlow = () => {
    setSelectedLawmaker(null);
    setLawmakerVideos([]);
    setPoliticalUrl("");
    setSelectedVideoTitle("");
    setVideosError("");
    setVideoIdeas([]);
    setSelectedIdea(null);
    setIdeasError("");
    setNavtvVideos([]);
    setNavtvError("");
  };

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
            const rev = d.result as ReviewPayload;
            setReview(rev);
            // 후보 이미지가 있으면 첫 번째를 기본 선택
            const firstPortrait = rev.portraitCandidates?.[0]?.path || "";
            setSelectedPortraitPath(firstPortrait);
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
    [
      "visualMode","imageStyle","videoProvider","imageProvider",
      "bgm","transitions","sfx","yt","tt",
      // Celebrity mode extras (유명인 탭): Phase 2 재전송 시 필요
      "celebrityName","celebrityQualifier","noVideo","noImages","symbolicImages","celebritySource",
    ].forEach(k => {
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
    // 검수 화면에서 선택·업로드한 인물 이미지를 Phase 2에 전달
    if (selectedPortraitPath) fd.set("portraitPath", selectedPortraitPath);
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
      portraitCandidates={review.portraitCandidates}
      selectedPortraitPath={selectedPortraitPath}
      onPortraitChange={(path) => setSelectedPortraitPath(path)}
      celebrityName={review.celebrityName || ""}
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
              imageStyle={result.imageStyle || imageStyle}
              sceneVideos={(result.sceneVideos && result.sceneVideos.length > 0) ? result.sceneVideos : (result.visualMode === "video" ? [] : undefined)}
              initialUseTransitions={transitions}
              initialUseSfx={sfx}
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
        {result.thumbnailPath && (
          <div className="mb-4">
            <p className="text-xs text-gray-400 mb-1">썸네일 미리보기 (1280×720)</p>
            <img
              src={`/api/download?path=${encodeURIComponent(result.thumbnailPath)}`}
              alt="thumbnail"
              className="w-full rounded-lg border border-gray-700"
              style={{maxHeight: "200px", objectFit: "cover"}}
            />
          </div>
        )}
        <div className="flex gap-3">
          {result.videoPath && <a href={url} download className="flex-1 py-3 bg-blue-600 hover:bg-blue-500 rounded-lg font-medium text-center transition">⬇️ 다운로드</a>}
          {result.thumbnailPath && (
            <a
              href={`/api/download?path=${encodeURIComponent(result.thumbnailPath)}`}
              download
              className="py-3 px-4 bg-yellow-600 hover:bg-yellow-500 rounded-lg font-medium text-center transition"
            >🖼️ 썸네일</a>
          )}
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
        {(["image","manual","url","topic","political","natv_clip","celebrity"] as const).map(t=>(
          <button key={t} onClick={()=>setTab(t)} className={`flex-1 py-2.5 rounded-lg font-medium transition text-xs ${tab===t?"bg-blue-600":"bg-gray-800 text-gray-400 hover:bg-gray-700"}`}>
            {t==="image"?"📸 스크린샷":t==="manual"?"✏️ 직접 입력":t==="url"?"🔗 URL":t==="topic"?"💡 주제":t==="political"?"🎙️ 정치 해설":t==="natv_clip"?"📺 NATV 클립":"👤 유명인"}
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
        <div className="flex flex-wrap gap-x-4 gap-y-2">
          <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={bgm} onChange={e=>setBgm(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🎵 배경음악 넣기</span></label>
          <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={transitions} onChange={e=>setTransitions(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🎬 화면 전환 효과</span></label>
          <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={sfx} onChange={e=>setSfx(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🔊 효과음</span></label>
        </div>
        <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={ytUpload} onChange={e=>setYtUpload(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">📺 YouTube 업로드</span></label>
        <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={ttUpload} onChange={e=>setTtUpload(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🎵 TikTok 업로드 (Draft)</span></label>
        <div className="flex gap-2">
          <button onClick={()=>{if(!files.length)return;const fd=new FormData();fd.set("mode","image");fd.set("bgm",bgm?"on":"off");fd.set("transitions",transitions?"on":"off");fd.set("sfx",sfx?"on":"off");fd.set("yt",ytUpload?"on":"off");fd.set("tt",ttUpload?"on":"off");fd.set("visualMode",visualMode);fd.set("imageStyle",imageStyle);fd.set("videoProvider",videoProvider);fd.set("imageProvider",imageProvider);if(customTitle.trim())fd.set("customTitle",customTitle.trim());files.forEach(f=>fd.append("images",f));startAnalyze(fd)}}
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
        <div className="flex flex-wrap gap-x-4 gap-y-2">
          <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={bgm} onChange={e=>setBgm(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🎵 배경음악 넣기</span></label>
          <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={transitions} onChange={e=>setTransitions(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🎬 화면 전환 효과</span></label>
          <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={sfx} onChange={e=>setSfx(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🔊 효과음</span></label>
        </div>
        <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={ytUpload} onChange={e=>setYtUpload(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">📺 YouTube 업로드</span></label>
        <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={ttUpload} onChange={e=>setTtUpload(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🎵 TikTok 업로드 (Draft)</span></label>
        <div className="flex gap-2">
          <button onClick={()=>{if(!title.trim()||!body.trim())return;const fd=new FormData();fd.set("mode","manual");fd.set("bgm",bgm?"on":"off");fd.set("transitions",transitions?"on":"off");fd.set("sfx",sfx?"on":"off");fd.set("yt",ytUpload?"on":"off");fd.set("tt",ttUpload?"on":"off");fd.set("visualMode",visualMode);fd.set("imageStyle",imageStyle);fd.set("videoProvider",videoProvider);fd.set("imageProvider",imageProvider);fd.set("title",title);fd.set("body",body);fd.set("comments",JSON.stringify(comments.filter(c=>c.trim())));startAnalyze(fd)}}
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
        <div className="flex flex-wrap gap-x-4 gap-y-2">
          <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={bgm} onChange={e=>setBgm(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🎵 배경음악 넣기</span></label>
          <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={transitions} onChange={e=>setTransitions(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🎬 화면 전환 효과</span></label>
          <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={sfx} onChange={e=>setSfx(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🔊 효과음</span></label>
        </div>
        <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={ytUpload} onChange={e=>setYtUpload(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">📺 YouTube 업로드</span></label>
        <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={ttUpload} onChange={e=>setTtUpload(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🎵 TikTok 업로드 (Draft)</span></label>
        <div className="flex gap-2">
          <button onClick={()=>{if(!urlInput.trim())return;const fd=new FormData();fd.set("mode","url");fd.set("bgm",bgm?"on":"off");fd.set("transitions",transitions?"on":"off");fd.set("sfx",sfx?"on":"off");fd.set("yt",ytUpload?"on":"off");fd.set("tt",ttUpload?"on":"off");fd.set("visualMode",visualMode);fd.set("imageStyle",imageStyle);fd.set("videoProvider",videoProvider);fd.set("imageProvider",imageProvider);fd.set("url",urlInput.trim());if(customTitle.trim())fd.set("customTitle",customTitle.trim());startAnalyze(fd)}}
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
        <div className="flex flex-wrap gap-x-4 gap-y-2">
          <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={bgm} onChange={e=>setBgm(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🎵 배경음악 넣기</span></label>
          <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={transitions} onChange={e=>setTransitions(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🎬 화면 전환 효과</span></label>
          <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={sfx} onChange={e=>setSfx(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🔊 효과음</span></label>
        </div>
        <div className="flex gap-2">
          <button onClick={()=>{if(topicText.trim().length<5)return;const fd=new FormData();fd.set("mode","topic");fd.set("bgm",bgm?"on":"off");fd.set("transitions",transitions?"on":"off");fd.set("sfx",sfx?"on":"off");fd.set("yt","off");fd.set("tt","off");fd.set("visualMode",visualMode);fd.set("imageStyle",imageStyle);fd.set("videoProvider",videoProvider);fd.set("imageProvider",imageProvider);fd.set("topic",topicText.trim());fd.set("contentStyle",contentStyle);fd.set("tone",tone);fd.set("details",details);startAnalyze(fd)}}
            disabled={topicText.trim().length<5} className={`flex-1 py-3 rounded-lg font-medium transition ${topicText.trim().length>=5?"bg-blue-600 hover:bg-blue-500":"bg-gray-700 text-gray-500 cursor-not-allowed"}`}>
            🎬 영상 생성
          </button>
          <button onClick={()=>{if(topicText.trim().length<5)return;const fd=new FormData();fd.set("mode","topic");fd.set("bgm","off");fd.set("yt","off");fd.set("tt","off");fd.set("dryRun","on");fd.set("topic",topicText.trim());fd.set("contentStyle",contentStyle);fd.set("tone",tone);fd.set("details",details);generate(fd)}}
            disabled={topicText.trim().length<5} className={`py-3 px-4 rounded-lg font-medium transition ${topicText.trim().length>=5?"bg-yellow-600 hover:bg-yellow-500":"bg-gray-700 text-gray-500 cursor-not-allowed"}`}>
            🧪 테스트
          </button>
        </div>
      </div>
      {/* NATV 클립 tab */}
      <div className="space-y-4" style={{display:tab==="natv_clip"?"block":"none"}}>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">국회방송 YouTube URL *</label>
          <input
            value={natvClipUrl}
            onChange={e=>setNavtClipUrl(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=..."
            className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none text-sm"
          />
          <p className="text-xs text-gray-500 mt-1">NATV 국회방송 영상 URL을 붙여넣으면 자동으로 최고 임팩트 구간을 찾아 쇼츠로 만듭니다.</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">감정 톤</label>
          <div className="grid grid-cols-4 gap-2">
            {(["angry","funny","touching","relatable"] as const).map(t=>(
              <button key={t} onClick={()=>setNavtTone(t)}
                className={`py-2 rounded-lg text-xs transition ${natvTone===t?"bg-blue-600 ring-2 ring-blue-400":"bg-gray-800 text-gray-400 hover:bg-gray-700"}`}>
                {t==="angry"?"😤 분노":t==="funny"?"😂 유머":t==="touching"?"🥹 감동":"🤝 공감"}
              </button>
            ))}
          </div>
        </div>
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" checked={natvUseTts} onChange={e=>setNavtUseTts(e.target.checked)} className="w-5 h-5 rounded"/>
          <span className="text-sm text-gray-300">🎙️ TTS 음성 추가 (끄면 BGM만)</span>
        </label>
        <div className="flex flex-wrap gap-x-4 gap-y-2">
          <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={bgm} onChange={e=>setBgm(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🎵 배경음악 넣기</span></label>
          <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={transitions} onChange={e=>setTransitions(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🎬 화면 전환 효과</span></label>
          <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={sfx} onChange={e=>setSfx(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🔊 효과음</span></label>
        </div>
        <button
          onClick={()=>{
            if(!natvClipUrl.trim())return;
            const fd=new FormData();
            fd.set("mode","natv_clip");
            fd.set("youtubeUrl",natvClipUrl.trim());
            fd.set("tone",natvTone);
            fd.set("tts",natvUseTts?"on":"off");
            fd.set("bgm",bgm?"on":"off");
            fd.set("transitions",transitions?"on":"off");
            fd.set("sfx",sfx?"on":"off");
            fd.set("yt","off");fd.set("tt","off");
            generate(fd);
          }}
          disabled={!natvClipUrl.trim()}
          className={`w-full py-3 rounded-lg font-medium transition ${natvClipUrl.trim()?"bg-emerald-600 hover:bg-emerald-500":"bg-gray-700 text-gray-500 cursor-not-allowed"}`}>
          📺 NATV 클립 쇼츠 생성
        </button>
      </div>

      {/* Political tab */}
      <div className="space-y-4" style={{display:tab==="political"?"block":"none"}}>
        {/* Step 1: Lawmaker selection */}
        {!selectedLawmaker && !politicalUrl && (
          <div>
            <h3 className="text-sm font-medium text-gray-300 mb-3">인기 의원 선택</h3>
            <div className="grid grid-cols-2 gap-2 mb-3">
              {lawmakers.map(lm=>(
                <button key={lm.name} onClick={()=>selectLawmaker(lm)}
                  className="flex items-start gap-2 p-3 bg-gray-800 hover:bg-gray-700 rounded-lg text-left transition border border-gray-700 hover:border-blue-500">
                  <span className="text-2xl">{lm.emoji}</span>
                  <div className="min-w-0">
                    <div className="font-medium text-sm">{lm.name}</div>
                    <div className="text-xs text-blue-400">{lm.party}</div>
                    <div className="text-xs text-gray-400 truncate">{lm.description}</div>
                  </div>
                </button>
              ))}
            </div>
            <div className="border-t border-gray-700 pt-3">
              <p className="text-xs text-gray-500 mb-2">또는 직접 NATV URL 입력</p>
              <input value={politicalUrl} onChange={e=>setPoliticalUrl(e.target.value)} placeholder="https://youtube.com/watch?v=..." className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none text-sm"/>
            </div>
          </div>
        )}

        {/* Step 2: Loading / fallback (lawmaker selected, ideas not yet ready) */}
        {selectedLawmaker && !politicalUrl && videoIdeas.length === 0 && (
          <div>
            <div className="flex items-center gap-2 mb-4">
              <button onClick={resetPoliticalFlow} className="text-gray-400 hover:text-white text-sm">← 뒤로</button>
              <h3 className="text-sm font-medium text-gray-300">{selectedLawmaker.emoji} {selectedLawmaker.name}</h3>
            </div>

            {/* Loading spinner */}
            {(videosLoading || ideasLoading) && (
              <div className="text-center py-8 text-gray-400 text-sm">
                <div className="text-3xl mb-3 animate-pulse">🤔</div>
                <div className="font-medium text-white mb-1">AI 아이디어 생성 중...</div>
                <div className="text-xs text-gray-500">
                  {videosLoading ? "YouTube 영상 제목 수집 중 (약 30초)" : "Claude가 쇼츠 아이디어 분석 중 (약 1~2분)"}
                </div>
              </div>
            )}

            {/* Errors */}
            {ideasError && !ideasLoading && (
              <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-sm text-red-300 mb-3">
                💡 아이디어 생성 실패: {ideasError}
              </div>
            )}
            {videosError && !videosLoading && (
              <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-sm text-red-300 mb-3">
                {videosError}
              </div>
            )}

            {/* Fallback: done loading, no ideas — show raw video list */}
            {!videosLoading && !ideasLoading && (
              <>
                {lawmakerVideos.length > 0 ? (
                  <div className="mb-3">
                    <p className="text-xs text-gray-400 mb-2">
                      {ideasError ? "아이디어 생성 실패 — " : "아이디어 준비 중 — "}영상을 직접 선택할 수 있습니다:
                    </p>
                    <div className="space-y-2">
                      {lawmakerVideos.map((v, i) => (
                        <button key={i} onClick={()=>pickVideo(v)}
                          className="w-full flex gap-3 p-3 bg-gray-800 hover:bg-gray-700 rounded-lg text-left transition border border-gray-700 hover:border-blue-500">
                          {v.thumbnail && <img src={v.thumbnail} alt="" className="w-16 h-10 object-cover rounded flex-shrink-0"/>}
                          <div className="min-w-0 flex-1">
                            <div className="text-sm font-medium text-white line-clamp-2 leading-tight mb-1">{v.title}</div>
                            <div className="text-xs text-gray-400">
                              {v.channel&&<span className="mr-2">{v.channel}</span>}
                              {v.duration_label&&<span className="mr-2">⏱ {v.duration_label}</span>}
                              {v.view_count>0&&<span className="mr-2">👁 {(v.view_count/10000).toFixed(1)}만</span>}
                              {v.date_label&&<span>{v.date_label}</span>}
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                ) : !videosError && (
                  <div className="text-center py-4 text-gray-500 text-sm mb-3">검색 결과가 없습니다</div>
                )}
                <div className="border-t border-gray-700 pt-3">
                  <p className="text-xs text-gray-500 mb-2">또는 직접 NATV URL 입력</p>
                  <input onChange={e=>{if(e.target.value)setPoliticalUrl(e.target.value)}} placeholder="https://youtube.com/watch?v=..." className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none text-sm"/>
                </div>
              </>
            )}
          </div>
        )}

        {/* Step 3: Idea cards (lawmaker selected, ideas ready, no idea selected) */}
        {selectedLawmaker && !politicalUrl && videoIdeas.length > 0 && !selectedIdea && (
          <div>
            <div className="flex items-center gap-2 mb-4">
              <button onClick={resetPoliticalFlow} className="text-gray-400 hover:text-white text-sm">← 뒤로</button>
              <h3 className="text-sm font-medium text-gray-300">{selectedLawmaker.emoji} {selectedLawmaker.name} — AI 쇼츠 아이디어</h3>
            </div>
            <div className="space-y-2 mb-4">
              {videoIdeas.map((idea, i) => (
                <button key={i} onClick={()=>selectIdea(idea)}
                  className="w-full p-4 bg-gray-800 hover:bg-gray-700 rounded-lg text-left transition border border-gray-700 hover:border-purple-500">
                  <div className="text-sm font-bold text-white mb-1 leading-snug">{idea.title}</div>
                  <div className="text-xs text-purple-300 mb-1">💬 {idea.hook}</div>
                  <div className="flex items-center gap-2 text-xs text-gray-400">
                    <span className="bg-gray-700 px-2 py-0.5 rounded">{idea.angle}</span>
                    <span className="text-gray-500">🔍 {idea.natvKeywords}</span>
                  </div>
                </button>
              ))}
            </div>
            <div className="border-t border-gray-700 pt-3">
              <p className="text-xs text-gray-500 mb-2">또는 직접 NATV URL 입력</p>
              <input onChange={e=>{if(e.target.value)setPoliticalUrl(e.target.value)}} placeholder="https://youtube.com/watch?v=..." className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none text-sm"/>
            </div>
          </div>
        )}

        {/* Step 4: NATV video list (idea selected, no URL yet) */}
        {selectedLawmaker && selectedIdea && !politicalUrl && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <button onClick={()=>{setSelectedIdea(null);setNavtvVideos([]);setNavtvError("");}} className="text-gray-400 hover:text-white text-sm">← 뒤로</button>
              <h3 className="text-sm font-medium text-gray-300">국회방송 영상 선택</h3>
            </div>
            <div className="bg-gray-900 rounded-lg p-3 mb-3 border border-purple-800">
              <div className="text-xs text-purple-300 mb-0.5">선택된 아이디어</div>
              <div className="text-sm font-medium text-white leading-snug">{selectedIdea.title}</div>
              <div className="text-xs text-gray-400 mt-1">🔍 검색: {selectedIdea.natvKeywords}</div>
            </div>
            {natvLoading && (
              <div className="text-center py-6 text-gray-400 text-sm">
                <div className="animate-spin text-2xl mb-2">⏳</div>
                국회방송 영상 검색 중...
              </div>
            )}
            {natvError && (
              <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-sm text-red-300 mb-3">{natvError}</div>
            )}
            {!natvLoading && !natvError && natvVideos.length === 0 && (
              <div className="bg-yellow-900/20 border border-yellow-700 rounded-lg p-3 mb-3">
                <div className="text-sm text-yellow-300 mb-2">국회방송 영상을 찾지 못했습니다</div>
                <p className="text-xs text-gray-400">아래에서 다른 키워드로 검색하거나 직접 URL을 입력하세요.</p>
              </div>
            )}
            <div className="space-y-2 mb-3">
              {natvVideos.map((v,i)=>(
                <button key={i} onClick={()=>pickVideo(v)}
                  className="w-full flex gap-3 p-3 bg-gray-800 hover:bg-gray-700 rounded-lg text-left transition border border-gray-700 hover:border-blue-500">
                  {v.thumbnail && <img src={v.thumbnail} alt="" className="w-16 h-10 object-cover rounded flex-shrink-0"/>}
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium text-white line-clamp-2 leading-tight mb-1">{v.title}</div>
                    <div className="text-xs text-gray-400">
                      <span className="text-green-400 mr-2">📺 국회방송</span>
                      {v.duration_label&&<span className="mr-2">⏱ {v.duration_label}</span>}
                      {v.date_label&&<span>{v.date_label}</span>}
                    </div>
                  </div>
                </button>
              ))}
            </div>
            <div className="border-t border-gray-700 pt-3 space-y-3">
              <div>
                <p className="text-xs text-gray-500 mb-2">다른 키워드로 국회방송 재검색</p>
                <div className="flex gap-2">
                  <input
                    id="natv-keyword-input"
                    defaultValue={selectedIdea?.natvKeywords || ""}
                    placeholder="예: 나경원 대정부질문"
                    className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none text-sm"
                  />
                  <button
                    onClick={()=>{
                      const kw = (document.getElementById("natv-keyword-input") as HTMLInputElement)?.value?.trim();
                      if (kw && selectedIdea) selectIdea({...selectedIdea, natvKeywords: kw});
                    }}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-medium transition whitespace-nowrap"
                  >
                    🔍 재검색
                  </button>
                </div>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-2">또는 직접 NATV URL 입력</p>
                <input onChange={e=>{if(e.target.value)setPoliticalUrl(e.target.value)}} placeholder="https://youtube.com/watch?v=..." className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none text-sm"/>
              </div>
            </div>
          </div>
        )}

        {/* Step 5: URL selected — show options form */}
        {politicalUrl && (
          <div className="space-y-4">
            <div className="flex items-center justify-between bg-gray-800 rounded-lg px-3 py-2 border border-gray-700">
              <div className="min-w-0 flex-1 mr-2">
                <div className="text-xs text-gray-400 mb-0.5">선택된 영상</div>
                <div className="text-sm text-white truncate">{selectedVideoTitle || politicalUrl}</div>
              </div>
              <button onClick={()=>{setPoliticalUrl("");setSelectedVideoTitle("");}} className="text-gray-400 hover:text-white text-xs whitespace-nowrap">변경</button>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="block text-sm font-medium text-gray-300 mb-1">시작 시간 (선택)</label>
                <input value={clipStart} onChange={e=>setClipStart(e.target.value)} placeholder="0:00 또는 초" className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none text-sm"/></div>
              <div><label className="block text-sm font-medium text-gray-300 mb-1">종료 시간 (선택)</label>
                <input value={clipEnd} onChange={e=>setClipEnd(e.target.value)} placeholder="비워두면 자동(60초)" className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none text-sm"/></div>
            </div>
            <div><label className="block text-sm font-medium text-gray-300 mb-1">해설 톤 (선택)</label>
              <input value={politicalTone} onChange={e=>setPoliticalTone(e.target.value)} placeholder="예: 날카롭게, 객관적으로, 유머러스" className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"/></div>
            <div><label className="block text-sm font-medium text-gray-300 mb-1">추가 지시 (선택)</label>
              <textarea value={politicalDetails} onChange={e=>setPoliticalDetails(e.target.value)} placeholder="예: 경제 정책에 집중, 야당 시각 포함" rows={2} className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none resize-y"/></div>
            <div className="flex flex-wrap gap-x-4 gap-y-2">
          <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={bgm} onChange={e=>setBgm(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🎵 배경음악 넣기</span></label>
          <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={transitions} onChange={e=>setTransitions(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🎬 화면 전환 효과</span></label>
          <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={sfx} onChange={e=>setSfx(e.target.checked)} className="w-5 h-5 rounded"/><span className="text-sm text-gray-300">🔊 효과음</span></label>
        </div>
            <div className="flex gap-2">
              <button onClick={()=>{const fd=new FormData();fd.set("mode","political");fd.set("bgm",bgm?"on":"off");fd.set("transitions",transitions?"on":"off");fd.set("sfx",sfx?"on":"off");fd.set("yt","off");fd.set("tt","off");fd.set("youtubeUrl",politicalUrl.trim());fd.set("clipStart",clipStart);fd.set("clipEnd",clipEnd);fd.set("politicalTone",politicalTone);fd.set("politicalDetails",politicalDetails);startAnalyze(fd)}}
                className="flex-1 py-3 rounded-lg font-medium transition bg-blue-600 hover:bg-blue-500">
                🎙️ 정치 해설 생성
              </button>
              <button onClick={()=>{const fd=new FormData();fd.set("mode","political");fd.set("bgm","off");fd.set("yt","off");fd.set("tt","off");fd.set("dryRun","on");fd.set("youtubeUrl",politicalUrl.trim());fd.set("clipStart",clipStart);fd.set("clipEnd",clipEnd);fd.set("politicalTone",politicalTone);fd.set("politicalDetails",politicalDetails);generate(fd)}}
                className="py-3 px-4 rounded-lg font-medium transition bg-yellow-600 hover:bg-yellow-500">
                🧪 테스트
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Celebrity tab (Phase 9) — 학습 목적 전용 */}
      <div className="space-y-4" style={{display:tab==="celebrity"?"block":"none"}}>
        <div className="bg-yellow-900/20 border border-yellow-700 rounded-lg p-3 text-xs text-yellow-200">
          ⚠️ <strong>학습 목적 전용</strong> — 나무위키(CC BY-NC-SA) + 네이버 이미지 기반. 공개 업로드 전 초상권·저작권 직접 확인 필요. 업로드 옵션은 비활성화됩니다.
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">인물 이름 *</label>
          <input value={celebrityName} onChange={e=>setCelebrityName(e.target.value)} placeholder="예: 손흥민, 세종대왕, 유재석" className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"/>
          <p className="text-gray-500 text-xs mt-1">나무위키에 문서가 있는 인물명</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">추가 키워드 <span className="text-gray-500 text-xs">(선택)</span></label>
          <input value={celebrityQualifier} onChange={e=>setCelebrityQualifier(e.target.value)} placeholder="예: 정치인, 배우, 축구선수, 가수" className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"/>
          <p className="text-gray-500 text-xs mt-1">동명이인이 많은 이름일 때 직업·분야를 적어주세요 (나무위키 <code>이름(키워드)</code> 페이지 우선 시도 + 네이버 검색에도 결합).</p>
        </div>
        <div className="space-y-2">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={celebrityNoVideo} onChange={e=>setCelebrityNoVideo(e.target.checked)} className="w-5 h-5 rounded"/>
            <span className="text-sm text-gray-300">🖼️ Freepik 영상 변환 스킵 (정지 이미지만, 훨씬 빠름)</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={celebrityNoImages} onChange={e=>setCelebrityNoImages(e.target.checked)} className="w-5 h-5 rounded"/>
            <span className="text-sm text-gray-300">🎨 이미지 전체 스킵 (그라데이션 배경만)</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={celebritySymbolicImages} onChange={e=>setCelebritySymbolicImages(e.target.checked)} className="w-5 h-5 rounded"/>
            <span className="text-sm text-gray-300">🏛️ 씬별 상징 이미지 사용 <span className="text-gray-500 text-xs">(기본 off = 인물 대표사진 1장 공유. on = 서울대/국회의사당 등)</span></span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={bgm} onChange={e=>setBgm(e.target.checked)} className="w-5 h-5 rounded"/>
            <span className="text-sm text-gray-300">🎵 배경음악 넣기</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={transitions} onChange={e=>setTransitions(e.target.checked)} className="w-5 h-5 rounded"/>
            <span className="text-sm text-gray-300">🎬 화면 전환 효과</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={sfx} onChange={e=>setSfx(e.target.checked)} className="w-5 h-5 rounded"/>
            <span className="text-sm text-gray-300">🔊 효과음</span>
          </label>
          <div className="flex items-center gap-2 text-xs text-gray-500 pl-7">
            <span>📺 YouTube 업로드</span>
            <span className="text-gray-600">— 유명인 탭에서는 비활성화됨</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={()=>{
            if(!celebrityName.trim())return;
            const fd=new FormData();
            fd.set("mode","celebrity");
            fd.set("celebrityName",celebrityName.trim());
            if(celebrityQualifier.trim()) fd.set("celebrityQualifier",celebrityQualifier.trim());
            fd.set("noVideo",celebrityNoVideo?"on":"off");
            fd.set("noImages",celebrityNoImages?"on":"off");
            fd.set("symbolicImages",celebritySymbolicImages?"on":"off");
            fd.set("bgm",bgm?"on":"off");
            fd.set("transitions",transitions?"on":"off");
            fd.set("sfx",sfx?"on":"off");
            fd.set("yt","off");
            fd.set("tt","off");
            // Phase 2 재전송 시 route.ts가 celebrity 분기를 타도록 힌트 전달
            fd.set("celebritySource","on");
            startAnalyze(fd);
          }}
            disabled={!celebrityName.trim()}
            className={`flex-1 py-3 rounded-lg font-medium transition ${celebrityName.trim()?"bg-blue-600 hover:bg-blue-500":"bg-gray-700 text-gray-500 cursor-not-allowed"}`}>
            📝 대본 먼저 생성 → 검토 후 영상
          </button>
        </div>
        <div className="text-xs text-gray-500 space-y-1">
          <p>💡 실행 전 체크리스트:</p>
          <ul className="list-disc list-inside space-y-0.5 pl-2">
            <li><code className="text-yellow-400">NAVER_CLIENT_ID</code> / <code className="text-yellow-400">NAVER_CLIENT_SECRET</code> <code>.env.local</code>에 설정 (이미지 사용 시)</li>
            <li>터미널에서 <code className="text-yellow-400">python3 -m src.main freepik_login</code> 사전 1회 실행 (영상 모드 사용 시)</li>
          </ul>
        </div>
      </div>

      {error&&<div className="mt-4 p-4 bg-red-900/50 border border-red-500 rounded-lg text-red-200">{error}</div>}
    </main>
  );
}
