import os
import io
import math
import wave
import struct
import shutil
import subprocess
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app
from app.services.media_service import _find_ffmpeg, validate_file, MediaError

client = TestClient(app)


def create_test_wav(duration: float = 1.0, sample_rate: int = 16000, freq: float = 440.0) -> bytes:
    """Generate in-memory WAV audio with a sine wave."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        n_frames = int(duration * sample_rate)
        for i in range(n_frames):
            val = int(16000 * math.sin(2 * math.pi * freq * (i / sample_rate)))
            wf.writeframes(struct.pack('<h', val))
    return buf.getvalue()


def create_test_mp3() -> bytes:
    """Generate test MP3 using ffmpeg."""
    wav_bytes = create_test_wav(duration=1.2)
    ffmpeg = _find_ffmpeg()
    proc = subprocess.run(
        [ffmpeg, "-y", "-i", "pipe:0", "-f", "mp3", "pipe:1"],
        input=wav_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return proc.stdout


def create_test_mp4() -> bytes:
    """Generate test MP4 video with audio using ffmpeg lavfi."""
    ffmpeg = _find_ffmpeg()
    proc = subprocess.run(
        [
            ffmpeg, "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1.2:size=160x120:rate=10",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1.2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-f", "mp4",
            "-movflags", "frag_keyframe+empty_moov",
            "pipe:1"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return proc.stdout


# ---------------------------------------------------------------------------
# Unit tests on validation
# ---------------------------------------------------------------------------

def test_validate_file_valid_audio():
    assert validate_file("speech.wav", 1000) == "audio"
    assert validate_file("speech.mp3", 1000) == "audio"
    assert validate_file("speech.m4a", 1000) == "audio"


def test_validate_file_valid_video():
    assert validate_file("speech.mp4", 1000) == "video"
    assert validate_file("speech.mov", 1000) == "video"
    assert validate_file("speech.webm", 1000) == "video"


def test_validate_file_empty():
    with pytest.raises(MediaError, match="empty"):
        validate_file("speech.wav", 0)


def test_validate_file_unsupported_extension():
    with pytest.raises(MediaError, match="Unsupported file format"):
        validate_file("document.pdf", 500)


def test_validate_file_too_large():
    too_large = (501) * 1024 * 1024
    with pytest.raises(MediaError, match="too large"):
        validate_file("speech.wav", too_large)


# ---------------------------------------------------------------------------
# Integration tests on POST /api/media/upload
# ---------------------------------------------------------------------------

def test_upload_wav():
    wav_data = create_test_wav(duration=1.5)
    response = client.post(
        "/api/media/upload",
        files={"file": ("test_sample.wav", wav_data, "audio/wav")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "ready"
    assert data["message"] == "Media ready for analysis."
    assert data["input_type"] == "audio"
    assert data["sample_rate"] == 16000
    assert data["duration"] >= 1.0
    assert "analysis_id" in data

    # Verify retrieval endpoints
    analysis_id = data["analysis_id"]
    audio_res = client.get(f"/api/media/{analysis_id}/audio")
    assert audio_res.status_code == 200
    assert audio_res.headers["content-type"] == "audio/wav"

    status_res = client.get(f"/api/media/{analysis_id}/status")
    assert status_res.status_code == 200
    assert status_res.json()["stage"] == "media_ready"


def test_upload_mp3():
    mp3_data = create_test_mp3()
    response = client.post(
        "/api/media/upload",
        files={"file": ("test_speech.mp3", mp3_data, "audio/mpeg")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "ready"
    assert data["input_type"] == "audio"
    assert data["duration"] >= 1.0
    assert data["sample_rate"] == 16000


def test_upload_mp4_video():
    mp4_data = create_test_mp4()
    response = client.post(
        "/api/media/upload",
        files={"file": ("presentation.mp4", mp4_data, "video/mp4")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "ready"
    assert data["input_type"] == "video"
    assert data["duration"] >= 1.0
    assert data["sample_rate"] == 16000

    # Verify normalized 16 kHz audio was extracted from video
    analysis_id = data["analysis_id"]
    audio_res = client.get(f"/api/media/{analysis_id}/audio")
    assert audio_res.status_code == 200
    assert len(audio_res.content) > 0


def test_upload_invalid_file_rejected():
    fake_txt = b"This is not audio"
    response = client.post(
        "/api/media/upload",
        files={"file": ("notes.txt", fake_txt, "text/plain")}
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_upload_empty_file_rejected():
    response = client.post(
        "/api/media/upload",
        files={"file": ("empty.wav", b"", "audio/wav")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"]


def test_upload_too_short_audio_rejected():
    short_wav = create_test_wav(duration=0.2)
    response = client.post(
        "/api/media/upload",
        files={"file": ("short.wav", short_wav, "audio/wav")}
    )
    assert response.status_code == 400
    assert "too short" in response.json()["detail"]
