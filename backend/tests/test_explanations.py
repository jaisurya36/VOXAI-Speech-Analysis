import json
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.database import SessionLocal, init_db
from app.models.analysis import Analysis
from app.services.explanation_service import (
    _deterministic_causal_reasoning,
    explain_and_store,
)

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()


def test_deterministic_causal_reasoning_fast_sprinter():
    """Identifies High-Velocity Sprinter archetype when tempo is elevated."""
    comparison = {
        "pace": {"delta_wpm": 32.0, "participant_wpm": 168.0, "reference_wpm": 136.0},
        "pitch": {"pitch_variation_ratio": 1.1},
        "pause": {"delta_pause_count": 0},
        "energy": {"energy_ratio": 1.0},
    }
    features = {}
    flaws = [
        {
            "id": "flaw-1",
            "flaw_type": "compressed_syllables",
            "start_time": 1.2,
            "end_time": 1.35,
            "duration": 0.15,
            "affected_text": "specifically",
            "metric_evidence": {"duration_ratio": 0.42},
        }
    ]

    res = _deterministic_causal_reasoning(flaws, comparison, features, analysis_id="test-fast")
    assert res.analysis_id == "test-fast"
    assert res.status == "explained"
    assert "Sprinter" in res.diagnosis.archetype.name
    assert len(res.diagnosis.top_root_causes) > 0
    assert len(res.flaw_explanations) == 1
    assert "lingual contact" in res.flaw_explanations[0].physiological_factor.lower()
    assert "staccato" in res.flaw_explanations[0].remedial_drill.lower()


def test_deterministic_causal_reasoning_monotone():
    """Identifies Controlled Analytical Monotone archetype when pitch variation is suppressed."""
    comparison = {
        "pace": {"delta_wpm": 2.0},
        "pitch": {"pitch_variation_ratio": 0.52},
        "pause": {"delta_pause_count": 0},
        "energy": {"energy_ratio": 0.95},
    }
    features = {}
    flaws = [
        {
            "id": "flaw-mono",
            "flaw_type": "monotone_passage",
            "start_time": 2.0,
            "end_time": 4.5,
            "duration": 2.5,
            "affected_text": "we must examine the core structure",
            "metric_evidence": {"participant_f0_std": 4.8, "reference_f0_std": 18.5},
        }
    ]

    res = _deterministic_causal_reasoning(flaws, comparison, features, analysis_id="test-mono")
    assert "Monotone" in res.diagnosis.archetype.name
    assert len(res.flaw_explanations) == 1
    assert "cricothyroid" in res.flaw_explanations[0].physiological_factor.lower()
    assert "pitch" in res.flaw_explanations[0].remedial_drill.lower()


def test_deterministic_causal_reasoning_energy_drop():
    """Attributes trailing energy drop to subglottic pressure depletion."""
    comparison = {
        "pace": {"delta_wpm": -5.0},
        "pitch": {"pitch_variation_ratio": 0.9},
        "pause": {"delta_pause_count": 1},
        "energy": {"energy_ratio": 0.85},
    }
    features = {}
    flaws = [
        {
            "id": "flaw-energy",
            "flaw_type": "trailing_energy_drop",
            "start_time": 3.5,
            "end_time": 4.2,
            "duration": 0.7,
            "affected_text": "before we conclude",
            "metric_evidence": {"drop_percentage": 68.5},
        }
    ]

    res = _deterministic_causal_reasoning(flaws, comparison, features, analysis_id="test-energy")
    expl = res.flaw_explanations[0]
    assert "subglottic" in expl.physiological_factor.lower() or "air depletion" in expl.physiological_factor.lower()
    assert "anchor" in expl.remedial_drill.lower()


def test_explain_and_store_db_integration():
    """explain_and_store persists explanations_json in DB and updates stage."""
    db = SessionLocal()
    analysis_id = str(uuid.uuid4())

    features_dict = {"participant_features": {"rhythm": {"total_duration": 4.0}}}
    comparison_dict = {
        "pace": {"delta_wpm": 5.0},
        "pitch": {"pitch_variation_ratio": 0.95},
        "pause": {"delta_pause_count": 0},
        "energy": {"energy_ratio": 1.0},
        "summary": {"overall_similarity_score": 88.0},
    }
    flaws_dict = {
        "summary": {"total_flaws": 1, "high_severity_count": 0, "medium_severity_count": 1, "low_severity_count": 0, "flaw_density_per_minute": 15.0, "flaws_by_category": {"pause": 1}, "primary_concern": "Pause gap"},
        "flaws": [
            {
                "id": "f-1",
                "flaw_type": "excessive_pause",
                "category": "pause",
                "severity": "medium",
                "start_time": 1.0,
                "end_time": 2.2,
                "duration": 1.2,
                "affected_text": "hello ... world",
                "metric_evidence": {"participant_pause_duration": 1.2, "reference_pause_duration": 0.2},
                "suggestion": "Keep tempo",
            }
        ],
    }

    record = Analysis(
        id=analysis_id,
        status="completed",
        stage="flaws_detected",
        original_filename="sample.wav",
        input_type="audio",
        analysis_audio_path="fake/path.wav",
        reference_audio_path="fake/ref.wav",
        raw_transcript="hello world",
        features_json=json.dumps(features_dict),
        comparison_json=json.dumps(comparison_dict),
        flaws_json=json.dumps(flaws_dict),
    )
    db.add(record)
    db.commit()

    try:
        res = explain_and_store(db, analysis_id)
        assert res.analysis_id == analysis_id
        assert res.status == "explained"
        assert len(res.flaw_explanations) == 1

        updated = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        assert updated.stage == "explained"
        assert updated.explanations_json is not None
        saved = json.loads(updated.explanations_json)
        assert "diagnosis" in saved
        assert "archetype" in saved["diagnosis"]
    finally:
        db.close()


def test_api_explanations_endpoints():
    """Test POST /api/analysis/{id}/explain and GET /api/analysis/{id}/explanations."""
    analysis_id = str(uuid.uuid4())

    # 404 on missing analysis
    res = client.get(f"/api/analysis/{analysis_id}/explanations")
    assert res.status_code == 404

    db = SessionLocal()
    features_dict = {"participant_features": {"rhythm": {"total_duration": 3.0}}}
    comparison_dict = {
        "pace": {"delta_wpm": 0.0},
        "pitch": {"pitch_variation_ratio": 1.0},
        "pause": {"delta_pause_count": 0},
        "energy": {"energy_ratio": 1.0},
        "summary": {},
    }
    flaws_dict = {
        "summary": {"total_flaws": 0, "high_severity_count": 0, "medium_severity_count": 0, "low_severity_count": 0, "flaw_density_per_minute": 0.0, "flaws_by_category": {}, "primary_concern": "Optimal"},
        "flaws": [],
    }

    record = Analysis(
        id=analysis_id,
        status="completed",
        stage="flaws_detected",
        original_filename="sample.wav",
        input_type="audio",
        analysis_audio_path="fake/path.wav",
        reference_audio_path="fake/ref.wav",
        features_json=json.dumps(features_dict),
        comparison_json=json.dumps(comparison_dict),
        flaws_json=json.dumps(flaws_dict),
    )
    db.add(record)
    db.commit()
    db.close()

    # Before explanation: GET returns 404
    assert client.get(f"/api/analysis/{analysis_id}/explanations").status_code == 404

    # POST triggers explanation
    post_res = client.post(f"/api/analysis/{analysis_id}/explain")
    assert post_res.status_code == 200
    data = post_res.json()
    assert data["status"] == "explained"
    assert "diagnosis" in data

    # After explanation: GET returns 200
    get_res = client.get(f"/api/analysis/{analysis_id}/explanations")
    assert get_res.status_code == 200
    assert get_res.json()["diagnosis"]["archetype"]["name"] == data["diagnosis"]["archetype"]["name"]
