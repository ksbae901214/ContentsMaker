"use client";
import { useState, useEffect } from "react";

type Status = "idle" | "processing" | "done" | "error";
interface JobResult { videoPath: string; title: string; emotion: string; duration: number; imageCount: number; cost: number; youtubeUrl?: string; }
interface Stats { imageCount: number; videoCount: number; audioCount: number; scriptCount: number; imageCost: number; videoSizeMB: number; }
const EL: Record<string, string> = { funny: "😂 재밌음", touching: "🥹 감동", angry: "😤 분노", relatable: "🤝 공감" };

export default function Home() {
  const [tab, setTab] = useState<"image"|"manual"|"url">("image");
  const [status, setStatus] = useState<Status>("idle");
  const [progress, setProgress] = useState<string[]>([]);
  const [result, setResult] = useState<JobResult|null>(null);
  const [error, setError] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [comments, setComments] = useState([""]);
  const [stats, setStats] = useState<Stats|null>(null);
  const [bgm, setBgm] = useState(true);
  const [ytUpload, setYtUpload] = useState(false);
  const [urlInput, setUrlInput] = useState("");

  const loadStats = () => { fetch("/api/stats").then(r=>r.json()).then(setStats).catch(()=>{}); };
  useEffect(()=>{ loadStats(); }, []);

  const generate = async (fd: FormData) => {
    setStatus("processing"); setProgress([]); setResult(null); setError("");
    try {
      const res = await fetch("/api/generate", { method: "POST", body: fd });
      const reader = res.body?.getReader();
      if (!reader) throw new Error("스트림 열기 실패");
      const dec = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        for (const line of dec.decode(value).split("\n").filter(l => l.startsWith("data: "))) {
          try {
            const d = JSON.parse(line.slice(6));
            if (d.type === "progress") setProgress(p => [...p, d.message]);
            else if (d.type === "done") { setResult(d.result); setStatus("done"); }
            else if (d.type === "error") throw new Error(d.message);
          } catch (e: any) { if (!e.message?.includes("JSON")) throw e; }
        }
      }
    } catch (e: any) { setError(e.message); setStatus("error"); }
  };

  const reset = () => { setStatus("idle"); setResult(null); setProgress([]); setFiles([]); setError(""); };

  if (status === "processing") return (
    <main className="max-w-2xl mx-auto px-4 py-8">
      <div className="text-center py-8">
        <div className="text-5xl mb-4 animate-bounce">🎬</div>
        <h2 className="text-xl font-bold mb-2">영상 생성 중...</h2>
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

  if (status === "done" && result) {
    const url = `/api/download?path=${encodeURIComponent(result.videoPath)}`;
    return (
      <main className="max-w-2xl mx-auto px-4 py-8">
        <div className="text-center mb-6"><div className="text-5xl mb-3">🎉</div><h2 className="text-2xl font-bold">영상 생성 완료!</h2></div>
        <div className="bg-gray-900 rounded-xl overflow-hidden flex justify-center mb-6">
          <video src={url} controls className="max-h-[500px]" style={{aspectRatio:"9/16",maxWidth:"300px"}}/>
        </div>
        <div className="bg-gray-800 rounded-lg p-4 space-y-2 text-sm mb-6">
          <div className="flex justify-between"><span className="text-gray-400">제목</span><span>{result.title}</span></div>
          <div className="flex justify-between"><span className="text-gray-400">감정</span><span>{EL[result.emotion]||result.emotion}</span></div>
          <div className="flex justify-between"><span className="text-gray-400">길이</span><span>{result.duration}초</span></div>
          <div className="flex justify-between"><span className="text-gray-400">만화</span><span>{result.imageCount}장</span></div>
          <div className="flex justify-between"><span className="text-gray-400">GPT API 비용</span><span className="text-green-400">${result.cost.toFixed(3)}</span></div>
          {result.youtubeUrl&&<div className="flex justify-between"><span className="text-gray-400">YouTube</span><a href={result.youtubeUrl} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">{result.youtubeUrl}</a></div>}
        </div>
        <div className="flex gap-3">
          <a href={url} download className="flex-1 py-3 bg-blue-600 hover:bg-blue-500 rounded-lg font-medium text-center transition">⬇️ 다운로드</a>
          <button onClick={reset} className="flex-1 py-3 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium transition">🔄 새로 만들기</button>
        </div>
      </main>
    );
  }

  return (
    <main className="max-w-2xl mx-auto px-4 py-8">
      <header className="text-center mb-8">
        <h1 className="text-3xl font-bold mb-2">ContentsMaker</h1>
        <p className="text-gray-400">블라인드 인기글 → 만화 쇼츠 자동 생성</p>
      </header>
      <div className="flex gap-2 mb-6">
        {(["image","manual","url"] as const).map(t=>(
          <button key={t} onClick={()=>setTab(t)} className={`flex-1 py-3 rounded-lg font-medium transition ${tab===t?"bg-blue-600":"bg-gray-800 text-gray-400 hover:bg-gray-700"}`}>
            {t==="image"?"📸 스크린샷":t==="manual"?"✏️ 직접 입력":"🔗 URL 입력"}
          </button>
        ))}
      </div>

      {tab==="url"?(
        <div className="space-y-4">
          <div><label className="block text-sm font-medium text-gray-300 mb-1">게시글 URL *</label>
            <input value={urlInput} onChange={e=>setUrlInput(e.target.value)} placeholder="https://gall.dcinside.com/... 또는 cafe.naver.com/..." className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"/>
            <p className="text-gray-500 text-xs mt-1">지원: 디시인사이드, 네이트판, 네이버 카페</p>
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={bgm} onChange={e=>setBgm(e.target.checked)} className="w-5 h-5 rounded"/>
            <span className="text-sm text-gray-300">🎵 배경음악 넣기</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={ytUpload} onChange={e=>setYtUpload(e.target.checked)} className="w-5 h-5 rounded"/>
            <span className="text-sm text-gray-300">📺 YouTube 자동 업로드</span>
          </label>
          <button onClick={()=>{if(!urlInput.trim())return;const fd=new FormData();fd.set("mode","url");fd.set("bgm",bgm?"on":"off");fd.set("yt",ytUpload?"on":"off");fd.set("url",urlInput.trim());generate(fd)}}
            disabled={!urlInput.trim()} className={`w-full py-3 rounded-lg font-medium transition ${urlInput.trim()?"bg-blue-600 hover:bg-blue-500":"bg-gray-700 text-gray-500 cursor-not-allowed"}`}>
            🎬 영상 생성하기
          </button>
        </div>
      ):tab==="image"?(
        <div>
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
            <div className="mt-4 space-y-2">
              {files.map((f,i)=>(<div key={i} className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-2">
                <span className="text-sm truncate">{f.name}</span>
                <button onClick={()=>setFiles(files.filter((_,j)=>j!==i))} className="text-red-400 ml-2">✕</button>
              </div>))}
              <label className="flex items-center gap-2 mt-3 cursor-pointer">
                <input type="checkbox" checked={bgm} onChange={e=>setBgm(e.target.checked)} className="w-5 h-5 rounded"/>
                <span className="text-sm text-gray-300">🎵 배경음악 넣기</span>
              </label>
              <button onClick={()=>{const fd=new FormData();fd.set("mode","image");fd.set("bgm",bgm?"on":"off");fd.set("yt",ytUpload?"on":"off");files.forEach(f=>fd.append("images",f));generate(fd)}}
                className="w-full mt-3 py-3 bg-blue-600 hover:bg-blue-500 rounded-lg font-medium transition">
                🎬 영상 생성하기 ({files.length}장)
              </button>
            </div>
          )}
        </div>
      ):(
        <div className="space-y-4">
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
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={bgm} onChange={e=>setBgm(e.target.checked)} className="w-5 h-5 rounded"/>
            <span className="text-sm text-gray-300">🎵 배경음악 넣기</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={ytUpload} onChange={e=>setYtUpload(e.target.checked)} className="w-5 h-5 rounded"/>
            <span className="text-sm text-gray-300">📺 YouTube 자동 업로드</span>
          </label>
          <button onClick={()=>{if(!title.trim()||!body.trim())return;const fd=new FormData();fd.set("mode","manual");fd.set("bgm",bgm?"on":"off");fd.set("yt",ytUpload?"on":"off");fd.set("title",title);fd.set("body",body);fd.set("comments",JSON.stringify(comments.filter(c=>c.trim())));generate(fd)}}
            disabled={!title.trim()||!body.trim()} className={`w-full py-3 rounded-lg font-medium transition ${title.trim()&&body.trim()?"bg-blue-600 hover:bg-blue-500":"bg-gray-700 text-gray-500 cursor-not-allowed"}`}>
            🎬 영상 생성하기
          </button>
        </div>
      )}
      {error&&<div className="mt-4 p-4 bg-red-900/50 border border-red-500 rounded-lg text-red-200">{error}</div>}
    </main>
  );
}
