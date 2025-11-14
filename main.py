from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import subprocess
import uuid
import os

app = FastAPI(title="YouTube to MP3 API")

# Create downloads folder
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Use cookies.txt if exists
COOKIES_FILE = "cookies.txt" if os.path.exists("cookies.txt") else None

@app.get("/")
def home():
    return {"status": "YouTube MP3 API running", "cookies_loaded": bool(COOKIES_FILE)}

@app.get("/mp3")
def download_mp3(url: str):
    """
    Download a YouTube video as MP3.
    Example: /mp3?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ
    """
    try:
        # Unique filename
        file_id = str(uuid.uuid4())
        mp3_path = f"{DOWNLOAD_DIR}/{file_id}.mp3"

        # Build yt-dlp command
        command = [
            "yt-dlp",
            "-f", "bestaudio",
            "--extract-audio",
            "--audio-format", "mp3",
            "-o", mp3_path.replace(".mp3", ".%(ext)s"),
            url
        ]

        # Add cookies if present
        if COOKIES_FILE:
            command += ["--cookies", COOKIES_FILE]

        # Run yt-dlp
        subprocess.run(command, check=True)

        # Return the downloaded file
        return FileResponse(
            mp3_path,
            media_type="audio/mpeg",
            filename="download.mp3"
        )

    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Download failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )
