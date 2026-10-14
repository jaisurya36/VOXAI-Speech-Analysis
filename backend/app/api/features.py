import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.analysis import Analysis
from app.schemas.features import FeaturesResponse
from app.services.feature_service import extract_and_store_features

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/analysis/{analysis_id}/extract-features",
    response_model=FeaturesResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract acoustic features for participant and Track A reference speech",
)
async def extract_features_endpoint(
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
            detail="Track A ideal delivery reference audio is missing. Generate reference first.",
        )

    try:
        result = extract_and_store_features(db, analysis_id)
        return result
    except Exception as exc:
        logger.error(f"Feature extraction failed for {analysis_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feature extraction failed: {str(exc)}",
        )


@router.get(
    "/analysis/{analysis_id}/features",
    response_model=FeaturesResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve extracted acoustic features",
)
async def get_features_endpoint(
    analysis_id: str,
    db: Session = Depends(get_db),
):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID '{analysis_id}' not found.",
        )

    if not analysis.features_json:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Acoustic features have not yet been extracted for this analysis.",
        )

    try:
        data = json.loads(analysis.features_json)
        return FeaturesResponse(**data)
    except Exception as exc:
        logger.error(f"Failed to parse stored features_json: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse stored acoustic feature data.",
        )
