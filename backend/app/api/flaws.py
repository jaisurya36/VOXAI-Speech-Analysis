import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.analysis import Analysis
from app.schemas.flaws import FlawsResponse
from app.services.flaw_detection_service import detect_and_store_flaws

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/analysis/{analysis_id}/detect-flaws",
    response_model=FlawsResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect temporal speech flaws grounded against Track A reference",
)
async def detect_flaws_endpoint(
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
        result = detect_and_store_flaws(db, analysis_id)
        return result
    except Exception as exc:
        logger.error(f"Flaw detection failed for {analysis_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Temporal flaw detection failed: {str(exc)}",
        )


@router.get(
    "/analysis/{analysis_id}/flaws",
    response_model=FlawsResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve detected temporal speech flaws",
)
async def get_flaws_endpoint(
    analysis_id: str,
    db: Session = Depends(get_db),
):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID '{analysis_id}' not found.",
        )

    if not analysis.flaws_json:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Temporal flaws have not yet been evaluated for this analysis.",
        )

    try:
        data = json.loads(analysis.flaws_json)
        return FlawsResponse(**data)
    except Exception as exc:
        logger.error(f"Failed to parse stored flaws_json: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse stored temporal flaw data.",
        )
