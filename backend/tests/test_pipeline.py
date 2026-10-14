import os
import uuid
import wave
import struct
import math
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.database import SessionLocal
from app.models.analysis import Analysis
from app.services.pipeline_service import run_pipeline, get_pipeline_progress
from app.schemas.pipeline import ProcessAllResponse, PipelineProgressResponse

client = TestClient(app)


def _generate_test_wav(filepath: str, duration_sec: float = 2.0, sample_rate: int = 16000, freq: float = 220.0):
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    num_samples = int(duration_sec * sample_rate)
    with wave.open(filepath, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        data = bytearray()
        for i in range(num_samples):
            val = int(16000 * math.sin(2 * math.pi * freq * (i / sample_rate)))
            data.extend(struct.pack("<h", val))
        wf.writeframes(data)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_get_pipeline_progress_initial_state(db_session: Session):
    analysis_id = str(uuid.uuid4())
    test_dir = os.path.join("uploads", analysis_id)
    os.makedirs(test_dir, exist_ok=True)
    audio_path = os.path.join(test_dir, "analysis_audio.wav")
    _generate_test_wav(audio_path, duration_sec=1.0)

    analysis = Analysis(
        id=analysis_id,
        status="pending",
        stage="media_ready",
        original_filename="test_speech.wav",
        input_type="audio",
        duration=1.0,
        sample_rate=16000,
        analysis_audio_path=audio_path,
    )
    db_session.add(analysis)
    db_session.commit()

    progress = get_pipeline_progress(analysis_id, db_session)
    assert progress.analysis_id == analysis_id
    assert progress.status in ["pending", "processing"]
    assert progress.total_steps == 10
    assert progress.progress_percent >= 10
    assert progress.stages[0].status == "completed"  # Ingestion
    assert progress.stages[1].status in ["pending", "running"]


def test_get_pipeline_progress_completed_state(db_session: Session):
    # Use precomputed keynote demo
    from app.services.demo_service import load_demo_sample
    analysis_id = "11111111-0000-0000-0000-000000000001"
    load_demo_sample(db_session, "demo-keynote")

    progress = get_pipeline_progress(analysis_id, db_session)
    assert progress.analysis_id == analysis_id
    assert progress.status == "completed"
    assert progress.progress_percent == 100
    assert all(s.status == "completed" for s in progress.stages)


def test_run_pipeline_end_to_end_on_audio(db_session: Session):
    analysis_id = str(uuid.uuid4())
    test_dir = os.path.join("uploads", analysis_id)
    os.makedirs(test_dir, exist_ok=True)
    audio_path = os.path.join(test_dir, "analysis_audio.wav")
    _generate_test_wav(audio_path, duration_sec=1.5, freq=180.0)

    analysis = Analysis(
        id=analysis_id,
        status="pending",
        stage="media_ready",
        original_filename="e2e_speech.wav",
        input_type="audio",
        duration=1.5,
        sample_rate=16000,
        analysis_audio_path=audio_path,
    )
    db_session.add(analysis)
    db_session.commit()

    response = run_pipeline(
        analysis_id=analysis_id,
        db=db_session,
        delivery_weight=0.50,
        content_weight=0.50,
    )

    assert isinstance(response, ProcessAllResponse)
    assert response.status == "completed"
    assert response.analysis_id == analysis_id
    assert response.stages_completed == 10
    assert response.overall_score is not None
    assert 0.0 <= response.overall_score <= 100.0
    assert response.letter_grade in ["A+", "A", "B+", "B", "C+", "C", "D", "F"]
    assert response.tier in ["Master", "Proficient", "Competent", "Developing", "Novice"]

    # Verify database state
    db_session.refresh(analysis)
    assert analysis.status == "completed"
    assert analysis.stage == "completed"
    assert analysis.delivery_transcript is not None
    assert analysis.content_analysis_json is not None
    assert analysis.reference_audio_path is not None and os.path.exists(analysis.reference_audio_path)
    assert analysis.alignment_json is not None
    assert analysis.features_json is not None
    assert analysis.comparison_json is not None
    assert analysis.flaws_json is not None
    assert analysis.explanations_json is not None
    assert analysis.scores_json is not None


def test_pipeline_missing_audio_raises_error(db_session: Session):
    analysis_id = str(uuid.uuid4())
    analysis = Analysis(
        id=analysis_id,
        status="pending",
        stage="media_ready",
        original_filename="missing_speech.wav",
        input_type="audio",
        duration=1.0,
        analysis_audio_path="nonexistent/audio/path.wav",
    )
    db_session.add(analysis)
    db_session.commit()

    with pytest.raises(ValueError, match="Standardized participant audio not found"):
        run_pipeline(analysis_id, db_session)


def test_api_pipeline_endpoints(db_session: Session):
    # 1. Test 404 on nonexistent analysis
    res_404 = client.post("/api/analysis/nonexistent-id/process-all")
    assert res_404.status_code == 404

    res_prog_404 = client.get("/api/analysis/nonexistent-id/progress")
    assert res_prog_404.status_code == 404

    # 2. Test progress endpoint on seeded keynote
    from app.services.demo_service import load_demo_sample
    keynote_id = "11111111-0000-0000-0000-000000000001"
    load_demo_sample(db_session, "demo-keynote")

    prog_res = client.get(f"/api/analysis/{keynote_id}/progress")
    assert prog_res.status_code == 200
    prog_data = prog_res.json()
    assert prog_data["analysis_id"] == keynote_id
    assert prog_data["progress_percent"] == 100
    assert len(prog_data["stages"]) == 10

    # 3. Test process-all on already completed analysis (idempotent re-scoring)
    proc_res = client.post(
        f"/api/analysis/{keynote_id}/process-all",
        json={"delivery_weight": 0.6, "content_weight": 0.4},
    )
    assert proc_res.status_code == 200
    proc_data = proc_res.json()
    assert proc_data["analysis_id"] == keynote_id
    assert proc_data["status"] == "completed"
    assert proc_data["stages_completed"] == 10
    assert proc_data["overall_score"] is not None


def test_api_upload_and_process():
    temp_wav = "uploads/test_upload_and_process.wav"
    _generate_test_wav(temp_wav, duration_sec=1.0, freq=240.0)

    try:
        with open(temp_wav, "rb") as f:
            res = client.post(
                "/api/analysis/upload-and-process",
                files={"file": ("test_upload_process.wav", f, "audio/wav")},
                data={"delivery_weight": "0.5", "content_weight": "0.5"},
            )

        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "completed"
        assert data["stages_completed"] == 10
        assert data["overall_score"] is not None
        assert data["letter_grade"] in ["A+", "A", "B+", "B", "C+", "C", "D", "F"]
        assert data["results_url"].startswith("/results/")
    finally:
        if os.path.exists(temp_wav):
            try:
                os.remove(temp_wav)
            except Exception:
                pass
