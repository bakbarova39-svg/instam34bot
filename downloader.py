import asyncio
import os
import re
import glob
import subprocess
from typing import Optional, Dict, Any, Tuple
import yt_dlp

DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Instagram havolalarini aniqlovchi regex
INSTAGRAM_PATTERN = re.compile(
    r"(https?://(?:www\.)?instagram\.com/(?:p|reel|reels|tv|share)/[A-Za-z0-9_-]+/?(?:\?[^\s]*)?)",
    re.IGNORECASE
)

# YouTube (Video, Shorts, youtu.be) havolalarini aniqlovchi regex
YOUTUBE_PATTERN = re.compile(
    r"(https?://(?:(?:www\.|m\.)?youtube\.com/(?:watch\?[^\s]*v=[A-Za-z0-9_-]+|shorts/[A-Za-z0-9_-]+|embed/[A-Za-z0-9_-]+)|youtu\.be/[A-Za-z0-9_-]+)(?:\?[^\s]*)?)",
    re.IGNORECASE
)

try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = None


def extract_media_url(text: str) -> Optional[Tuple[str, str]]:
    """Matn ichidan Instagram yoki YouTube havolasini aniqlaydi.
    Qaytaradi: (platform_nomi, havola_url) yoki None
    """
    ig_match = INSTAGRAM_PATTERN.search(text)
    if ig_match:
        return "Instagram", ig_match.group(1)

    yt_match = YOUTUBE_PATTERN.search(text)
    if yt_match:
        return "YouTube", yt_match.group(1)

    return None


def extract_instagram_url(text: str) -> Optional[str]:
    """Matn ichidan birinchi Instagram havolasini ajratib oladi."""
    match = INSTAGRAM_PATTERN.search(text)
    return match.group(1) if match else None


def extract_youtube_url(text: str) -> Optional[str]:
    """Matn ichidan birinchi YouTube havolasini ajratib oladi."""
    match = YOUTUBE_PATTERN.search(text)
    return match.group(1) if match else None


def _download_sync(url: str) -> Dict[str, Any]:
    """Sinxron tarzda yt-dlp orqali videoni yuklab oladi."""
    out_template = os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s")

    # Format strategiyasi:
    # 1. Avval 45 MB dan kichik video + audio oqimlarini qidirish
    # 2. Keyin 48 MB dan kichik to'liq bitta MP4 fayl
    # 3. Oxirida 50 MB gacha bo'lgan eng yaxshi sifat
    ydl_opts = {
        'format': 'bestvideo[filesize<?45M][ext=mp4]+bestaudio[ext=m4a]/bestvideo[filesize<?45M]+bestaudio/best[filesize<?48M][ext=mp4]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'outtmpl': out_template,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        # 50 MB Telegram bot fayl yuborish chegarasi
        'max_filesize': 50 * 1024 * 1024,
    }

    if FFMPEG_EXE:
        ydl_opts['ffmpeg_location'] = FFMPEG_EXE

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if not info:
            raise Exception("Video ma'lumotlarini olib bo'lmadi.")

        video_id = info.get("id")

        # Yuklab olingan faylni topish
        downloaded_file = ydl.prepare_filename(info)
        if not os.path.exists(downloaded_file):
            matched_files = glob.glob(os.path.join(DOWNLOAD_DIR, f"{video_id}.*"))
            if matched_files:
                downloaded_file = matched_files[0]
            else:
                raise FileNotFoundError("Yuklangan video fayli topilmadi.")

        return {
            "file_path": downloaded_file,
            "title": info.get("title") or info.get("description") or "Video",
            "uploader": info.get("uploader") or info.get("channel") or "",
            "duration": info.get("duration") or 0,
            "width": info.get("width"),
            "height": info.get("height"),
            "thumbnail": info.get("thumbnail"),
        }


async def download_video(url: str) -> Dict[str, Any]:
    """Asinxron o'rab turuvchi funksiya: event loopni bloklamaslik uchun alohida thread'da ishlaydi."""
    return await asyncio.to_thread(_download_sync, url)


# Orqaga moslik uchun alias
download_instagram_video = download_video


def _convert_to_round_sync(input_path: str, output_path: str) -> None:
    """Ixtiyoriy to'rtburchak/vertikal videoni markazidan qirqib 1:1 kvadrat dumaloq video xabarga aylantirish."""
    if not FFMPEG_EXE:
        raise Exception("FFmpeg vositasi topilmadi.")

    cmd = [
        FFMPEG_EXE,
        "-y",
        "-i", input_path,
        "-t", "60",  # Telegram video note limiti: 60 soniya
        "-vf", "crop=min(iw\\,ih):min(iw\\,ih),scale=480:480",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "24",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_path
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise Exception(f"Video konvertatsiyasida xatolik: {res.stderr}")


async def convert_to_round_video(input_path: str, output_path: str) -> None:
    """Asinxron ravishda videoni dumaloq video formatiga o'tkazadi."""
    await asyncio.to_thread(_convert_to_round_sync, input_path, output_path)


def cleanup_file(file_path: Optional[str]) -> None:
    """Yuborilgandan so'ng vaqtinchalik video faylini o'chirib xotirani tozalash."""
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Faylni o'chirishda xatolik: {e}")
