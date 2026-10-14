import json
import uuid
import pytest
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.models.database import SessionLocal, init_db
from app.models.analysis import Analysis
from app.services.comparison_service import (
    compute_dtw_1d,
    compute_mfcc_cosine_distance,
    build_word_comparison,
    compare_tracks,
    compare_and_store,
)

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()


def test_compute_dtw_identical():
    """DTW between identical series must yield 0 cost."""
    series = [float(x) for x in np.sin(np.linspace(0, 3.14, 50))]
    res = compute_dtw_1d(series, series)
    assert res.accumulated_cost == 0.0
    assert res.normalized_distance == 0.0
    assert res.path_length >= 50
    assert len(res.sample_path) > 0


def test_compute_dtw_shifted():
    """DTW on shifted series must produce a valid positive cost and downsampled path."""
    s1 = [100.0 + 10.0 * np.sin(x) for x in np.linspace(0, 10, 50)]
    s2 = [100.0 + 10.0 * np.sin(x + 0.5) for x in np.linspace(0, 10, 50)]
    res = compute_dtw_1d(s1, s2)
    assert res.accumulated_cost > 0.0
    assert res.normalized_distance > 0.0
    assert len(res.sample_path) <= 20
    assert res.sample_path[0].participant_index == 0
    assert res.sample_path[-1].normalized_participant_time == 1.0


def test_compute_dtw_empty_edge_case():
    """Empty or 1-element arrays should return gracefully without crashing."""
    res = compute_dtw_1d([], [])
    assert res.accumulated_cost == 0.0
    assert res.normalized_distance == 0.0

    res2 = compute_dtw_1d([1.0], [2.0])
    assert res2.accumulated_cost == 0.0


def test_mfcc_cosine_distance():
    """Cosine distance between identical vectors is 0.0; non-identical > 0.0."""
    v1 = [1.0, 2.0, 3.0, 4.0, 5.0] + [0.0] * 8
    assert compute_mfcc_cosine_distance(v1, v1) == 0.0

    v2 = [-1.0, -2.0, -3.0, -4.0, -5.0] + [0.0] * 8
    dist = compute_mfcc_cosine_distance(v1, v2)
    assert dist > 1.5  # Opposite vectors


def test_build_word_comparison():
    """Word comparison correctly computes duration ratios and tempo/emphasis flags."""
    aligned_words = [
        {
            "word": "Artificial",
            "participant_start": 0.0,
            "participant_end": 0.8,
            "reference_start": 0.0,
            "reference_end": 0.4,
        },
        {
            "word": "intelligence",
            "participant_start": 0.8,
            "participant_end": 1.1,
            "reference_start": 0.4,
            "reference_end": 0.9,
        },
    ]
    p_feats = [
        {"word": "Artificial", "start": 0.0, "end": 0.8, "mean_f0": 160.0, "mean_energy": 0.08},
        {"word": "intelligence", "start": 0.8, "end": 1.1, "mean_f0": 150.0, "mean_energy": 0.05},
    ]
    r_feats = [
        {"word": "Artificial", "start": 0.0, "end": 0.4, "mean_f0": 140.0, "mean_energy": 0.05},
        {"word": "intelligence", "start": 0.4, "end": 0.9, "mean_f0": 145.0, "mean_energy": 0.05},
    ]

    items = build_word_comparison(aligned_words, p_feats, r_feats)
    assert len(items) == 2
    # First word: 0.8s vs 0.4s -> ratio 2.0 -> stretched
    assert items[0].word == "Artificial"
    assert items[0].tempo_flag == "stretched"
    assert items[0].pitch_delta_hz == 20.0
    # Second word: 0.3s vs 0.5s -> ratio 0.6 -> compressed
    assert items[1].word == "intelligence"
    assert items[1].tempo_flag == "compressed"


def test_compare_tracks_full_metrics():
    """compare_tracks computes mathematically valid scores and deviations."""
    p_data = {
        "pitch": {
            "mean_f0": 135.0,
            "median_f0": 134.0,
            "std_f0": 14.0,
            "pitch_range_semitones": 6.0,
            "contour": [130.0 + np.sin(x) * 10 for x in np.linspace(0, 6, 100)],
        },
        "energy": {
            "mean_rms": 0.045,
            "std_rms": 0.015,
            "dynamic_range_db": 28.0,
            "contour": [0.04 + np.sin(x) * 0.02 for x in np.linspace(0, 6, 100)],
        },
        "spectral": {
            "mean_spectral_centroid": 1800.0,
            "mean_spectral_bandwidth": 1600.0,
            "mean_spectral_rolloff": 3400.0,
            "mean_zero_crossing_rate": 0.07,
        },
        "mfcc": {
            "mean_mfcc": [-150.0, 100.0, -20.0, 15.0] + [2.0] * 9,
            "std_mfcc": [20.0] * 13,
        },
        "rhythm": {
            "total_duration": 4.5,
            "speaking_duration": 3.8,
            "pause_duration": 0.7,
            "pause_count": 2,
            "mean_pause_duration": 0.35,
            "pause_to_speech_ratio": 0.18,
            "words_per_minute": 155.0,
            "articulation_rate": 180.0,
        },
        "word_features": [],
    }

    r_data = {
        "pitch": {
            "mean_f0": 140.0,
            "median_f0": 140.0,
            "std_f0": 22.0,
            "pitch_range_semitones": 10.5,
            "contour": [140.0 + np.sin(x) * 15 for x in np.linspace(0, 6, 100)],
        },
        "energy": {
            "mean_rms": 0.055,
            "std_rms": 0.02,
            "dynamic_range_db": 32.0,
            "contour": [0.05 + np.sin(x) * 0.02 for x in np.linspace(0, 6, 100)],
        },
        "spectral": {
            "mean_spectral_centroid": 1900.0,
            "mean_spectral_bandwidth": 1700.0,
            "mean_spectral_rolloff": 3600.0,
            "mean_zero_crossing_rate": 0.065,
        },
        "mfcc": {
            "mean_mfcc": [-145.0, 102.0, -18.0, 14.0] + [2.1] * 9,
            "std_mfcc": [18.0] * 13,
        },
        "rhythm": {
            "total_duration": 4.2,
            "speaking_duration": 3.6,
            "pause_duration": 0.6,
            "pause_count": 2,
            "mean_pause_duration": 0.30,
            "pause_to_speech_ratio": 0.17,
            "words_per_minute": 140.0,
            "articulation_rate": 165.0,
        },
        "word_features": [],
    }

    resp = compare_tracks(p_data, r_data, analysis_id="test-123")
    assert resp.analysis_id == "test-123"
    assert resp.status == "compared"
    # Verify scores in range [0, 100]
    assert 0.0 <= resp.summary.overall_similarity_score <= 100.0
    assert 0.0 <= resp.pace.similarity_score <= 100.0
    assert 0.0 <= resp.pitch.similarity_score <= 100.0
    assert 0.0 <= resp.pause.similarity_score <= 100.0
    assert 0.0 <= resp.energy.similarity_score <= 100.0
    assert 0.0 <= resp.timbre.similarity_score <= 100.0

    # Verify DTW metrics
    assert resp.pitch.dtw.accumulated_cost >= 0.0
    assert resp.energy.dtw.accumulated_cost >= 0.0

    # Verify delta calculations
    assert resp.pace.delta_wpm == 15.0
    assert resp.pause.delta_pause_count == 0


def test_compare_and_store_db_integration():
    """compare_and_store correctly persists comparison_json and sets stage='compared'."""
    db = SessionLocal()
    analysis_id = str(uuid.uuid4())
    p_contour = [120.0 + 5.0 * np.sin(x) for x in np.linspace(0, 3, 100)]
    r_contour = [125.0 + 8.0 * np.sin(x) for x in np.linspace(0, 3, 100)]
    e_contour = [0.05] * 100

    features_payload = {
        "analysis_id": analysis_id,
        "status": "extracted",
        "participant_features": {
            "pitch": {"mean_f0": 120.0, "median_f0": 120.0, "std_f0": 15.0, "min_f0": 90.0, "max_f0": 160.0, "pitch_range_semitones": 8.0, "voiced_fraction": 0.75, "contour": p_contour},
            "energy": {"mean_rms": 0.05, "std_rms": 0.02, "max_rms": 0.1, "dynamic_range_db": 30.0, "contour": e_contour},
            "spectral": {"mean_spectral_centroid": 1800.0, "mean_spectral_bandwidth": 1600.0, "mean_spectral_rolloff": 3400.0, "mean_zero_crossing_rate": 0.07},
            "mfcc": {"mean_mfcc": [1.0] * 13, "std_mfcc": [0.5] * 13},
            "rhythm": {"total_duration": 3.0, "speaking_duration": 2.5, "pause_duration": 0.5, "pause_count": 1, "mean_pause_duration": 0.5, "pause_to_speech_ratio": 0.2, "words_per_minute": 130.0, "articulation_rate": 150.0},
            "word_features": [],
        },
        "reference_features": {
            "pitch": {"mean_f0": 125.0, "median_f0": 125.0, "std_f0": 20.0, "min_f0": 95.0, "max_f0": 170.0, "pitch_range_semitones": 10.0, "voiced_fraction": 0.80, "contour": r_contour},
            "energy": {"mean_rms": 0.055, "std_rms": 0.02, "max_rms": 0.11, "dynamic_range_db": 32.0, "contour": e_contour},
            "spectral": {"mean_spectral_centroid": 1850.0, "mean_spectral_bandwidth": 1650.0, "mean_spectral_rolloff": 3500.0, "mean_zero_crossing_rate": 0.065},
            "mfcc": {"mean_mfcc": [1.0] * 13, "std_mfcc": [0.5] * 13},
            "rhythm": {"total_duration": 2.8, "speaking_duration": 2.4, "pause_duration": 0.4, "pause_count": 1, "mean_pause_duration": 0.4, "pause_to_speech_ratio": 0.17, "words_per_minute": 135.0, "articulation_rate": 155.0},
            "word_features": [],
        },
        "time_axis": list(np.linspace(0.0, 1.0, 100)),
        "message": "OK",
    }

    record = Analysis(
        id=analysis_id,
        status="completed",
        stage="features_extracted",
        original_filename="sample.wav",
        input_type="audio",
        analysis_audio_path="fake/path.wav",
        reference_audio_path="fake/ref.wav",
        features_json=json.dumps(features_payload),
    )
    db.add(record)
    db.commit()

    try:
        result = compare_and_store(db, analysis_id)
        assert result.analysis_id == analysis_id
        assert result.status == "compared"

        # Query DB to verify persistence
        updated = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        assert updated.stage == "compared"
        assert updated.comparison_json is not None
        stored_data = json.loads(updated.comparison_json)
        assert stored_data["summary"]["overall_similarity_score"] > 0
    finally:
        db.close()


def test_api_comparison_endpoints():
    """Test POST /api/analysis/{id}/compare and GET /api/analysis/{id}/comparison."""
    analysis_id = str(uuid.uuid4())

    # 404 for non-existent analysis
    res = client.get(f"/api/analysis/{analysis_id}/comparison")
    assert res.status_code == 404

    db = SessionLocal()
    p_contour = [110.0] * 100
    r_contour = [120.0] * 100
    e_contour = [0.05] * 100

    features_dict = {
        "analysis_id": analysis_id,
        "status": "extracted",
        "participant_features": {
            "pitch": {"mean_f0": 110.0, "median_f0": 110.0, "std_f0": 10.0, "min_f0": 90.0, "max_f0": 140.0, "pitch_range_semitones": 6.0, "voiced_fraction": 0.7, "contour": p_contour},
            "energy": {"mean_rms": 0.04, "std_rms": 0.01, "max_rms": 0.08, "dynamic_range_db": 25.0, "contour": e_contour},
            "spectral": {"mean_spectral_centroid": 1700.0, "mean_spectral_bandwidth": 1500.0, "mean_spectral_rolloff": 3200.0, "mean_zero_crossing_rate": 0.06},
            "mfcc": {"mean_mfcc": [0.5] * 13, "std_mfcc": [0.2] * 13},
            "rhythm": {"total_duration": 3.0, "speaking_duration": 2.5, "pause_duration": 0.5, "pause_count": 1, "mean_pause_duration": 0.5, "pause_to_speech_ratio": 0.2, "words_per_minute": 120.0, "articulation_rate": 140.0},
            "word_features": [],
        },
        "reference_features": {
            "pitch": {"mean_f0": 120.0, "median_f0": 120.0, "std_f0": 18.0, "min_f0": 95.0, "max_f0": 160.0, "pitch_range_semitones": 9.0, "voiced_fraction": 0.8, "contour": r_contour},
            "energy": {"mean_rms": 0.05, "std_rms": 0.02, "max_rms": 0.1, "dynamic_range_db": 30.0, "contour": e_contour},
            "spectral": {"mean_spectral_centroid": 1800.0, "mean_spectral_bandwidth": 1600.0, "mean_spectral_rolloff": 3400.0, "mean_zero_crossing_rate": 0.065},
            "mfcc": {"mean_mfcc": [0.5] * 13, "std_mfcc": [0.2] * 13},
            "rhythm": {"total_duration": 2.8, "speaking_duration": 2.4, "pause_duration": 0.4, "pause_count": 1, "mean_pause_duration": 0.4, "pause_to_speech_ratio": 0.17, "words_per_minute": 135.0, "articulation_rate": 155.0},
            "word_features": [],
        },
        "time_axis": list(np.linspace(0.0, 1.0, 100)),
        "message": "OK",
    }

    record = Analysis(
        id=analysis_id,
        status="completed",
        stage="features_extracted",
        original_filename="sample.wav",
        input_type="audio",
        analysis_audio_path="fake/path.wav",
        reference_audio_path="fake/ref.wav",
        features_json=json.dumps(features_dict),
    )
    db.add(record)
    db.commit()
    db.close()

    # Before comparison: GET returns 404
    res = client.get(f"/api/analysis/{analysis_id}/comparison")
    assert res.status_code == 404

    # POST triggers comparison
    post_res = client.post(f"/api/analysis/{analysis_id}/compare")
    assert post_res.status_code == 200
    data = post_res.json()
    assert data["status"] == "compared"
    assert "summary" in data
    assert "pitch" in data
    assert "pace" in data

    # After comparison: GET returns 200 with saved comparison data
    get_res = client.get(f"/api/analysis/{analysis_id}/comparison")
    assert get_res.status_code == 200
    assert get_res.json()["summary"]["overall_similarity_score"] == data["summary"]["overall_similarity_score"]
