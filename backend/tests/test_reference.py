import os
import wave
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.reference_service import (
    generate_ideal_reference,
    generate_improved_preview,
)

client = TestClient(app)

SAMPLE_SPEECH_PATH = os.path.join(os.path.dirname(__file__), "sample_speech.wav")


# ---------------------------------------------------------------------------
# Unit tests on Reference Generation
# ---------------------------------------------------------------------------

def test_generate_ideal_reference_produces_valid_wav(tmp_path):
    script = "We must continue our journey towards excellence."
    analysis_id = "unit-test-ref-1"

    meta = generate_ideal_reference(analysis_id, script)
    assert meta["analysis_id"] == analysis_id
    assert meta["reference_script"] == script
    assert meta["duration"] > 1.0
    assert meta["sample_rate"] == 16000

    # Verify output audio file is valid 16kHz mono WAV
    audio_path = meta["audio_path"]
    assert os.path.exists(audio_path)
    assert os.path.getsize(audio_path) > 0

    with wave.open(audio_path, "rb") as wf:
        assert wf.getframerate() == 16000
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2  # 16-bit PCM


def test_generate_improved_preview_produces_audio():
    script = "We should continually strive for operational excellence."
    analysis_id = "unit-test-improved-1"

    audio_path = generate_improved_preview(analysis_id, script)
    assert audio_path is not None
    assert os.path.exists(audio_path)
    assert os.path.getsize(audio_path) > 0


def test_generate_reference_empty_script_raises_error():
    with pytest.raises(ValueError, match="empty"):
        generate_ideal_reference("err-test", "")


# ---------------------------------------------------------------------------
# API Integration Tests
# ---------------------------------------------------------------------------

def test_generate_reference_api_flow():
    # 1. Upload
    with open(SAMPLE_SPEECH_PATH, "rb") as f:
        up_res = client.post(
            "/api/media/upload",
            files={"file": ("ref_test.wav", f.read(), "audio/wav")}
        )
    assert up_res.status_code == 201
    analysis_id = up_res.json()["analysis_id"]

    # 2. Transcribe
    trans_res = client.post(f"/api/analysis/{analysis_id}/transcribe")
    assert trans_res.status_code == 200
    delivery_script = trans_res.json()["delivery_transcript"]

    # 3. Evaluate Content (creates Track B)
    eval_res = client.post(f"/api/analysis/{analysis_id}/evaluate-content")
    assert eval_res.status_code == 200

    # 4. Generate Ideal Reference
    gen_res = client.post(f"/api/analysis/{analysis_id}/generate-reference")
    assert gen_res.status_code == 200
    data = gen_res.json()

    assert data["analysis_id"] == analysis_id
    assert data["reference_script"] == delivery_script
    assert data["duration"] > 0
    assert data["has_improved_audio"] is True

    # 5. Verify Audio Serving Endpoints
    ref_audio_res = client.get(f"/api/analysis/{analysis_id}/reference-audio")
    assert ref_audio_res.status_code == 200
    assert ref_audio_res.headers["content-type"] == "audio/wav"
    assert len(ref_audio_res.content) > 1000

    imp_audio_res = client.get(f"/api/analysis/{analysis_id}/improved-audio")
    assert imp_audio_res.status_code == 200
    assert imp_audio_res.headers["content-type"] == "audio/wav"
    assert len(imp_audio_res.content) > 1000


def test_generate_reference_without_transcription_returns_400():
    # Upload without transcribing
    with open(SAMPLE_SPEECH_PATH, "rb") as f:
        up_res = client.post(
            "/api/media/upload",
            files={"file": ("untranscribed_ref.wav", f.read(), "audio/wav")}
        )
    analysis_id = up_res.json()["analysis_id"]

    res = client.post(f"/api/analysis/{analysis_id}/generate-reference")
    assert res.status_code == 400
    assert "transcribed" in res.json()["detail"].lower()


def test_generate_reference_nonexistent_returns_404():
    res = client.post("/api/analysis/nonexistent-id/generate-reference")
    assert res.status_code == 404
