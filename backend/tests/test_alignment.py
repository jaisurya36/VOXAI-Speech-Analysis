import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.alignment_service import (
    clean_word,
    align_word_sequences,
    _enforce_monotonic_timestamps,
    _build_aligned_phrases,
)

client = TestClient(app)

SAMPLE_SPEECH_PATH = os.path.join(os.path.dirname(__file__), "sample_speech.wav")


# ---------------------------------------------------------------------------
# Unit tests on Word Cleaning & Alignment
# ---------------------------------------------------------------------------

def test_clean_word():
    assert clean_word("Hello,") == "hello"
    assert clean_word("WORLD!!") == "world"
    assert clean_word("don't") == "dont"
    assert clean_word("I'm") == "im"
    assert clean_word("") == ""


def test_align_word_sequences_exact_match():
    p_words = [
        {"word": "Hello", "start": 0.0, "end": 0.4, "probability": 0.95},
        {"word": "world", "start": 0.5, "end": 0.9, "probability": 0.98},
        {"word": "today", "start": 1.0, "end": 1.4, "probability": 0.92},
    ]
    r_words = [
        {"word": "Hello,", "start": 0.0, "end": 0.35, "probability": 0.99},
        {"word": "world", "start": 0.4, "end": 0.8, "probability": 0.99},
        {"word": "today.", "start": 0.85, "end": 1.2, "probability": 0.99},
    ]

    res = align_word_sequences(p_words, r_words, analysis_id="test-exact")
    assert res["status"] == "aligned"
    assert res["alignment_coverage"] == 100.0
    assert res["matched_word_count"] == 3
    assert len(res["aligned_words"]) == 3
    assert len(res["aligned_phrases"]) >= 1


def test_align_word_sequences_with_discrepancy():
    # Participant included an extra word "actually"
    p_words = [
        {"word": "We", "start": 0.0, "end": 0.2},
        {"word": "actually", "start": 0.3, "end": 0.6},
        {"word": "must", "start": 0.7, "end": 0.9},
        {"word": "continue", "start": 1.0, "end": 1.5},
    ]
    r_words = [
        {"word": "We", "start": 0.0, "end": 0.2},
        {"word": "must", "start": 0.3, "end": 0.5},
        {"word": "continue", "start": 0.6, "end": 1.0},
    ]

    res = align_word_sequences(p_words, r_words, analysis_id="test-disc")
    assert res["matched_word_count"] == 3
    assert res["alignment_coverage"] == 75.0  # 3 out of 4 words
    assert "actually" in res["unmatched_participant_words"]

    # Verify timestamps remain monotonic
    aligned = res["aligned_words"]
    for i in range(len(aligned) - 1):
        assert aligned[i]["participant_start"] <= aligned[i + 1]["participant_start"]
        assert aligned[i]["reference_start"] <= aligned[i + 1]["reference_start"]


def test_align_empty_words():
    res = align_word_sequences([], [], analysis_id="empty-test")
    assert res["alignment_coverage"] == 0.0
    assert len(res["aligned_words"]) == 0


def test_build_aligned_phrases():
    words = [
        {"word": "One", "participant_start": 0.0, "participant_end": 0.3, "reference_start": 0.0, "reference_end": 0.25},
        {"word": "two", "participant_start": 0.4, "participant_end": 0.7, "reference_start": 0.3, "reference_end": 0.5},
        {"word": "three.", "participant_start": 0.8, "participant_end": 1.2, "reference_start": 0.6, "reference_end": 0.9},
    ]
    phrases = _build_aligned_phrases(words, max_words=5)
    assert len(phrases) == 1
    assert phrases[0]["text"] == "One two three."
    assert phrases[0]["participant_start"] == 0.0
    assert phrases[0]["participant_end"] == 1.2
    assert phrases[0]["reference_start"] == 0.0
    assert phrases[0]["reference_end"] == 0.9


# ---------------------------------------------------------------------------
# API Integration Tests
# ---------------------------------------------------------------------------

def test_forced_alignment_api_flow():
    # 1. Upload
    with open(SAMPLE_SPEECH_PATH, "rb") as f:
        up_res = client.post(
            "/api/media/upload",
            files={"file": ("align_test.wav", f.read(), "audio/wav")}
        )
    assert up_res.status_code == 201
    analysis_id = up_res.json()["analysis_id"]

    # 2. Transcribe
    trans_res = client.post(f"/api/analysis/{analysis_id}/transcribe")
    assert trans_res.status_code == 200

    # 3. Generate Reference
    ref_res = client.post(f"/api/analysis/{analysis_id}/generate-reference")
    assert ref_res.status_code == 200

    # 4. Trigger Forced Alignment
    align_res = client.post(f"/api/analysis/{analysis_id}/align")
    assert align_res.status_code == 200
    data = align_res.json()

    assert data["analysis_id"] == analysis_id
    assert data["alignment_coverage"] >= 70.0
    assert len(data["aligned_words"]) > 0
    assert len(data["aligned_phrases"]) > 0

    # Check timestamps ordering on aligned words
    for item in data["aligned_words"]:
        assert item["participant_start"] <= item["participant_end"]
        assert item["reference_start"] <= item["reference_end"]

    # 5. Verify Persistence
    get_res = client.get(f"/api/analysis/{analysis_id}/alignment")
    assert get_res.status_code == 200
    saved = get_res.json()
    assert saved["alignment_coverage"] == data["alignment_coverage"]
    assert len(saved["aligned_words"]) == len(data["aligned_words"])


def test_align_without_transcription_returns_400():
    with open(SAMPLE_SPEECH_PATH, "rb") as f:
        up_res = client.post(
            "/api/media/upload",
            files={"file": ("untranscribed_align.wav", f.read(), "audio/wav")}
        )
    analysis_id = up_res.json()["analysis_id"]

    res = client.post(f"/api/analysis/{analysis_id}/align")
    assert res.status_code == 400
    assert "transcribe" in res.json()["detail"].lower()


def test_align_nonexistent_returns_404():
    res = client.post("/api/analysis/nonexistent-uuid/align")
    assert res.status_code == 404
