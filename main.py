

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
import yt_dlp
import os
import shutil
import pathlib
import tempfile
import re

app = FastAPI(title="YouTube -> MP3 Converter")

TMP_DIR = pathlib.Path(tempfile.gettempdir()) / "yt_mp3_tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)

# sanitize filename for responses
def _sanitize_filename(name: str) -> str:
    # very small sanitizer: remove path chars
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name)
    name = name.strip()
    return name[:200]


@app.get("/download")
async def download(url: str = Query(..., description="YouTube video URL"), background_tasks: BackgroundTasks = None):
    """Download a YouTube video's audio and return MP3 file.

    Example: /download?url=https://www.youtube.com/watch?v=VIDEO_ID
    """
    if not url:
        raise HTTPException(status_code=400, detail="Missing url parameter")

    # Configure yt-dlp
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(TMP_DIR / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        # Avoid writing metadata or embed thumbnails to keep it simple
        "writethumbnail": False,
        "nopart": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=422, detail=f"Download failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    # Construct mp3 path
    video_id = info.get("id")
    title = info.get("title") or video_id
    mp3_path = TMP_DIR / f"{video_id}.mp3"

    if not mp3_path.exists():
        # fallback: try to find any mp3 file starting with id
        matches = list(TMP_DIR.glob(f"{video_id}*.mp3"))
        if matches:
            mp3_path = matches[0]

    if not mp3_path.exists():
        raise HTTPException(status_code=500, detail="MP3 file not found after conversion")

    safe_name = _sanitize_filename(title) + ".mp3"

    # Schedule cleanup after sending
    def _cleanup(path: str):
        try:
            p = pathlib.Path(path)
            if p.exists():
                p.unlink()
        except Exception:
            pass

    if background_tasks is not None:
        background_tasks.add_task(_cleanup, str(mp3_path))

    # Return file response (streaming handled by server)
    return FileResponse(path=str(mp3_path), filename=safe_name, media_type="audio/mpeg")


# Optional: health check
@app.get("/health")
async def health():
    return {"status": "ok", "tmp_dir": str(TMP_DIR)}


# Optional: simple index page
@app.get("/")
async def index():
    return {"usage": "GET /download?url=YOUTUBE_URL"}
    
