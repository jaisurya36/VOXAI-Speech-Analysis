import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.content_ai_service import evaluate_content, _deterministic_fallback
from app.schemas.content_ai import ContentEvaluationResponse

client = TestClient(app)

SAMPLE_SPEECH_PATH = os.path.join(os.path.dirname(__file__), "sample_speech.wav")


# ---------------------------------------------------------------------------
# Unit tests on Schema and Evaluation Logic
# ---------------------------------------------------------------------------

def test_deterministic_fallback_evaluation():
    transcript = "um so basically i think that the the speech was good you know"
    result = _deterministic_fallback(transcript, analysis_id="test-123", reason="Test fallback")

    # Validate with Pydantic
    validated = ContentEvaluationResponse(**result)
    assert validated.analysis_id == "test-123"
    assert validated.is_fallback is True
    assert 0 <= validated.grammar.score <= 100
    assert 0 <= validated.semantics.score <= 100
    assert 0 <= validated.content.score <= 100

    # Verify error detections
    assert len(validated.grammar.errors) > 0
    assert any("the the" in err.original for err in validated.grammar.errors)
    assert len(validated.semantics.issues) > 0

    # Verify Track B corrected transcript is generated
    assert validated.corrected_transcript
    assert "um" not in validated.corrected_transcript.lower()


def test_evaluate_content_empty_transcript():
    result = evaluate_content("", analysis_id="empty-test")
    validated = ContentEvaluationResponse(**result)
    assert validated.grammar.score == 0
    assert validated.corrected_transcript == ""


# ---------------------------------------------------------------------------
# API Integration Tests
# ---------------------------------------------------------------------------

def test_content_evaluation_api_flow():
    # 1. Upload audio
    with open(SAMPLE_SPEECH_PATH, "rb") as f:
        up_res = client.post(
            "/api/media/upload",
            files={"file": ("speech_eval.wav", f.read(), "audio/wav")}
        )
    assert up_res.status_code == 201
    analysis_id = up_res.json()["analysis_id"]

    # 2. Transcribe
    trans_res = client.post(f"/api/analysis/{analysis_id}/transcribe")
    assert trans_res.status_code == 200

    # 3. Evaluate Content
    eval_res = client.post(f"/api/analysis/{analysis_id}/evaluate-content")
    assert eval_res.status_code == 200
    data = eval_res.json()

    assert data["analysis_id"] == analysis_id
    assert "corrected_transcript" in data
    assert 0 <= data["grammar"]["score"] <= 100
    assert 0 <= data["semantics"]["score"] <= 100
    assert 0 <= data["content"]["score"] <= 100
    assert isinstance(data["content"]["strengths"], list)
    assert isinstance(data["content"]["recommendations"], list)

    # 4. Verify Persistence
    get_res = client.get(f"/api/analysis/{analysis_id}/content-evaluation")
    assert get_res.status_code == 200
    saved = get_res.json()
    assert saved["grammar"]["score"] == data["grammar"]["score"]
    assert saved["corrected_transcript"] == data["corrected_transcript"]


def test_evaluate_without_transcription_returns_400():
    # Upload without transcribing
    with open(SAMPLE_SPEECH_PATH, "rb") as f:
        up_res = client.post(
            "/api/media/upload",
            files={"file": ("untranscribed.wav", f.read(), "audio/wav")}
        )
    analysis_id = up_res.json()["analysis_id"]

    res = client.post(f"/api/analysis/{analysis_id}/evaluate-content")
    assert res.status_code == 400
    assert "transcribe" in res.json()["detail"].lower()


def test_evaluate_nonexistent_returns_404():
    res = client.post("/api/analysis/nonexistent-id/evaluate-content")
    assert res.status_code == 404
