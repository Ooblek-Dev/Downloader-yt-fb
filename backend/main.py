
import os, re, tempfile, shutil, logging
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="IDM Online API - HP Save Fix", version="HP-FIX")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

ALLOWED = [r"(youtube\.com|youtu\.be|youtube-nocookie\.com)", r"(facebook\.com|fb\.watch|fb\.com)"]
def is_allowed(url): return any(re.search(p, url, re.I) for p in ALLOWED)
def cleanup(p):
    try:
        if os.path.isdir(p): shutil.rmtree(p, ignore_errors=True)
        elif os.path.isfile(p): os.remove(p)
    except: pass

def get_opts(fmt, tmpdir):
    opts = {"outtmpl": os.path.join(tmpdir, "%(title)s.%(ext)s"), "noplaylist": True, "merge_output_format":"mp4", "nocheckcertificate":True, "quiet":False}
    f = (fmt or "best").lower()
    if "best" in f and "mp4" in f: opts["format"]="bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
    elif "1080" in f: opts["format"]="bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]+bestaudio/best[height<=1080]/best"
    elif "720" in f: opts["format"]="bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best"
    elif "320" in f: opts["format"]="bestaudio/best"; opts["postprocessors"]=[{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"320"}]
    elif "192" in f or "mp3" in f: opts["format"]="bestaudio/best"; opts["postprocessors"]=[{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"192"}]
    else: opts["format"]="bestvideo+bestaudio/best"
    return opts

def do_download(url, fmt, tmpdir):
    opts = get_opts(fmt, tmpdir)
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.extract_info(url, download=True)
        files=[]
        for r,d,fns in os.walk(tmpdir):
            for fn in fns: files.append(os.path.join(r,fn))
        if not files: raise Exception("File tidak ditemukan")
        files.sort(key=lambda x: os.path.getsize(x), reverse=True)
        return files[0]

@app.get("/api/status")
def health(): return {"status":"online","hp_fix":True,"real_download":True,"idm_connections":8}

@app.get("/")
def root(): return {"status":"IDM Online HP Fix ONLINE","docs":"/docs"}

@app.post("/api/info")
def info_post(payload: dict):
    url = payload.get("url","").strip()
    if not url: raise HTTPException(400,"URL kosong")
    if not is_allowed(url): raise HTTPException(400,"URL harus YouTube/Facebook")
    try:
        with yt_dlp.YoutubeDL({"quiet":True,"noplaylist":True,"nocheckcertificate":True}) as ydl:
            data = ydl.extract_info(url, download=False)
            return {"title":data.get("title"),"duration":data.get("duration"),"id":data.get("id")}
    except Exception as e: raise HTTPException(500,f"Info gagal: {e}")

@app.post("/api/download")
@app.post("/api/youtube/download")
@app.post("/api/facebook/download")
def download_post(payload: dict, background_tasks: BackgroundTasks):
    url = payload.get("url","").strip()
    fmt = payload.get("format","Video Best MP4")
    if not url: raise HTTPException(400,"URL kosong")
    if not is_allowed(url): raise HTTPException(400,"URL harus YouTube/Facebook")
    tmpdir = tempfile.mkdtemp()
    try:
        fp = do_download(url, fmt, tmpdir)
        fn = os.path.basename(fp)
        background_tasks.add_task(cleanup, tmpdir)
        ext = os.path.splitext(fn)[1].lower()
        mt = "video/mp4" if ext==".mp4" else "audio/mpeg" if ext==".mp3" else "application/octet-stream"
        return FileResponse(fp, media_type=mt, filename=fn, headers={"Content-Disposition": f'attachment; filename="{fn}"', "Access-Control-Expose-Headers":"Content-Disposition"})
    except HTTPException:
        cleanup(tmpdir); raise
    except Exception as e:
        cleanup(tmpdir); raise HTTPException(500,f"Download gagal: {e}")

@app.get("/api/download")
@app.get("/api/youtube/download")
@app.get("/api/facebook/download")
def download_get(url: str = Query(...), format: str = Query("Video Best MP4"), background_tasks: BackgroundTasks = None):
    if not url.strip(): raise HTTPException(400,"URL kosong")
    if not is_allowed(url): raise HTTPException(400,"URL harus YouTube/Facebook")
    tmpdir = tempfile.mkdtemp()
    try:
        fp = do_download(url, format, tmpdir)
        fn = os.path.basename(fp)
        if background_tasks:
            background_tasks.add_task(cleanup, tmpdir)
        ext = os.path.splitext(fn)[1].lower()
        mt = "video/mp4" if ext==".mp4" else "audio/mpeg" if ext==".mp3" else "application/octet-stream"
        return FileResponse(fp, media_type=mt, filename=fn, headers={"Content-Disposition": f'attachment; filename="{fn}"'})
    except HTTPException:
        cleanup(tmpdir); raise
    except Exception as e:
        cleanup(tmpdir); raise HTTPException(500,f"Download gagal: {e}")
