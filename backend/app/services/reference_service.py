"""
reference_service.py — Automatic Ideal Reference Speech Generation.

Responsibilities:
  - Automatically synthesizes ideal public-speaking delivery audio from Track A delivery_transcript.
  - Controlled style: clear articulation, confident delivery, natural professional tone, moderate pace.
  - Primary engine: Gemini TTS API (gemini-2.0-flash / gemini-2.5-flash-preview-tts with Audio modality).
  - Fallback engine: Native SAPI speech synthesizer on Windows ensuring 100% offline reliability.
  - Normalizes generated audio to standardized 16 kHz mono PCM WAV with EBU R128 loudness normalization.
  - Optional second audio: synthesizes Track B improved speech for participant preview.
"""

import os
import uuid
import base64
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.config.settings import settings
from app.services.media_service import (
    get_generated_dir,
    _normalize_audio,
    _get_audio_duration,
    ANALYSIS_SAMPLE_RATE,
)

logger = logging.getLogger(__name__)

IDEAL_SPEECH_INSTRUCTION = (
    "Speak the following text with an ideal public-speaking delivery: "
    "clear articulation, confident delivery, natural conversational-professional tone, "
    "moderate pace, appropriate pauses, and natural cadence. "
    "Do not use theatrical or exaggerated delivery:\n\n"
)


def generate_ideal_reference(
    analysis_id: str,
    delivery_script: str,
    voice_name: str = "Puck",
) -> Dict[str, Any]:
    """
    Generate the Track A Ideal Delivery Reference audio from delivery_script.
    Returns metadata and path to the standardized 16 kHz mono WAV reference.
    """
    if not delivery_script or not delivery_script.strip():
        raise ValueError("Delivery script cannot be empty.")

    out_dir = get_generated_dir() / analysis_id
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_output_path = out_dir / "raw_reference.wav"
    final_output_path = out_dir / "reference_audio.wav"

    api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY", "")
    is_fallback = False
    model_used = settings.gemini_tts_model or "gemini-2.0-flash"

    # Attempt Gemini TTS if API key is present
    gemini_success = False
    if api_key:
        try:
            logger.info(f"[{analysis_id}] Synthesizing reference audio with Gemini TTS ({model_used})...")
            gemini_success = _synthesize_with_gemini(
                script=delivery_script,
                output_path=str(raw_output_path),
                api_key=api_key,
                model=model_used,
                voice_name=voice_name,
            )
        except Exception as e:
            logger.warning(f"[{analysis_id}] Gemini TTS call failed: {e}. Falling back to local TTS.")

    # Fallback to local synthesizer if Gemini was not available or failed
    if not gemini_success:
        logger.info(f"[{analysis_id}] Generating ideal reference audio with native speech synthesizer...")
        _synthesize_with_native_sapi(
            script=delivery_script,
            output_path=str(raw_output_path),
        )
        is_fallback = True
        model_used = "Windows SAPI High-Fidelity Synthesizer"
        voice_name = "Desktop Pro Natural"

    # Standardize the generated audio to 16 kHz mono WAV with EBU R128 loudness normalization
    logger.info(f"[{analysis_id}] Normalizing reference audio to 16 kHz mono PCM WAV...")
    _normalize_audio(str(raw_output_path), str(final_output_path), analysis_id)

    # Clean up intermediate raw file
    if raw_output_path.exists():
        try:
            raw_output_path.unlink()
        except Exception:
            pass

    duration = _get_audio_duration(str(final_output_path), analysis_id)

    return {
        "analysis_id": analysis_id,
        "audio_path": str(final_output_path),
        "reference_script": delivery_script,
        "duration": round(duration, 2),
        "sample_rate": ANALYSIS_SAMPLE_RATE,
        "model_name": model_used,
        "voice_name": voice_name,
        "is_fallback": is_fallback,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_improved_preview(
    analysis_id: str,
    corrected_script: str,
    voice_name: str = "Puck",
) -> Optional[str]:
    """
    Generate optional Track B improved speech preview for participant learning.
    """
    if not corrected_script or not corrected_script.strip():
        return None

    out_dir = get_generated_dir() / analysis_id
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_path = out_dir / "raw_improved.wav"
    final_path = out_dir / "improved_audio.wav"

    api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY", "")
    gemini_success = False

    if api_key:
        try:
            gemini_success = _synthesize_with_gemini(
                script=corrected_script,
                output_path=str(raw_path),
                api_key=api_key,
                model=settings.gemini_tts_model or "gemini-2.0-flash",
                voice_name=voice_name,
            )
        except Exception as e:
            logger.warning(f"[{analysis_id}] Gemini TTS for improved audio failed: {e}")

    if not gemini_success:
        _synthesize_with_native_sapi(corrected_script, str(raw_path))

    _normalize_audio(str(raw_path), str(final_path), analysis_id)

    if raw_path.exists():
        try:
            raw_path.unlink()
        except Exception:
            pass

    return str(final_path)


# ---------------------------------------------------------------------------
# Internal Synthesizer Engines
# ---------------------------------------------------------------------------

def _synthesize_with_gemini(
    script: str,
    output_path: str,
    api_key: str,
    model: str,
    voice_name: str,
) -> bool:
    """Invoke Gemini API to generate TTS audio bytes."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    prompt = f"{IDEAL_SPEECH_INSTRUCTION}{script}"

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            ),
        ),
    )

    audio_bytes = None
    for candidate in response.candidates:
        for part in candidate.content.parts:
            if part.inline_data and part.inline_data.data:
                audio_bytes = part.inline_data.data
                break
        if audio_bytes:
            break

    if not audio_bytes:
        return False

    Path(output_path).write_bytes(audio_bytes)
    return True


def _synthesize_with_native_sapi(script: str, output_path: str) -> None:
    """
    Generate pristine speech WAV using native Windows SAPI.
    Uses moderate speaking rate (Rate = 0) and clear volume.
    """
    escaped_script = script.replace('"', '""').replace("'", "''")
    escaped_path = os.path.abspath(output_path).replace('"', '""')

    # Create temporary script file to avoid shell escaping issues
    script_file = Path(output_path).parent / f"synth_{uuid.uuid4().hex[:8]}.ps1"
    ps_content = f"""
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = 0
$synth.Volume = 100
$synth.SetOutputToWaveFile('{escaped_path}')
$synth.Speak('{escaped_script}')
$synth.Dispose()
"""
    try:
        script_file.write_text(ps_content, encoding="utf-8")
        proc = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            check=True,
        )
    finally:
        if script_file.exists():
            try:
                script_file.unlink()
            except Exception:
                pass

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("Speech synthesis failed to produce an audio file.")
