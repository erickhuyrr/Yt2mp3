from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
import yt_dlp
import pathlib
import tempfile
import re

app = FastAPI(title="YouTube to MP3 API")

TMP_DIR = pathlib.Path(tempfile.gettempdir()) / "yt_mp3_tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)

def sanitize(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "_", name)[:200]


@app.get("/download")
async def download(url: str, background_tasks: BackgroundTasks):
    if not url:
        raise HTTPException(400, "Missing ?url=")

    ydl_opts = {
        "format": "bestaudio",
        "outtmpl": str(TMP_DIR / "%(id)s.%(ext)s"),
        "quiet": True,
        "noplaylist": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as e:
        raise HTTPException(422, f"Download error: {e}")

    video_id = info.get("id")
    title = info.get("title") or "audio"
    mp3_file = TMP_DIR / f"{video_id}.mp3"

    if not mp3_file.exists():
        raise HTTPException(500, "MP3 not found after conversion")

    safe_name = sanitize(title) + ".mp3"

    def cleanup(path):
        p = pathlib.Path(path)
        if p.exists():
            p.unlink()

    background_tasks.add_task(cleanup, str(mp3_file))

    return FileResponse(str(mp3_file), filename=safe_name, media_type="audio/mpeg")


@app.get("/")
async def home():
    return {"status": "running", "usage": "/download?url=YOUTUBE_URL"}
