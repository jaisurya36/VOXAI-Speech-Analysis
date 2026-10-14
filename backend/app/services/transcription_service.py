"""
transcription_service.py — Automatic Speech-to-Text using Faster-Whisper.

Provides:
  - transcribe_audio(audio_path: str) -> dict
  - normalize_delivery_transcript(raw_text: str) -> str
  - Structured segments, word timestamps, language, duration
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Cached model instance
_WHISPER_MODEL = None
_CURRENT_MODEL_SIZE = None

DEFAULT_WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
DEFAULT_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
DEFAULT_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")


def get_whisper_model(
    model_size: str = DEFAULT_WHISPER_MODEL,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE_TYPE,
):
    """
    Lazy-load and cache the Faster-Whisper model in memory.
    Uses CPU with int8 quantization by default for rapid inference.
    """
    global _WHISPER_MODEL, _CURRENT_MODEL_SIZE
    if _WHISPER_MODEL is None or _CURRENT_MODEL_SIZE != model_size:
        from faster_whisper import WhisperModel
        logger.info(f"Loading Faster-Whisper model '{model_size}' on {device} ({compute_type})...")
        _WHISPER_MODEL = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            download_root=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "models"),
        )
        _CURRENT_MODEL_SIZE = model_size
        logger.info("Faster-Whisper model loaded successfully.")
    return _WHISPER_MODEL


def normalize_delivery_transcript(raw_text: str) -> str:
    """
    Track A: Delivery Reference transcript.
    
    CRITICAL ARCHITECTURAL RULE:
    Use the participant's recognized transcript while preserving the same words
    as much as possible.
    
    Only normalizes:
      - Repeated punctuation / artifacts
      - Capitalization of sentence starts and 'I'
      - Standardized sentence boundary spacing
      - Obvious ASR formatting glitches
      
    Do NOT rewrite vocabulary, grammar, or word choices.
    """
    if not raw_text:
        return ""

    text = raw_text.strip()

    # 1. Collapse multiple spaces / newlines into a single space
    text = re.sub(r"\s+", " ", text)

    # 2. Fix multiple punctuations (e.g., '..', '??', ',,')
    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r"\?{2,}", "?", text)
    text = re.sub(r"!{2,}", "!", text)
    text = re.sub(r",{2,}", ",", text)

    # 3. Ensure space after punctuation if missing
    text = re.sub(r"([.,!?;:])([A-Za-z0-9])", r"\1 \2", text)

    # 4. Remove space before punctuation (e.g., "word ." -> "word.")
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)

    # 5. Capitalize standalone 'i'
    text = re.sub(r"\bi\b", "I", text)

    # 6. Capitalize sentence beginnings
    sentences = re.split(r"(?<=[.!?])\s+", text)
    capitalized_sentences = []
    for s in sentences:
        s = s.strip()
        if s:
            s = s[0].upper() + s[1:]
            capitalized_sentences.append(s)

    normalized = " ".join(capitalized_sentences)

    # 7. Ensure ends with a period if no closing punctuation
    if normalized and normalized[-1] not in ".!?":
        normalized += "."

    return normalized


import wave
import subprocess
import numpy as np


def load_audio_array(audio_path: str) -> np.ndarray:
    """
    Load audio as 16 kHz mono float32 numpy array.
    Reads directly from standardized 16 kHz WAV, or decodes via FFmpeg pipe.
    """
    try:
        with wave.open(audio_path, "rb") as wf:
            framerate = wf.getframerate()
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            frames = wf.readframes(wf.getnframes())

            if framerate == 16000 and n_channels == 1 and sampwidth == 2:
                return np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    except Exception as e:
        logger.debug(f"Direct wave read fallback: {e}")

    from app.services.media_service import _find_ffmpeg
    ffmpeg = _find_ffmpeg()
    cmd = [
        ffmpeg, "-y", "-i", audio_path,
        "-f", "s16le",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        "pipe:1",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def transcribe_audio(
    audio_path: str,
    model_size: str = DEFAULT_WHISPER_MODEL,
    language: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Transcribe an audio file using Faster-Whisper with word-level timestamps.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    audio_np = load_audio_array(audio_path)
    model = get_whisper_model(model_size=model_size)

    # Perform transcription with word-level timestamps on numpy array
    segments_iter, info = model.transcribe(
        audio_np,
        beam_size=5,
        word_timestamps=True,
        language=language,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    detected_language = info.language
    total_duration = info.duration

    segments: List[Dict[str, Any]] = []
    words: List[Dict[str, Any]] = []
    full_text_parts = []

    for idx, seg in enumerate(segments_iter):
        seg_text = seg.text.strip()
        if not seg_text:
            continue

        full_text_parts.append(seg_text)

        seg_dict = {
            "id": idx,
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg_text,
        }
        segments.append(seg_dict)

        # Collect word-level timestamps
        if seg.words:
            for w in seg.words:
                cleaned_word = w.word.strip()
                if cleaned_word:
                    words.append({
                        "word": cleaned_word,
                        "start": round(w.start, 2),
                        "end": round(w.end, 2),
                        "probability": round(w.probability, 3),
                    })

    raw_text = " ".join(full_text_parts).strip()

    # Fallback: if no word timestamps were extracted, generate approximate word intervals from segments
    if segments and not words:
        logger.warning("No word-level timestamps returned by Faster-Whisper. Generating proportional word timestamps.")
        words = _generate_fallback_words(segments)

    # Generate Track A Delivery Transcript
    delivery_text = normalize_delivery_transcript(raw_text)

    return {
        "text": raw_text,
        "delivery_transcript": delivery_text,
        "language": detected_language,
        "duration": round(total_duration, 2),
        "segments": segments,
        "words": words,
    }


def _generate_fallback_words(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Proportionally distribute words across segment durations as a fallback."""
    words: List[Dict[str, Any]] = []
    for seg in segments:
        seg_words = seg["text"].split()
        if not seg_words:
            continue
        seg_duration = max(0.1, seg["end"] - seg["start"])
        word_duration = seg_duration / len(seg_words)
        for i, w in enumerate(seg_words):
            w_start = round(seg["start"] + (i * word_duration), 2)
            w_end = round(w_start + word_duration, 2)
            words.append({
                "word": w.strip(".,!?;:\"'"),
                "start": w_start,
                "end": w_end,
                "probability": 1.0,
            })
    return words
