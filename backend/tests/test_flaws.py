import json
import uuid
import pytest
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.models.database import SessionLocal, init_db
from app.models.analysis import Analysis
from app.services.flaw_detection_service import (
    detect_pause_flaws,
    detect_word_tempo_flaws,
    detect_monotone_passages,
    detect_energy_dynamics_flaws,
    scan_temporal_flaws,
    detect_and_store_flaws,
)

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()


def test_detect_pause_flaws():
    """Detects excessive silence pauses and rushed collisions at punctuation."""
    words = [
        {"word": "Welcome,", "participant_start": 0.0, "participant_end": 0.5, "reference_start": 0.0, "reference_end": 0.5},
        # Gap: 2.1s - 0.5s = 1.6s (Excessive pause)
        {"word": "everyone.", "participant_start": 2.1, "participant_end": 2.6, "reference_start": 0.8, "reference_end": 1.3},
        # Gap: 2.62s - 2.60s = 0.02s at punctuation (Rushed transition)
        {"word": "Today", "participant_start": 2.62, "participant_end": 3.0, "reference_start": 1.7, "reference_end": 2.1},
    ]
    flaws = detect_pause_flaws(words, total_duration=3.5)
    assert len(flaws) >= 2
    types = [f.flaw_type for f in flaws]
    assert "excessive_pause" in types
    assert "rushed_transition" in types
    # Check severity on 1.6s pause
    excessive_flaw = next(f for f in flaws if f.flaw_type == "excessive_pause")
    assert excessive_flaw.severity == "high"
    assert excessive_flaw.duration == 1.6


def test_detect_word_tempo_flaws():
    """Detects compressed words and drawn out syllables."""
    comp_items = [
        {
            "word": "specifically",
            "participant_start": 0.0,
            "participant_end": 0.12,
            "participant_duration": 0.12,
            "reference_duration": 0.35,
            "duration_ratio": 0.34,
            "tempo_flag": "compressed",
        },
        {
            "word": "important",
            "participant_start": 0.2,
            "participant_end": 1.1,
            "participant_duration": 0.90,
            "reference_duration": 0.40,
            "duration_ratio": 2.25,
            "tempo_flag": "stretched",
        },
        {
            "word": "concept",
            "participant_start": 1.2,
            "participant_end": 1.6,
            "participant_duration": 0.40,
            "reference_duration": 0.38,
            "duration_ratio": 1.05,
            "tempo_flag": "normal",
        },
    ]
    flaws = detect_word_tempo_flaws(comp_items)
    assert len(flaws) == 2
    flaw_types = [f.flaw_type for f in flaws]
    assert "compressed_syllables" in flaw_types
    assert "drawn_out_syllable" in flaw_types


def test_detect_monotone_passages():
    """Identifies extended flat pitch sequences with low standard deviation."""
    flat_pitch = [120.0 + float(np.random.normal(0, 0.5)) for _ in range(100)]
    ref_pitch = [120.0 + float(np.sin(x) * 25.0) for x in np.linspace(0, 10, 100)]
    words = [{"word": "Test", "participant_start": 0.5, "participant_end": 1.5}]

    flaws = detect_monotone_passages(
        p_pitch_contour=flat_pitch,
        r_pitch_contour=ref_pitch,
        total_duration=5.0,
        words_list=words,
        window_frames=15,
    )
    assert len(flaws) >= 1
    assert flaws[0].flaw_type == "monotone_passage"
    assert flaws[0].category == "pitch"
    assert flaws[0].severity in ("medium", "high")


def test_detect_energy_dynamics_flaws():
    """Detects phrase-ending trailing off and harsh volume bursts."""
    # Contour with volume spike in middle
    energy = [0.03] * 100
    energy[40] = 0.12
    energy[41] = 0.14
    energy[42] = 0.11

    phrases = [
        {
            "text": "This is a long sentence fading out",
            "participant_start": 0.0,
            "participant_end": 3.0,
        }
    ]
    # Simulate tail drop
    energy[25:30] = [0.005] * 5

    flaws = detect_energy_dynamics_flaws(
        p_energy_contour=energy,
        total_duration=4.0,
        phrases_list=phrases,
    )
    types = [f.flaw_type for f in flaws]
    assert "overprojection_burst" in types


def test_scan_temporal_flaws_full():
    """scan_temporal_flaws compiles summary, density, and categorized flaws."""
    features_data = {
        "participant_features": {
            "pitch": {"contour": [120.0] * 100},
            "energy": {"contour": [0.04] * 100},
            "rhythm": {"total_duration": 6.0},
        },
        "reference_features": {
            "pitch": {"contour": [120.0 + np.sin(x) * 20 for x in np.linspace(0, 6, 100)]},
            "energy": {"contour": [0.05] * 100},
            "rhythm": {"total_duration": 5.8},
        },
    }
    comparison_data = {
        "aligned_words_comparison": [
            {
                "word": "demonstration",
                "participant_start": 1.0,
                "participant_end": 1.12,
                "participant_duration": 0.12,
                "reference_duration": 0.35,
                "duration_ratio": 0.34,
                "tempo_flag": "compressed",
            }
        ]
    }
    alignment_data = {
        "aligned_words": [
            {"word": "First,", "participant_start": 0.0, "participant_end": 0.4, "reference_start": 0.0, "reference_end": 0.4},
            {"word": "second", "participant_start": 1.8, "participant_end": 2.2, "reference_start": 0.7, "reference_end": 1.1},
        ],
        "aligned_phrases": [],
    }

    res = scan_temporal_flaws(features_data, comparison_data, alignment_data, analysis_id="test-scan")
    assert res.analysis_id == "test-scan"
    assert res.status == "flaws_detected"
    assert res.summary.total_flaws > 0
    assert res.summary.flaw_density_per_minute > 0
    assert len(res.summary.primary_concern) > 5


def test_detect_and_store_flaws_db_integration():
    """detect_and_store_flaws persists flaws_json and sets stage='flaws_detected'."""
    db = SessionLocal()
    analysis_id = str(uuid.uuid4())

    features_dict = {
        "analysis_id": analysis_id,
        "status": "extracted",
        "participant_features": {
            "pitch": {"contour": [120.0] * 100},
            "energy": {"contour": [0.04] * 100},
            "rhythm": {"total_duration": 4.0},
        },
        "reference_features": {
            "pitch": {"contour": [120.0 + np.sin(x) * 20 for x in np.linspace(0, 6, 100)]},
            "energy": {"contour": [0.05] * 100},
            "rhythm": {"total_duration": 3.8},
        },
    }
    comp_dict = {
        "analysis_id": analysis_id,
        "status": "compared",
        "aligned_words_comparison": [],
    }
    record = Analysis(
        id=analysis_id,
        status="completed",
        stage="compared",
        original_filename="sample.wav",
        input_type="audio",
        analysis_audio_path="fake/path.wav",
        reference_audio_path="fake/ref.wav",
        features_json=json.dumps(features_dict),
        comparison_json=json.dumps(comp_dict),
    )
    db.add(record)
    db.commit()

    try:
        res = detect_and_store_flaws(db, analysis_id)
        assert res.analysis_id == analysis_id
        assert res.status == "flaws_detected"

        updated = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        assert updated.stage == "flaws_detected"
        assert updated.flaws_json is not None
        data = json.loads(updated.flaws_json)
        assert "summary" in data
        assert "flaws" in data
    finally:
        db.close()


def test_api_flaws_endpoints():
    """Test POST /api/analysis/{id}/detect-flaws and GET /api/analysis/{id}/flaws."""
    analysis_id = str(uuid.uuid4())

    # 404 on missing analysis
    res = client.get(f"/api/analysis/{analysis_id}/flaws")
    assert res.status_code == 404

    db = SessionLocal()
    features_dict = {
        "analysis_id": analysis_id,
        "participant_features": {
            "pitch": {"contour": [120.0] * 100},
            "energy": {"contour": [0.04] * 100},
            "rhythm": {"total_duration": 4.0},
        },
        "reference_features": {
            "pitch": {"contour": [120.0 + np.sin(x) * 15 for x in np.linspace(0, 6, 100)]},
            "energy": {"contour": [0.05] * 100},
            "rhythm": {"total_duration": 3.8},
        },
    }
    comp_dict = {
        "analysis_id": analysis_id,
        "aligned_words_comparison": [],
    }
    record = Analysis(
        id=analysis_id,
        status="completed",
        stage="compared",
        original_filename="sample.wav",
        input_type="audio",
        analysis_audio_path="fake/path.wav",
        reference_audio_path="fake/ref.wav",
        features_json=json.dumps(features_dict),
        comparison_json=json.dumps(comp_dict),
    )
    db.add(record)
    db.commit()
    db.close()

    # Before detection: GET returns 404
    assert client.get(f"/api/analysis/{analysis_id}/flaws").status_code == 404

    # POST triggers detection
    post_res = client.post(f"/api/analysis/{analysis_id}/detect-flaws")
    assert post_res.status_code == 200
    data = post_res.json()
    assert data["status"] == "flaws_detected"
    assert "flaws" in data
    assert "summary" in data

    # After detection: GET returns 200
    get_res = client.get(f"/api/analysis/{analysis_id}/flaws")
    assert get_res.status_code == 200
    assert get_res.json()["summary"]["total_flaws"] == data["summary"]["total_flaws"]
