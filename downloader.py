import asyncio
import os
import re
import glob
import subprocess
from typing import Optional, Dict, Any, Tuple
import yt_dlp

DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Deno va FFmpeg yo'llarini avtomatik PATH ga qo'shish
DENO_DIRS = [
    os.path.expanduser("~/.deno/bin"),
    r"C:\Users\user\.deno\bin",
    "/root/.deno/bin",
    "/usr/local/bin",
]
for d in DENO_DIRS:
    if os.path.isdir(d) and d not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{d}{os.pathsep}{os.environ.get('PATH', '')}"

# Instagram havolalarini aniqlovchi regex
INSTAGRAM_PATTERN = re.compile(
    r"(https?://(?:www\.)?instagram\.com/(?:p|reel|reels|tv|share)/[A-Za-z0-9_-]+/?(?:\?[^\s]*)?)",
    re.IGNORECASE
)

# YouTube (Video, Shorts, youtu.be, Live, Music) havolalarini aniqlovchi regex
YOUTUBE_PATTERN = re.compile(
    r"(https?://(?:(?:www\.|m\.|music\.)?youtube\.com/(?:watch\?[^\s]*v=[A-Za-z0-9_-]+|shorts/[A-Za-z0-9_-]+|live/[A-Za-z0-9_-]+|embed/[A-Za-z0-9_-]+|v/[A-Za-z0-9_-]+)|youtu\.be/[A-Za-z0-9_-]+)(?:[^\s]*))",
    re.IGNORECASE
)

try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = None

if not FFMPEG_EXE:
    import shutil
    FFMPEG_EXE = shutil.which("ffmpeg")


def _clean_url(url: str) -> str:
    """Havola oxiridagi tinish belgilari yoki qavslarni tozalaydi."""
    return url.rstrip(".,!?:;)'\"]") if url else url


def extract_media_url(text: str) -> Optional[Tuple[str, str]]:
    """Matn ichidan Instagram yoki YouTube havolasini aniqlaydi.
    Qaytaradi: (platform_nomi, havola_url) yoki None
    """
    ig_match = INSTAGRAM_PATTERN.search(text)
    if ig_match:
        return "Instagram", _clean_url(ig_match.group(1))

    yt_match = YOUTUBE_PATTERN.search(text)
    if yt_match:
        return "YouTube", _clean_url(yt_match.group(1))

    return None


def extract_instagram_url(text: str) -> Optional[str]:
    """Matn ichidan birinchi Instagram havolasini ajratib oladi."""
    match = INSTAGRAM_PATTERN.search(text)
    return _clean_url(match.group(1)) if match else None


def extract_youtube_url(text: str) -> Optional[str]:
    """Matn ichidan birinchi YouTube havolasini ajratib oladi."""
    match = YOUTUBE_PATTERN.search(text)
    return _clean_url(match.group(1)) if match else None


def _download_sync(url: str) -> Dict[str, Any]:
    """Sinxron tarzda yt-dlp orqali videoni yuklab oladi."""
    out_template = os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s")

    # Format tanlash strategiyasi:
    # 1. 720p HD (gorizontal 1280x720 va vertikal Shorts 720x1280 uchun) - eng tezkor va har doim 50MB dan kichik
    # 2. Agar 720p topilmasa 1080p yoki 480p/360p
    format_selector = (
        'bestvideo[height<=720][width<=1280][ext=mp4]+bestaudio[ext=m4a]/'
        'bestvideo[width<=720][height<=1280][ext=mp4]+bestaudio[ext=m4a]/'
        'bestvideo[height<=720][width<=1280]+bestaudio/'
        'bestvideo[width<=720][height<=1280]+bestaudio/'
        'best[height<=720][ext=mp4]/'
        'best[height<=720]/'
        'bestvideo[height<=1080][width<=1920][ext=mp4]+bestaudio[ext=m4a]/'
        'bestvideo[width<=1080][height<=1920][ext=mp4]+bestaudio[ext=m4a]/'
        'bestvideo[height<=1080][width<=1920]+bestaudio/'
        'bestvideo[width<=1080][height<=1920]+bestaudio/'
        'bestvideo[height<=480]+bestaudio/'
        'best[height<=480]/'
        'bestvideo[height<=360]+bestaudio/'
        'best[height<=360]/'
        'best'
    )

    ydl_opts = {
        'format': format_selector,
        'merge_output_format': 'mp4',
        'outtmpl': out_template,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'source_address': '0.0.0.0',
        'js_runtimes': {'deno': {}, 'node': {}, 'quickjs': {}},
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

    cookie_path = os.path.join(os.path.dirname(__file__), "cookies.txt")
    if os.path.exists(cookie_path):
        ydl_opts['cookiefile'] = cookie_path

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

        # Agar yuklangan fayl 50 MB dan katta bo'lsa, avtomatik 480p/360p hajmda qayta urinish
        if os.path.exists(downloaded_file) and os.path.getsize(downloaded_file) > 50 * 1024 * 1024:
            try:
                os.remove(downloaded_file)
            except Exception:
                pass
            fallback_opts = dict(ydl_opts)
            fallback_opts['format'] = (
                'bestvideo[height<=480]+bestaudio/'
                'bestvideo[width<=480]+bestaudio/'
                'best[height<=480]/'
                'bestvideo[height<=360]+bestaudio/'
                'best[height<=360]/'
                'best'
            )
            with yt_dlp.YoutubeDL(fallback_opts) as ydl_fb:
                info = ydl_fb.extract_info(url, download=True)
                downloaded_file = ydl_fb.prepare_filename(info)
                if not os.path.exists(downloaded_file):
                    matched_files = glob.glob(os.path.join(DOWNLOAD_DIR, f"{video_id}.*"))
                    if matched_files:
                        downloaded_file = matched_files[0]

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
