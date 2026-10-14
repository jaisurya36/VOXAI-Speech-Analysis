import json
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.database import SessionLocal, init_db
from app.models.analysis import Analysis
from app.services.scoring_service import (
    determine_grade,
    determine_tier,
    calculate_percentile,
    compute_rubric_scores,
    score_and_store,
)

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()


def test_grade_and_tier_mapping():
    """Verify standard letter grades and speaker mastery tiers."""
    assert determine_grade(97.0) == "A+"
    assert determine_grade(91.5) == "A"
    assert determine_grade(86.0) == "B+"
    assert determine_grade(81.0) == "B"
    assert determine_grade(76.5) == "C+"
    assert determine_grade(71.0) == "C"
    assert determine_grade(63.0) == "D"
    assert determine_grade(48.0) == "F"

    tier, title = determine_tier(92.0)
    assert tier == "Master"
    assert "Master" in title

    tier, title = determine_tier(84.0)
    assert tier == "Proficient"
    assert "Proficient" in title

    tier, title = determine_tier(72.0)
    assert tier == "Competent"
    assert "Competent" in title

    tier, title = determine_tier(58.0)
    assert tier == "Developing"
    assert "Developing" in title

    tier, title = determine_tier(35.0)
    assert tier == "Novice"
    assert "Novice" in title


def test_percentile_calculation():
    """Verify deterministic logistic CDF percentile behavior."""
    pct_high = calculate_percentile(92.0)
    assert 90 <= pct_high <= 99

    pct_mid = calculate_percentile(68.0)
    assert 45 <= pct_mid <= 55

    pct_low = calculate_percentile(45.0)
    assert 1 <= pct_low <= 15


def test_compute_rubric_scores_high_performer():
    """Validates rubric computation for a high-performing speaker with zero flaws."""
    comparison = {
        "summary": {
            "pace_score": 92.0,
            "pitch_score": 90.0,
            "rhythm_score": 88.0,
            "energy_score": 94.0,
            "timbre_score": 89.0,
        }
    }
    flaws = {
        "summary": {
            "high_severity_count": 0,
            "medium_severity_count": 0,
            "low_severity_count": 0,
        }
    }
    content = {
        "grammar": {"score": 95, "errors": []},
        "semantics": {"score": 92, "issues": []},
        "content": {"score": 90, "strengths": ["Excellent flow", "Compelling rhetoric"]},
    }

    res = compute_rubric_scores(
        comparison_data=comparison,
        flaws_data=flaws,
        content_data=content,
        archetype="The Dynamic Orator",
        analysis_id="test-high",
    )

    assert res.analysis_id == "test-high"
    assert res.status == "scored"
    # Raw delivery: 0.20*92 + 0.25*90 + 0.20*88 + 0.20*94 + 0.15*89 = 18.4 + 22.5 + 17.6 + 18.8 + 13.35 = 90.65 -> 90.7
    assert res.delivery.raw_delivery_score >= 90.0
    assert res.delivery.total_flaw_deduction == 0.0
    assert res.delivery.net_delivery_score >= 90.0
    assert res.delivery.grade in ["A", "A+"]
    assert res.delivery.tier == "Master"
    assert res.delivery.archetype == "The Dynamic Orator"

    # Content: 0.30*95 + 0.35*92 + 0.35*90 = 28.5 + 32.2 + 31.5 = 92.2
    assert res.content.net_content_score == 92.2
    assert res.content.grade in ["A", "A+"]

    # Composite: 0.50 * 90.7 + 0.50 * 92.2 = 45.35 + 46.10 = 91.5
    assert res.summary.overall_score >= 90.0
    assert res.summary.tier == "Master"
    assert res.summary.percentile_estimate >= 90

    # 8 Dimensions verified
    assert len(res.dimensions) == 8
    assert len(res.rubric_tiers) == 5


def test_compute_rubric_scores_with_flaw_penalties():
    """Validates mathematical flaw deduction (High: -4, Med: -2, Low: -1) capped at 25.0."""
    comparison = {
        "summary": {
            "pace_score": 80.0,
            "pitch_score": 75.0,
            "rhythm_score": 70.0,
            "energy_score": 80.0,
            "timbre_score": 75.0,
        }
    }
    # 2 high (-8), 3 med (-6), 2 low (-2) = total 16.0 penalty
    flaws = {
        "summary": {
            "high_severity_count": 2,
            "medium_severity_count": 3,
            "low_severity_count": 2,
        }
    }
    content = {
        "grammar": {"score": 70, "errors": [{"original": "foo", "corrected": "bar", "explanation": "test"}]},
        "semantics": {"score": 65, "issues": []},
        "content": {"score": 70, "strengths": []},
    }

    res = compute_rubric_scores(
        comparison_data=comparison,
        flaws_data=flaws,
        content_data=content,
        analysis_id="test-flaws",
    )

    # Raw delivery: 0.20*80 + 0.25*75 + 0.20*70 + 0.20*80 + 0.15*75 = 16 + 18.75 + 14 + 16 + 11.25 = 76.0
    assert res.delivery.raw_delivery_score == 76.0
    assert res.delivery.total_flaw_deduction == 16.0
    assert res.delivery.net_delivery_score == 60.0
    assert res.delivery.tier == "Developing"

    # Verify breakdown items
    high_deduction = next(p for p in res.delivery.flaw_penalties if p.severity == "high")
    assert high_deduction.count == 2
    assert high_deduction.total_penalty == 8.0


def test_compute_rubric_scores_custom_weights():
    """Validates custom delivery/content weighting allocation."""
    comparison = {
        "summary": {
            "pace_score": 80.0,
            "pitch_score": 80.0,
            "rhythm_score": 80.0,
            "energy_score": 80.0,
            "timbre_score": 80.0,
        }
    }
    flaws = {"summary": {"high_severity_count": 0, "medium_severity_count": 0, "low_severity_count": 0}}
    content = {
        "grammar": {"score": 60, "errors": []},
        "semantics": {"score": 60, "issues": []},
        "content": {"score": 60, "strengths": []},
    }

    # 70% delivery (80.0) + 30% content (60.0) = 56.0 + 18.0 = 74.0
    res = compute_rubric_scores(
        comparison_data=comparison,
        flaws_data=flaws,
        content_data=content,
        delivery_weight=0.70,
        content_weight=0.30,
        analysis_id="test-weights",
    )

    assert res.summary.delivery_weight == 0.70
    assert res.summary.content_weight == 0.30
    assert res.summary.weighted_delivery_score == 56.0
    assert res.summary.weighted_content_score == 18.0
    assert res.summary.overall_score == 74.0


def test_score_and_store_db_integration():
    """Tests full database storage and stage transition to 'scored'."""
    db = SessionLocal()
    analysis_id = str(uuid.uuid4())

    comparison_data = {
        "summary": {
            "pace_score": 85.0,
            "pitch_score": 82.0,
            "rhythm_score": 80.0,
            "energy_score": 84.0,
            "timbre_score": 86.0,
        }
    }
    flaws_data = {
        "summary": {
            "total_flaws": 1,
            "high_severity_count": 0,
            "medium_severity_count": 1,
            "low_severity_count": 0,
        },
        "flaws": [],
    }
    content_data = {
        "grammar": {"score": 88, "errors": []},
        "semantics": {"score": 85, "issues": []},
        "content": {"score": 80, "strengths": ["Clear delivery"]},
    }

    record = Analysis(
        id=analysis_id,
        status="processing",
        stage="explained",
        original_filename="sample.wav",
        input_type="audio",
        analysis_audio_path="./tests/sample.wav",
        raw_transcript="We are ready to deliver clear speech analytics.",
        delivery_transcript="We are ready to deliver clear speech analytics.",
        comparison_json=json.dumps(comparison_data),
        flaws_json=json.dumps(flaws_data),
        content_analysis_json=json.dumps(content_data),
    )
    db.add(record)
    db.commit()

    try:
        response = score_and_store(db, analysis_id)
        assert response.analysis_id == analysis_id
        assert response.status == "scored"
        assert response.summary.overall_score > 0

        # Check DB persistence
        db.refresh(record)
        assert record.stage == "scored"
        assert record.scores_json is not None

        parsed = json.loads(record.scores_json)
        assert parsed["summary"]["overall_score"] == response.summary.overall_score
        assert parsed["delivery"]["net_delivery_score"] == response.delivery.net_delivery_score
    finally:
        db.delete(record)
        db.commit()
        db.close()


def test_api_scoring_endpoints():
    """Tests POST and GET endpoints for rubric scoring."""
    db = SessionLocal()
    analysis_id = str(uuid.uuid4())

    comparison_data = {
        "summary": {
            "pace_score": 88.0,
            "pitch_score": 84.0,
            "rhythm_score": 82.0,
            "energy_score": 86.0,
            "timbre_score": 85.0,
        }
    }
    flaws_data = {
        "summary": {
            "total_flaws": 0,
            "high_severity_count": 0,
            "medium_severity_count": 0,
            "low_severity_count": 0,
        },
        "flaws": [],
    }
    content_data = {
        "grammar": {"score": 90, "errors": []},
        "semantics": {"score": 88, "issues": []},
        "content": {"score": 85, "strengths": ["Confident tone"]},
    }

    record = Analysis(
        id=analysis_id,
        status="processing",
        stage="explained",
        original_filename="api_sample.wav",
        input_type="audio",
        analysis_audio_path="./tests/api_sample.wav",
        raw_transcript="Testing the rubric scoring endpoints.",
        delivery_transcript="Testing the rubric scoring endpoints.",
        comparison_json=json.dumps(comparison_data),
        flaws_json=json.dumps(flaws_data),
        content_analysis_json=json.dumps(content_data),
    )
    db.add(record)
    db.commit()

    try:
        # POST
        post_resp = client.post(f"/api/analysis/{analysis_id}/score?delivery_weight=0.50&content_weight=0.50")
        assert post_resp.status_code == 200
        data = post_resp.json()
        assert data["analysis_id"] == analysis_id
        assert data["status"] == "scored"
        assert "summary" in data
        assert "delivery" in data
        assert "content" in data
        assert len(data["dimensions"]) == 8

        # GET
        get_resp = client.get(f"/api/analysis/{analysis_id}/score")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["analysis_id"] == analysis_id
        assert get_data["summary"]["overall_score"] == data["summary"]["overall_score"]
    finally:
        db.delete(record)
        db.commit()
        db.close()


def test_api_scoring_nonexistent_returns_404():
    """Validates 404 behavior for unknown analysis ID."""
    resp = client.post("/api/analysis/unknown-id-xyz/score")
    assert resp.status_code == 404

    resp_get = client.get("/api/analysis/unknown-id-xyz/score")
    assert resp_get.status_code == 404


def test_api_scoring_missing_audio_returns_400():
    """Validates 400 rejection when participant audio is absent."""
    db = SessionLocal()
    analysis_id = str(uuid.uuid4())
    record = Analysis(
        id=analysis_id,
        status="pending",
        original_filename="empty.wav",
        input_type="audio",
        analysis_audio_path=None,
    )
    db.add(record)
    db.commit()

    try:
        resp = client.post(f"/api/analysis/{analysis_id}/score")
        assert resp.status_code == 400
        assert "audio is missing" in resp.json()["detail"].lower()
    finally:
        db.delete(record)
        db.commit()
        db.close()
