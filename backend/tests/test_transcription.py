import os
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.transcription_service import (
    normalize_delivery_transcript,
    _generate_fallback_words,
    transcribe_audio,
)

client = TestClient(app)

SAMPLE_SPEECH_PATH = os.path.join(os.path.dirname(__file__), "sample_speech.wav")


# ---------------------------------------------------------------------------
# Unit tests on Delivery Transcript Normalization
# ---------------------------------------------------------------------------

def test_normalize_delivery_transcript_preserves_wording():
    """Rule: Must NOT rewrite participant wording, only formatting."""
    raw = "so basically i think that we should like continue"
    normalized = normalize_delivery_transcript(raw)
    assert "So basically I think that we should like continue." == normalized


def test_normalize_delivery_transcript_fixes_punctuation_and_caps():
    raw = "hello world..how are you doing?? i am doing great"
    normalized = normalize_delivery_transcript(raw)
    assert normalized == "Hello world. How are you doing? I am doing great."


def test_normalize_delivery_transcript_handles_empty():
    assert normalize_delivery_transcript("") == ""
    assert normalize_delivery_transcript("   ") == ""


# ---------------------------------------------------------------------------
# Unit tests on Fallback Word Generation
# ---------------------------------------------------------------------------

def test_generate_fallback_words():
    segments = [
        {"id": 0, "start": 0.0, "end": 2.0, "text": "hello brave world"},
        {"id": 1, "start": 2.5, "end": 4.5, "text": "speech analytics testing"},
    ]
    words = _generate_fallback_words(segments)
    assert len(words) == 6

    # Verify monotonic timestamps
    for i in range(len(words) - 1):
        assert words[i]["start"] <= words[i]["end"]
        assert words[i]["start"] <= words[i + 1]["start"]

    assert words[0]["word"] == "hello"
    assert words[-1]["word"] == "testing"


# ---------------------------------------------------------------------------
# End-to-End Transcription API Tests
# ---------------------------------------------------------------------------

def test_transcribe_endpoint_flow():
    assert os.path.exists(SAMPLE_SPEECH_PATH), "sample_speech.wav must exist for integration tests"

    # 1. Upload sample speech through Phase 2 upload endpoint
    with open(SAMPLE_SPEECH_PATH, "rb") as f:
        upload_res = client.post(
            "/api/media/upload",
            files={"file": ("speech_test.wav", f.read(), "audio/wav")}
        )
    assert upload_res.status_code == 201
    analysis_id = upload_res.json()["analysis_id"]

    # 2. Trigger transcription
    trans_res = client.post(f"/api/analysis/{analysis_id}/transcribe")
    assert trans_res.status_code == 200
    data = trans_res.json()

    # 3. Verify non-empty transcripts
    assert data["raw_transcript"], "raw_transcript must not be empty"
    assert data["delivery_transcript"], "delivery_transcript must not be empty"
    assert "speech" in data["raw_transcript"].lower() or "hello" in data["raw_transcript"].lower()

    # 4. Verify monotonic timestamps
    words = data["words"]
    assert len(words) > 0, "Should contain word-level timestamps"
    for i in range(len(words)):
        assert words[i]["start"] <= words[i]["end"]
        if i < len(words) - 1:
            assert words[i]["start"] <= words[i + 1]["start"]

    segments = data["segments"]
    assert len(segments) > 0
    for s in segments:
        assert s["start"] <= s["end"]

    # 5. Verify duration roughly matches audio
    assert data["duration"] >= 2.0

    # 6. Verify persistence via GET /api/analysis/{analysis_id}/transcript
    get_res = client.get(f"/api/analysis/{analysis_id}/transcript")
    assert get_res.status_code == 200
    saved = get_res.json()
    assert saved["raw_transcript"] == data["raw_transcript"]
    assert saved["delivery_transcript"] == data["delivery_transcript"]
    assert len(saved["words"]) == len(data["words"])


def test_transcribe_nonexistent_analysis_404():
    res = client.post("/api/analysis/non-existent-uuid/transcribe")
    assert res.status_code == 404


def test_get_transcript_nonexistent_404():
    res = client.get("/api/analysis/non-existent-uuid/transcript")
    assert res.status_code == 404
