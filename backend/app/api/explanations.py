import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.analysis import Analysis
from app.schemas.explanations import ExplanationsResponse
from app.services.explanation_service import explain_and_store

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/analysis/{analysis_id}/explain",
    response_model=ExplanationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate causal explanations and diagnostic reasoning for speech delivery",
)
async def explain_endpoint(
    analysis_id: str,
    db: Session = Depends(get_db),
):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID '{analysis_id}' not found.",
        )

    if not analysis.analysis_audio_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Participant audio is missing. Upload media first.",
        )

    try:
        result = explain_and_store(db, analysis_id)
        return result
    except Exception as exc:
        logger.error(f"Causal explanation failed for {analysis_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Causal explanation failed: {str(exc)}",
        )


@router.get(
    "/analysis/{analysis_id}/explanations",
    response_model=ExplanationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve stored causal explanations and delivery diagnosis",
)
async def get_explanations_endpoint(
    analysis_id: str,
    db: Session = Depends(get_db),
):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID '{analysis_id}' not found.",
        )

    if not analysis.explanations_json:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Causal explanations have not yet been generated for this analysis.",
        )

    try:
        data = json.loads(analysis.explanations_json)
        return ExplanationsResponse(**data)
    except Exception as exc:
        logger.error(f"Failed to parse stored explanations_json: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse stored causal explanation data.",
        )
