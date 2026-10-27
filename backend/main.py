
import os, re, tempfile
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp

app = FastAPI(title="FetchHub API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

ALLOWED = [r"(youtube\.com|youtu\.be)", r"(facebook\.com|fb\.watch)"]

def is_allowed(url: str):
    return any(re.search(p, url, re.I) for p in ALLOWED)

def get_opts(fmt, tmpdir):
    opts = {"outtmpl": os.path.join(tmpdir, "%(title)s.%(ext)s"), "noplaylist": True}
    if fmt in ["best","Video Best MP4"]: opts["format"]="bestvideo+bestaudio/best"
    elif fmt=="1080": opts["format"]="bestvideo[height<=1080]+bestaudio/best[height<=1080]"
    elif fmt=="720": opts["format"]="bestvideo[height<=720]+bestaudio/best[height<=720]"
    elif "320" in fmt: 
        opts["format"]="bestaudio/best"
        opts["postprocessors"]=[{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"320"}]
    elif "192" in fmt:
        opts["format"]="bestaudio/best"
        opts["postprocessors"]=[{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"192"}]
    else: opts["format"]="best"
    return opts

@app.post("/api/info")
@app.post("/api/youtube/info")
@app.post("/api/facebook/info")
def info(payload: dict):
    url = payload.get("url","")
    if not is_allowed(url): raise HTTPException(400,"URL tidak didukung")
    try:
        with yt_dlp.YoutubeDL({"quiet":True}) as ydl:
            data = ydl.extract_info(url, download=False)
            return {"title": data.get("title"), "duration": data.get("duration"), "extractor": data.get("extractor")}
    except Exception as e:
        raise HTTPException(500, f"Gagal: {e}")

@app.post("/api/download")
@app.post("/api/youtube/download")
@app.post("/api/facebook/download")
def download(payload: dict):
    url = payload.get("url","")
    fmt = payload.get("format","best")
    if not is_allowed(url): raise HTTPException(400,"URL tidak didukung")
    tmpdir = tempfile.mkdtemp()
    try:
        with yt_dlp.YoutubeDL(get_opts(fmt, tmpdir)) as ydl:
            info = ydl.extract_info(url, download=True)
            fname = ydl.prepare_filename(info)
            # check for mp3 conversion
            base_no_ext = os.path.splitext(fname)[0]
            for ext in [".mp3",".m4a",".mp4",".webm"]:
                cand = base_no_ext+ext
                if os.path.exists(cand):
                    fname=cand
                    break
            if not os.path.exists(fname):
                files = os.listdir(tmpdir)
                if files: fname = os.path.join(tmpdir, files[0])
            return FileResponse(fname, filename=os.path.basename(fname))
    except Exception as e:
        raise HTTPException(500, f"Download gagal: {e}")

@app.get("/")
def root(): return {"status":"FetchHub API running"}
