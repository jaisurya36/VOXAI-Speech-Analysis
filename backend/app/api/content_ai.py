import os
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.analysis import Analysis
from app.schemas.content_ai import ContentEvaluationResponse
from app.services.content_ai_service import evaluate_content

router = APIRouter(prefix="/analysis", tags=["content-evaluation"])
logger = logging.getLogger(__name__)


@router.post("/{analysis_id}/evaluate-content", response_model=ContentEvaluationResponse)
def evaluate_speech_content(
    analysis_id: str,
    db: Session = Depends(get_db),
):
    """
    Run Gemini AI evaluation on WHAT the participant said.
    Evaluates grammar, semantics, vocabulary, structure, and produces Track B
    (corrected/improved transcript) without modifying Track A delivery reference.
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID '{analysis_id}' not found.",
        )

    transcript = analysis.delivery_transcript or analysis.raw_transcript
    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Speech has not been transcribed yet. Please transcribe audio before content evaluation.",
        )

    try:
        analysis.stage = "evaluating_content"
        db.commit()

        logger.info(f"[{analysis_id}] Evaluating content for transcript...")
        result = evaluate_content(transcript, analysis_id=analysis_id)

        # Persist Track B and evaluation JSON
        analysis.corrected_transcript = result.get("corrected_transcript", transcript)
        analysis.content_analysis_json = json.dumps(result)
        analysis.stage = "content_evaluated"

        db.commit()
        db.refresh(analysis)

        return ContentEvaluationResponse(**result)

    except Exception as e:
        logger.exception(f"[{analysis_id}] Content evaluation error: {e}")
        analysis.stage = "content_evaluation_failed"
        analysis.error_message = str(e)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Content evaluation failed: {str(e)}",
        )


@router.get("/{analysis_id}/content-evaluation", response_model=ContentEvaluationResponse)
def get_content_evaluation(
    analysis_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve saved content evaluation for an analysis."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID '{analysis_id}' not found.",
        )

    if not analysis.content_analysis_json:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content evaluation has not been performed yet for this analysis.",
        )

    data = json.loads(analysis.content_analysis_json)
    return ContentEvaluationResponse(**data)
