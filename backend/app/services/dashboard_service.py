"""
dashboard_service.py — Assembles and unifies multi-track speech analytics data for visualization.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.schemas.dashboard import DashboardDataResponse
from app.services.scoring_service import score_and_store

logger = logging.getLogger(__name__)


def get_dashboard_data(
    db: Session,
    analysis_id: str,
    auto_complete: bool = True,
) -> DashboardDataResponse:
    """
    Assembles comprehensive multi-track acoustic, content, flaw, and rubric data
    for interactive dashboards and visualizations.
    If auto_complete is True and scoring has not yet run, automatically chains
    and generates the missing downstream analytics.
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise ValueError(f"Analysis with ID '{analysis_id}' not found.")

    # Auto-complete up to scoring if media audio exists and scores not yet generated
    if auto_complete and not analysis.scores_json and analysis.analysis_audio_path:
        try:
            logger.info(f"[{analysis_id}] Auto-completing pipeline up to scoring for dashboard view...")
            score_and_store(db, analysis_id)
            db.refresh(analysis)
        except Exception as exc:
            logger.warning(f"[{analysis_id}] Auto-completion partially completed or failed: {exc}")

    def safe_parse(json_str: Optional[str]) -> Optional[Dict[str, Any]]:
        if not json_str:
            return None
        try:
            return json.loads(json_str)
        except Exception as exc:
            logger.warning(f"Error parsing JSON for analysis {analysis_id}: {exc}")
            return None

    features_dict = safe_parse(analysis.features_json)
    comparison_dict = safe_parse(analysis.comparison_json)
    flaws_dict = safe_parse(analysis.flaws_json)
    explanations_dict = safe_parse(analysis.explanations_json)
    scores_dict = safe_parse(analysis.scores_json)

    has_audio = bool(analysis.analysis_audio_path and os.path.exists(analysis.analysis_audio_path))
    has_reference_audio = bool(analysis.reference_audio_path and os.path.exists(analysis.reference_audio_path))
    has_improved_audio = bool(analysis.improved_audio_path and os.path.exists(analysis.improved_audio_path))

    return DashboardDataResponse(
        analysis_id=analysis.id,
        status=analysis.status,
        stage=analysis.stage,
        original_filename=analysis.original_filename,
        input_type=analysis.input_type,
        duration=analysis.duration,
        sample_rate=analysis.sample_rate,
        created_at=analysis.created_at,
        raw_transcript=analysis.raw_transcript,
        delivery_transcript=analysis.delivery_transcript,
        corrected_transcript=analysis.corrected_transcript,
        features=features_dict,
        comparison=comparison_dict,
        flaws=flaws_dict,
        explanations=explanations_dict,
        scores=scores_dict,
        has_audio=has_audio,
        has_reference_audio=has_reference_audio,
        has_improved_audio=has_improved_audio,
        message="Dashboard data retrieved successfully.",
    )
