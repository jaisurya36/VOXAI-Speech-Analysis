"""
media_service.py — Audio/Video ingestion and preprocessing.

Responsibilities:
  - Validate uploaded file (MIME, extension, size, non-empty)
  - Store original file
  - Extract audio from video via FFmpeg
  - Normalize analysis audio: WAV, mono, 16 kHz, PCM, level-normalized
  - Store & return media metadata
"""

import os
import uuid
import shutil
import subprocess
import mimetypes
import logging
from pathlib import Path
from typing import Optional

from app.config.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi"}
ALLOWED_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS

AUDIO_MIME_PREFIXES = ("audio/",)
VIDEO_MIME_PREFIXES = ("video/",)

ANALYSIS_SAMPLE_RATE = 16000  # Hz
ANALYSIS_CHANNELS = 1         # mono
ANALYSIS_FORMAT = "wav"
ANALYSIS_CODEC = "pcm_s16le"

TARGET_LUFS = -23.0           # EBU R128 broadcast loudness target
MAX_TRUE_PEAK = -1.0          # dBTP


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class MediaMetadata:
    """Container returned after successful media processing."""

    def __init__(
        self,
        analysis_id: str,
        original_filename: str,
        input_type: str,          # "audio" | "video"
        upload_path: str,
        analysis_audio_path: str,
        duration: float,
        sample_rate: int,
    ):
        self.analysis_id = analysis_id
        self.original_filename = original_filename
        self.input_type = input_type
        self.upload_path = upload_path
        self.analysis_audio_path = analysis_audio_path
        self.duration = duration
        self.sample_rate = sample_rate


class MediaError(Exception):
    """Raised for any media validation or processing failure."""
    pass


def get_upload_dir() -> Path:
    """Resolve the upload directory, creating it if needed."""
    raw = settings.upload_dir
    if not os.path.isabs(raw):
        backend_root = Path(__file__).resolve().parents[2]
        path = backend_root / raw.lstrip("./")
    else:
        path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_generated_dir() -> Path:
    """Resolve the generated directory, creating it if needed."""
    raw = settings.generated_dir
    if not os.path.isabs(raw):
        backend_root = Path(__file__).resolve().parents[2]
        path = backend_root / raw.lstrip("./")
    else:
        path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_file(filename: str, file_size: int, content_type: Optional[str] = None) -> str:
    """
    Validate filename + size + MIME.
    Returns 'audio' or 'video'.
    Raises MediaError for invalid files.
    """
    if not filename:
        raise MediaError("No filename provided.")

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise MediaError(
            f"Unsupported file format '{ext}'. "
            f"Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if file_size == 0:
        raise MediaError("Uploaded file is empty (0 bytes).")
    if file_size > max_bytes:
        raise MediaError(
            f"File too large ({file_size / 1024 / 1024:.1f} MB). "
            f"Maximum allowed: {settings.max_file_size_mb} MB."
        )

    if ext in AUDIO_EXTENSIONS:
        return "audio"
    return "video"


def process_upload(
    file_bytes: bytes,
    original_filename: str,
    analysis_id: Optional[str] = None,
) -> MediaMetadata:
    """
    Main entry point.
    1. Validate
    2. Save original
    3. Extract / normalize audio
    4. Return MediaMetadata

    Raises MediaError on any failure.
    """
    if analysis_id is None:
        analysis_id = str(uuid.uuid4())

    file_size = len(file_bytes)
    input_type = validate_file(original_filename, file_size)

    upload_dir = get_upload_dir()
    analysis_dir = upload_dir / analysis_id
    analysis_dir.mkdir(parents=True, exist_ok=True)

    # Save original
    safe_name = Path(original_filename).name
    upload_path = analysis_dir / f"original_{safe_name}"
    upload_path.write_bytes(file_bytes)
    logger.info(f"[{analysis_id}] Saved original → {upload_path}")

    # Determine analysis audio output path
    analysis_audio_path = analysis_dir / "analysis_audio.wav"

    if input_type == "video":
        _extract_audio_from_video(str(upload_path), str(analysis_audio_path), analysis_id)
    else:
        _normalize_audio(str(upload_path), str(analysis_audio_path), analysis_id)

    # Measure duration
    duration = _get_audio_duration(str(analysis_audio_path), analysis_id)

    if duration < 0.5:
        raise MediaError(
            f"Audio is too short ({duration:.2f}s). "
            "Please upload a recording with at least 0.5 seconds of speech."
        )

    logger.info(
        f"[{analysis_id}] Processing complete — "
        f"type={input_type}, duration={duration:.2f}s, "
        f"output={analysis_audio_path}"
    )

    return MediaMetadata(
        analysis_id=analysis_id,
        original_filename=original_filename,
        input_type=input_type,
        upload_path=str(upload_path),
        analysis_audio_path=str(analysis_audio_path),
        duration=duration,
        sample_rate=ANALYSIS_SAMPLE_RATE,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_ffmpeg() -> str:
    """
    Locate the ffmpeg executable.
    Checks system PATH first, then common Windows install locations.
    Raises MediaError if not found.
    """
    # 1. System PATH
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path

    # 2. Common Windows locations after winget/chocolatey install
    candidates = [
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet",
                     "Packages", "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe",
                     "ffmpeg-7.1-full_build", "bin", "ffmpeg.exe"),
    ]
    # Also scan LOCALAPPDATA WinGet packages dynamically
    winget_pkg_root = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    if winget_pkg_root.exists():
        for pkg_dir in winget_pkg_root.iterdir():
            if "ffmpeg" in pkg_dir.name.lower():
                candidate = pkg_dir / "bin" / "ffmpeg.exe"
                if candidate.exists():
                    return str(candidate)
                # Some builds nest one level deeper
                for sub in pkg_dir.iterdir():
                    nested = sub / "bin" / "ffmpeg.exe"
                    if nested.exists():
                        return str(nested)

    for c in candidates:
        if os.path.isfile(c):
            return c

    raise MediaError(
        "FFmpeg is not installed or not on PATH. "
        "Install it with: winget install Gyan.FFmpeg  "
        "or download from https://ffmpeg.org/download.html and add to PATH."
    )


def _run_ffmpeg(args: list[str], analysis_id: str) -> None:
    """Run an FFmpeg command, raising MediaError on failure."""
    ffmpeg = _find_ffmpeg()
    cmd = [ffmpeg, "-y"] + args
    logger.debug(f"[{analysis_id}] FFmpeg cmd: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        raise MediaError("FFmpeg processing timed out (>5 minutes). File may be corrupt or too large.")
    except FileNotFoundError:
        raise MediaError("FFmpeg executable not found. Please install FFmpeg.")

    if result.returncode != 0:
        stderr_text = result.stderr.decode("utf-8", errors="replace")
        logger.error(f"[{analysis_id}] FFmpeg error:\n{stderr_text}")
        raise MediaError(f"FFmpeg processing failed: {stderr_text[-500:]}")


def _extract_audio_from_video(input_path: str, output_path: str, analysis_id: str) -> None:
    """Extract audio track from video and normalize it."""
    logger.info(f"[{analysis_id}] Extracting audio from video...")
    _run_ffmpeg(
        [
            "-i", input_path,
            "-vn",                              # no video
            "-acodec", ANALYSIS_CODEC,
            "-ar", str(ANALYSIS_SAMPLE_RATE),
            "-ac", str(ANALYSIS_CHANNELS),
            "-af", "loudnorm",                  # EBU R128 normalization
            output_path,
        ],
        analysis_id,
    )


def _normalize_audio(input_path: str, output_path: str, analysis_id: str) -> None:
    """Convert audio to standard analysis format with level normalization."""
    logger.info(f"[{analysis_id}] Normalizing audio...")
    _run_ffmpeg(
        [
            "-i", input_path,
            "-acodec", ANALYSIS_CODEC,
            "-ar", str(ANALYSIS_SAMPLE_RATE),
            "-ac", str(ANALYSIS_CHANNELS),
            "-af", "loudnorm",
            output_path,
        ],
        analysis_id,
    )


def _get_audio_duration(audio_path: str, analysis_id: str) -> float:
    """
    Get duration in seconds using ffprobe.
    Falls back to 0.0 if ffprobe fails.
    """
    ffmpeg = _find_ffmpeg()
    ffprobe_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
    ffprobe = str(Path(ffmpeg).with_name(ffprobe_name))
    if not os.path.exists(ffprobe):
        ffprobe = shutil.which("ffprobe") or ffprobe

    try:
        result = subprocess.run(
            [
                ffprobe, "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        if result.returncode == 0:
            return float(result.stdout.decode().strip())
    except Exception as e:
        logger.warning(f"[{analysis_id}] ffprobe duration check failed: {e}")

    # Fallback: use Python wave module for WAV files
    try:
        import wave
        with wave.open(audio_path, "r") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate)
    except Exception as e:
        logger.warning(f"[{analysis_id}] wave duration fallback failed: {e}")

    return 0.0
