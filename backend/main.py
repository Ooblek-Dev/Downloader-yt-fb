
import os, re, tempfile, shutil
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp

app = FastAPI(title="FetchHub API - Real Download")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED = [r"(youtube\.com|youtu\.be)", r"(facebook\.com|fb\.watch)"]

def is_allowed(url: str):
    return any(re.search(p, url, re.I) for p in ALLOWED)

def cleanup(path):
    try:
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        elif os.path.isfile(path):
            os.remove(path)
    except:
        pass

def get_opts(fmt, tmpdir):
    opts = {
        "outtmpl": os.path.join(tmpdir, "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": False,
        "no_warnings": True,
        "merge_output_format": "mp4",
    }
    f = fmt.lower()
    if "best" in f and "mp4" in f:
        opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
    elif f == "1080" or "1080" in f:
        opts["format"] = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]"
    elif f == "720" or "720" in f:
        opts["format"] = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]"
    elif "320" in f:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"320"}]
    elif "192" in f:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"192"}]
    elif "mp3" in f or "audio" in f:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"192"}]
    else:
        opts["format"] = "bestvideo+bestaudio/best"
    return opts

@app.get("/")
def root():
    return {"status":"FetchHub API running - real download ready", "endpoints":["/api/info","/api/download"]}

@app.post("/api/info")
@app.post("/api/youtube/info")
@app.post("/api/facebook/info")
def info(payload: dict):
    url = payload.get("url","").strip()
    if not url: raise HTTPException(400,"URL kosong")
    if not is_allowed(url): raise HTTPException(400,"URL harus YouTube atau Facebook")
    try:
        with yt_dlp.YoutubeDL({"quiet":True, "noplaylist":True}) as ydl:
            data = ydl.extract_info(url, download=False)
            return {
                "title": data.get("title"),
                "duration": data.get("duration"),
                "uploader": data.get("uploader"),
                "extractor": data.get("extractor"),
            }
    except Exception as e:
        raise HTTPException(500, f"Gagal ambil info: {str(e)}")

@app.post("/api/download")
@app.post("/api/youtube/download")
@app.post("/api/facebook/download")
def download(payload: dict, background_tasks: BackgroundTasks):
    url = payload.get("url","").strip()
    fmt = payload.get("format","best")
    if not url: raise HTTPException(400,"URL kosong")
    if not is_allowed(url): raise HTTPException(400,"URL harus YouTube atau Facebook")
    
    tmpdir = tempfile.mkdtemp()
    try:
        opts = get_opts(fmt, tmpdir)
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)
            files = []
            for r,d,fns in os.walk(tmpdir):
                for fn in fns:
                    files.append(os.path.join(r,fn))
            if not files:
                raise HTTPException(500,"File tidak ditemukan")
            files.sort(key=lambda x: os.path.getsize(x), reverse=True)
            filepath = files[0]
            filename = os.path.basename(filepath)
            background_tasks.add_task(cleanup, tmpdir)
            ext = os.path.splitext(filename)[1].lower()
            if ext==".mp3": media_type="audio/mpeg"
            elif ext==".m4a": media_type="audio/mp4"
            elif ext==".mp4": media_type="video/mp4"
            elif ext==".webm": media_type="video/webm"
            else: media_type="application/octet-stream"
            return FileResponse(filepath, media_type=media_type, filename=filename, headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    except HTTPException:
        cleanup(tmpdir)
        raise
    except Exception as e:
        cleanup(tmpdir)
        raise HTTPException(500, f"Download gagal: {str(e)}")
