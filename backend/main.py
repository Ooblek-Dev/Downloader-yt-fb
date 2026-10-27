
import os, re, tempfile, shutil, logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import yt_dlp

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="FetchHub API - Online Real Download", version="Final")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED = [r"(youtube\.com|youtu\.be|youtube-nocookie\.com)", r"(facebook\.com|fb\.watch|fb\.com)"]

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
    # Real production opts - tested with youtube shorts
    opts = {
        "outtmpl": os.path.join(tmpdir, "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
        "merge_output_format": "mp4",
        "nocheckcertificate": True,
    }
    f = (fmt or "best").lower()
    if "best" in f and "mp4" in f:
        opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
    elif "1080" in f:
        opts["format"] = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
    elif "720" in f:
        opts["format"] = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best"
    elif "320" in f:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"320"}]
    elif "192" in f:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"192"}]
    elif "mp3" in f:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"192"}]
    elif "m4a" in f or "audio" in f:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{"key":"FFmpegExtractAudio","preferredcodec":"m4a"}]
    else:
        opts["format"] = "bestvideo+bestaudio/best"
    return opts

@app.get("/api/status")
@app.get("/api/health")
def health():
    return {"status":"online", "engine":"yt-dlp", "real_download":True, "formats":["Video Best MP4","Video 1080p","Video 720p","MP3 320kbps","MP3 192kbps"]}

@app.get("/")
def root():
    return {"status":"FetchHub API ONLINE - real download ready", "docs":"/docs", "frontend":"http://localhost:3000"}

@app.post("/api/info")
@app.post("/api/youtube/info")
@app.post("/api/facebook/info")
def info(payload: dict):
    url = payload.get("url","").strip()
    if not url:
        raise HTTPException(400,"URL kosong")
    if not is_allowed(url):
        raise HTTPException(400,"URL harus YouTube atau Facebook")
    try:
        with yt_dlp.YoutubeDL({"quiet":True, "noplaylist":True, "nocheckcertificate":True}) as ydl:
            data = ydl.extract_info(url, download=False)
            return {
                "title": data.get("title"),
                "duration": data.get("duration"),
                "uploader": data.get("uploader"),
                "extractor": data.get("extractor"),
                "id": data.get("id"),
            }
    except Exception as e:
        logging.error(f"Info error: {e}")
        raise HTTPException(500, f"Gagal ambil info: {str(e)}")

@app.post("/api/download")
@app.post("/api/youtube/download")
@app.post("/api/facebook/download")
def download(payload: dict, background_tasks: BackgroundTasks):
    url = payload.get("url","").strip()
    fmt = payload.get("format","Video Best MP4")
    if not url:
        raise HTTPException(400,"URL kosong")
    if not is_allowed(url):
        raise HTTPException(400,"URL harus YouTube atau Facebook")
    
    tmpdir = tempfile.mkdtemp()
    logging.info(f"REAL DOWNLOAD: {url} format={fmt} dir={tmpdir}")
    
    try:
        opts = get_opts(fmt, tmpdir)
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)
            files = []
            for r,d,fns in os.walk(tmpdir):
                for fn in fns:
                    files.append(os.path.join(r,fn))
            if not files:
                raise HTTPException(500,"File tidak ditemukan setelah download - yt-dlp gagal")
            files.sort(key=lambda x: os.path.getsize(x), reverse=True)
            filepath = files[0]
            filename = os.path.basename(filepath)
            size = os.path.getsize(filepath)
            logging.info(f"File ready: {filename} {size} bytes")
            
            background_tasks.add_task(cleanup, tmpdir)
            
            ext = os.path.splitext(filename)[1].lower()
            if ext==".mp3": media_type="audio/mpeg"
            elif ext==".m4a": media_type="audio/mp4"
            elif ext==".mp4": media_type="video/mp4"
            elif ext==".webm": media_type="video/webm"
            else: media_type="application/octet-stream"
            
            return FileResponse(
                filepath,
                media_type=media_type,
                filename=filename,
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "X-File-Size": str(size),
                    "Access-Control-Expose-Headers": "Content-Disposition, X-File-Size"
                }
            )
    except HTTPException:
        cleanup(tmpdir)
        raise
    except Exception as e:
        cleanup(tmpdir)
        logging.error(f"Download error: {e}")
        raise HTTPException(500, f"Download gagal: {str(e)}")

# Serve frontend if exists
try:
    if os.path.exists("frontend"):
        app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
except:
    pass
