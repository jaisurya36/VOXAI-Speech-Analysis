import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.analysis import Analysis
from app.schemas.comparison import ComparisonResponse
from app.services.comparison_service import compare_and_store

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/analysis/{analysis_id}/compare",
    response_model=ComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Perform acoustic and temporal contrastive comparison with Track A reference",
)
async def compare_endpoint(
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

    if not analysis.reference_audio_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Track A reference audio is missing. Generate reference speech first.",
        )

    try:
        result = compare_and_store(db, analysis_id)
        return result
    except Exception as exc:
        logger.error(f"Comparison failed for {analysis_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Acoustic comparison failed: {str(exc)}",
        )


@router.get(
    "/analysis/{analysis_id}/comparison",
    response_model=ComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve stored acoustic and temporal comparison results",
)
async def get_comparison_endpoint(
    analysis_id: str,
    db: Session = Depends(get_db),
):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID '{analysis_id}' not found.",
        )

    if not analysis.comparison_json:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Acoustic comparison has not yet been performed for this analysis.",
        )

    try:
        data = json.loads(analysis.comparison_json)
        return ComparisonResponse(**data)
    except Exception as exc:
        logger.error(f"Failed to parse stored comparison_json: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse stored acoustic comparison data.",
        )
