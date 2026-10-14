import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.analysis import Analysis
from app.schemas.scoring import ScoringResponse
from app.services.scoring_service import score_and_store

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/analysis/{analysis_id}/score",
    response_model=ScoringResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute rubric scoring and composite evaluation across Delivery (HOW) and Content (WHAT)",
)
async def score_endpoint(
    analysis_id: str,
    delivery_weight: float = Query(default=0.50, ge=0.0, le=1.0, description="Weight allocated to Track A Delivery"),
    content_weight: float = Query(default=0.50, ge=0.0, le=1.0, description="Weight allocated to Track B Content"),
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
        result = score_and_store(
            db=db,
            analysis_id=analysis_id,
            delivery_weight=delivery_weight,
            content_weight=content_weight,
        )
        return result
    except Exception as exc:
        logger.error(f"Rubric evaluation failed for {analysis_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rubric evaluation failed: {str(exc)}",
        )


@router.get(
    "/analysis/{analysis_id}/score",
    response_model=ScoringResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve stored rubric scores and composite evaluation",
)
async def get_score_endpoint(
    analysis_id: str,
    db: Session = Depends(get_db),
):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID '{analysis_id}' not found.",
        )

    if not analysis.scores_json:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rubric evaluation has not yet been computed for this analysis.",
        )

    try:
        data = json.loads(analysis.scores_json)
        return ScoringResponse(**data)
    except Exception as exc:
        logger.error(f"Failed to parse stored scores_json: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse stored rubric score data.",
        )
