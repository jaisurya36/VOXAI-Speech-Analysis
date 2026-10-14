import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.database import SessionLocal, init_db
from app.models.analysis import Analysis
from app.services.demo_service import (
    get_demo_samples_list,
    load_demo_sample,
    DEMO_SAMPLES_REGISTRY,
)

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()


def test_get_demo_samples_list():
    """Verify demo catalog returns all 4 contrastive showcase samples."""
    catalog = get_demo_samples_list()
    assert catalog.count == 4
    assert len(catalog.samples) == 4

    sample_ids = [s.sample_id for s in catalog.samples]
    assert "demo-keynote" in sample_ids
    assert "demo-sprinter" in sample_ids
    assert "demo-monotone" in sample_ids
    assert "demo-hesitant" in sample_ids

    # Verify Executive Keynote is Master Tier
    keynote = next(s for s in catalog.samples if s.sample_id == "demo-keynote")
    assert keynote.tier == "Master"
    assert keynote.grade == "A"
    assert "Dynamic Orator" in keynote.archetype

    # Verify Rapid Pitch is Sprinter
    sprinter = next(s for s in catalog.samples if s.sample_id == "demo-sprinter")
    assert "Sprinter" in sprinter.archetype
    assert len(sprinter.key_flaws) > 0


def test_load_demo_sample_keynote():
    """Verify loading demo-keynote seeds full multi-track analysis into DB."""
    db = SessionLocal()
    try:
        resp = load_demo_sample(db, "demo-keynote")
        assert resp.sample_id == "demo-keynote"
        assert resp.status == "ready"
        assert resp.analysis_id == DEMO_SAMPLES_REGISTRY["demo-keynote"]["analysis_id"]

        # Check DB record
        record = db.query(Analysis).filter(Analysis.id == resp.analysis_id).first()
        assert record is not None
        assert record.status == "completed"
        assert record.stage in ["scored", "completed"]
        assert record.analysis_audio_path is not None
        assert record.scores_json is not None

        # Parse scores
        scores = json.loads(record.scores_json)
        assert scores["summary"]["overall_score"] >= 90.0
        assert scores["summary"]["tier"] == "Master"
    finally:
        db.close()


def test_load_demo_sample_sprinter():
    """Verify loading demo-sprinter seeds flaw evidence and causal reasoning."""
    db = SessionLocal()
    try:
        resp = load_demo_sample(db, "demo-sprinter")
        assert resp.sample_id == "demo-sprinter"

        record = db.query(Analysis).filter(Analysis.id == resp.analysis_id).first()
        assert record is not None
        assert record.flaws_json is not None

        flaws = json.loads(record.flaws_json)
        assert flaws["summary"]["total_flaws"] >= 2
        assert any(f["flaw_type"] == "compressed_syllables" for f in flaws["flaws"])
    finally:
        db.close()


def test_load_demo_sample_unknown_raises_error():
    """Verify unknown sample ID raises ValueError."""
    db = SessionLocal()
    try:
        with pytest.raises(ValueError) as excinfo:
            load_demo_sample(db, "demo-nonexistent-xyz")
        assert "Unknown demo sample ID" in str(excinfo.value)
    finally:
        db.close()


def test_demo_api_endpoints():
    """Verify GET /api/demo/samples and POST /api/demo/load/{sample_id} API routes."""
    # GET catalog
    get_resp = client.get("/api/demo/samples")
    assert get_resp.status_code == 200
    catalog = get_resp.json()
    assert catalog["count"] == 4
    assert len(catalog["samples"]) == 4

    # POST load sample
    post_resp = client.post("/api/demo/load/demo-monotone")
    assert post_resp.status_code == 200
    data = post_resp.json()
    assert data["sample_id"] == "demo-monotone"
    assert "analysis_id" in data
    assert data["status"] == "ready"

    # POST unknown sample
    err_resp = client.post("/api/demo/load/demo-invalid-sample")
    assert err_resp.status_code == 404
