from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
import subprocess
import uuid
import os
from urllib.parse import urlparse, parse_qs, urlunparse

app = FastAPI(title="YouTube to MP3 API")

# Create downloads folder
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Use cookies if available
COOKIES_FILE = "cookies.txt" if os.path.exists("cookies.txt") else None

@app.get("/")
def home():
    return {"status": "YouTube MP3 API running", "cookies_loaded": bool(COOKIES_FILE)}

def clean_youtube_url(url: str) -> str:
    """Clean YouTube URL to remove extra parameters like ?si="""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    # Keep only 'v' parameter for YouTube
    if 'v' in qs:
        return f"https://www.youtube.com/watch?v={qs['v'][0]}"
    # If it's a short youtu.be URL
    if parsed.netloc in ["youtu.be"]:
        video_id = parsed.path.lstrip('/')
        return f"https://www.youtube.com/watch?v={video_id}"
    return url

@app.get("/mp3")
def download_mp3(url: str = Query(..., description="YouTube video URL")):
    """
    Download a YouTube video as MP3.
    Example: /mp3?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ
    """
    if not url:
        raise HTTPException(status_code=400, detail="No URL provided")

    clean_url = clean_youtube_url(url)

    try:
        # Unique filename
        file_id = str(uuid.uuid4())
        mp3_path = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp3")

        # yt-dlp command
        command = [
            "yt-dlp",
            "-f", "bestaudio",
            "--extract-audio",
            "--audio-format", "mp3",
            "-o", mp3_path.replace(".mp3", ".%(ext)s"),
            clean_url
        ]

        if COOKIES_FILE:
            command += ["--cookies", COOKIES_FILE]

        # Run yt-dlp
        subprocess.run(command, check=True)

        # Return downloaded MP3
        return FileResponse(
            mp3_path,
            media_type="audio/mpeg",
            filename="download.mp3"
        )

    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Download failed: Make sure URL is correct and your cookies are fresh. Error: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )
