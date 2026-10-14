import json
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.database import SessionLocal, init_db
from app.models.analysis import Analysis
from app.services.dashboard_service import get_dashboard_data

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()


def test_get_dashboard_data_structure():
    """Verify get_dashboard_data parses and assembles all multi-track fields."""
    db = SessionLocal()
    analysis_id = str(uuid.uuid4())

    record = Analysis(
        id=analysis_id,
        status="completed",
        stage="scored",
        original_filename="dashboard_test.wav",
        input_type="audio",
        duration=12.5,
        sample_rate=16000,
        raw_transcript="Testing the unified dashboard assembly.",
        delivery_transcript="Testing the unified dashboard assembly.",
        corrected_transcript="Testing the unified dashboard assembly.",
        features_json=json.dumps({"time_axis": [0.0, 0.1, 0.2]}),
        comparison_json=json.dumps({"summary": {"overall_similarity_score": 86.5}}),
        flaws_json=json.dumps({"summary": {"total_flaws": 0}, "flaws": []}),
        explanations_json=json.dumps({"diagnosis": {"archetype": {"name": "Dynamic Orator"}}}),
        scores_json=json.dumps({"summary": {"overall_score": 88.0, "grade": "B+", "tier": "Proficient"}}),
    )
    db.add(record)
    db.commit()

    try:
        data = get_dashboard_data(db, analysis_id, auto_complete=False)
        assert data.analysis_id == analysis_id
        assert data.duration == 12.5
        assert data.features is not None
        assert data.features["time_axis"] == [0.0, 0.1, 0.2]
        assert data.comparison["summary"]["overall_similarity_score"] == 86.5
        assert data.flaws["summary"]["total_flaws"] == 0
        assert data.scores["summary"]["overall_score"] == 88.0
    finally:
        db.delete(record)
        db.commit()
        db.close()


def test_dashboard_api_endpoint():
    """Verify GET /api/analysis/{analysis_id}/dashboard returns 200 with assembled data."""
    db = SessionLocal()
    analysis_id = str(uuid.uuid4())

    record = Analysis(
        id=analysis_id,
        status="completed",
        stage="scored",
        original_filename="api_dashboard.wav",
        input_type="audio",
        duration=8.0,
        raw_transcript="Testing dashboard endpoint.",
        delivery_transcript="Testing dashboard endpoint.",
        scores_json=json.dumps({"summary": {"overall_score": 85.0}}),
    )
    db.add(record)
    db.commit()

    try:
        resp = client.get(f"/api/analysis/{analysis_id}/dashboard?auto_complete=false")
        assert resp.status_code == 200
        json_data = resp.json()
        assert json_data["analysis_id"] == analysis_id
        assert json_data["duration"] == 8.0
        assert json_data["scores"]["summary"]["overall_score"] == 85.0
    finally:
        db.delete(record)
        db.commit()
        db.close()


def test_dashboard_api_nonexistent_returns_404():
    """Verify 404 for unknown analysis ID."""
    resp = client.get("/api/analysis/nonexistent-id-xyz/dashboard")
    assert resp.status_code == 404
