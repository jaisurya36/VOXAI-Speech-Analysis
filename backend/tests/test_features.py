import os
import wave
import json
import pytest
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.models.database import SessionLocal, init_db
from app.models.analysis import Analysis
from app.services.feature_service import (
    load_audio_array,
    extract_pitch_features,
    extract_energy_features,
    extract_spectral_features,
    extract_mfcc_features,
    extract_rhythm_features,
    extract_word_acoustic_features,
)

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()


def create_test_wav(filepath: str, duration: float = 2.0, freq: float = 200.0, sr: int = 16000):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Fundamental + harmonics to simulate vocal tone
    samples = 0.5 * np.sin(2 * np.pi * freq * t) + 0.2 * np.sin(2 * np.pi * 2 * freq * t)
    int_samples = (samples * 32767).astype(np.int16)

    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with wave.open(filepath, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(int_samples.tobytes())


def test_extract_pitch_features_accuracy():
    sr = 16000
    duration = 2.0
    freq = 220.0  # A3 note
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    y = 0.6 * np.sin(2 * np.pi * freq * t)

    pitch = extract_pitch_features(y, sr=sr)
    assert abs(pitch.mean_f0 - freq) < 10.0
    assert abs(pitch.median_f0 - freq) < 10.0
    assert pitch.voiced_fraction > 0.85
    assert len(pitch.contour) == 100


def test_extract_pitch_empty_audio():
    empty_y = np.zeros(100, dtype=np.float32)
    pitch = extract_pitch_features(empty_y)
    assert pitch.mean_f0 == 0.0
    assert pitch.voiced_fraction == 0.0
    assert len(pitch.contour) == 100


def test_extract_energy_features():
    sr = 16000
    t = np.linspace(0, 1.5, int(sr * 1.5), endpoint=False)
    y = 0.5 * np.sin(2 * np.pi * 300 * t)

    energy = extract_energy_features(y)
    assert energy.mean_rms > 0.1
    assert energy.max_rms > energy.mean_rms
    assert len(energy.contour) == 100


def test_extract_spectral_features():
    sr = 16000
    t = np.linspace(0, 1.0, sr, endpoint=False)
    y = 0.4 * np.sin(2 * np.pi * 440 * t)

    spectral = extract_spectral_features(y, sr=sr)
    assert spectral.mean_spectral_centroid > 200.0
    assert spectral.mean_spectral_bandwidth > 0.0
    assert spectral.mean_spectral_rolloff > 0.0
    assert spectral.mean_zero_crossing_rate > 0.0


def test_extract_mfcc_features():
    sr = 16000
    t = np.linspace(0, 1.0, sr, endpoint=False)
    y = 0.5 * np.sin(2 * np.pi * 250 * t)

    mfcc = extract_mfcc_features(y, sr=sr, n_mfcc=13)
    assert len(mfcc.mean_mfcc) == 13
    assert len(mfcc.std_mfcc) == 13


def test_extract_rhythm_features():
    sr = 16000
    # 2 seconds total: 0.8s speech + 0.4s silence + 0.8s speech
    t_speech = np.linspace(0, 0.8, int(sr * 0.8), endpoint=False)
    speech = 0.5 * np.sin(2 * np.pi * 200 * t_speech)
    silence = np.zeros(int(sr * 0.4))
    y = np.concatenate([speech, silence, speech])

    rhythm = extract_rhythm_features(y, sr=sr, word_count=6)
    assert abs(rhythm.total_duration - 2.0) < 0.1
    assert rhythm.pause_count >= 1
    assert rhythm.pause_duration >= 0.2
    assert rhythm.words_per_minute > 0.0


def test_extract_word_acoustic_features():
    sr = 16000
    t = np.linspace(0, 1.0, sr, endpoint=False)
    y = 0.5 * np.sin(2 * np.pi * 220 * t)
    words = [
        {"word": "hello", "start": 0.0, "end": 0.4},
        {"word": "world", "start": 0.5, "end": 0.9},
    ]

    word_feats = extract_word_acoustic_features(y, sr, words)
    assert len(word_feats) == 2
    assert word_feats[0].word == "hello"
    assert word_feats[0].mean_energy > 0.0


def test_feature_extraction_api_flow(tmp_path):
    part_wav = str(tmp_path / "part_speech.wav")
    ref_wav = str(tmp_path / "ref_speech.wav")
    create_test_wav(part_wav, duration=2.0, freq=180.0)
    create_test_wav(ref_wav, duration=1.8, freq=190.0)

    db = SessionLocal()
    analysis = Analysis(
        original_filename="api_test_speech.wav",
        input_type="audio",
        duration=2.0,
        sample_rate=16000,
        analysis_audio_path=part_wav,
        reference_audio_path=ref_wav,
        raw_transcript="Testing acoustic feature extraction.",
        delivery_transcript="Testing acoustic feature extraction.",
        words_json=json.dumps([
            {"word": "Testing", "start": 0.0, "end": 0.5},
            {"word": "acoustic", "start": 0.5, "end": 1.0},
            {"word": "feature", "start": 1.0, "end": 1.5},
            {"word": "extraction", "start": 1.5, "end": 2.0},
        ]),
        alignment_json=json.dumps({
            "alignment_coverage": 100.0,
            "matched_word_count": 4,
            "total_participant_words": 4,
            "total_reference_words": 4,
            "aligned_words": [
                {"word": "Testing", "participant_start": 0.0, "participant_end": 0.5, "reference_start": 0.0, "reference_end": 0.45},
                {"word": "acoustic", "participant_start": 0.5, "participant_end": 1.0, "reference_start": 0.45, "reference_end": 0.9},
                {"word": "feature", "participant_start": 1.0, "participant_end": 1.5, "reference_start": 0.9, "reference_end": 1.35},
                {"word": "extraction", "participant_start": 1.5, "participant_end": 2.0, "reference_start": 1.35, "reference_end": 1.8},
            ],
            "aligned_phrases": [],
            "unmatched_participant_words": [],
            "unmatched_reference_words": [],
        }),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    analysis_id = analysis.id
    db.close()

    # Call POST extract-features
    res = client.post(f"/api/analysis/{analysis_id}/extract-features")
    assert res.status_code == 200
    data = res.json()

    assert data["analysis_id"] == analysis_id
    assert data["status"] == "completed"
    assert "participant_features" in data
    assert "reference_features" in data
    assert len(data["time_axis"]) == 100

    part_f0 = data["participant_features"]["pitch"]["mean_f0"]
    ref_f0 = data["reference_features"]["pitch"]["mean_f0"]
    assert part_f0 > 100.0
    assert ref_f0 > 100.0
    assert len(data["participant_features"]["word_features"]) == 4

    # Call GET features
    get_res = client.get(f"/api/analysis/{analysis_id}/features")
    assert get_res.status_code == 200
    assert get_res.json()["analysis_id"] == analysis_id


def test_extract_features_missing_reference_returns_400(tmp_path):
    part_wav = str(tmp_path / "part_only.wav")
    create_test_wav(part_wav, duration=1.0)

    db = SessionLocal()
    analysis = Analysis(
        original_filename="no_ref.wav",
        input_type="audio",
        analysis_audio_path=part_wav,
        reference_audio_path=None,  # Missing reference
    )
    db.add(analysis)
    db.commit()
    analysis_id = analysis.id
    db.close()

    res = client.post(f"/api/analysis/{analysis_id}/extract-features")
    assert res.status_code == 400
    assert "reference" in res.json()["detail"].lower()


def test_extract_features_nonexistent_returns_404():
    res = client.post("/api/analysis/nonexistent-id-12345/extract-features")
    assert res.status_code == 404
