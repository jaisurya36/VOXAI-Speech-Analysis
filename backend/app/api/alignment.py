import os
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.analysis import Analysis
from app.schemas.alignment import AlignmentResponse
from app.services.alignment_service import align_speech_tracks
from app.services.reference_service import generate_ideal_reference

router = APIRouter(prefix="/analysis", tags=["forced-alignment"])
logger = logging.getLogger(__name__)


@router.post("/{analysis_id}/align", response_model=AlignmentResponse)
def align_analysis_speech(
    analysis_id: str,
    db: Session = Depends(get_db),
):
    """
    Execute forced alignment between participant audio and the ideal delivery reference.
    Maps words and phrases to exact timestamps, computes coverage percentage,
    and establishes the temporal baseline for acoustic feature comparison.
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID '{analysis_id}' not found.",
        )

    # 1. Ensure participant words exist
    if not analysis.words_json:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Speech must be transcribed before running forced alignment.",
        )

    participant_words = json.loads(analysis.words_json)

    # 2. Ensure reference audio exists (auto-generate if missing)
    ref_audio_path = analysis.reference_audio_path
    if not ref_audio_path or not os.path.exists(ref_audio_path):
        delivery_script = analysis.delivery_transcript or analysis.raw_transcript
        if not delivery_script:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No delivery script available to generate reference audio.",
            )
        logger.info(f"[{analysis_id}] Auto-generating reference audio before alignment...")
        ref_meta = generate_ideal_reference(analysis_id, delivery_script)
        analysis.reference_audio_path = ref_meta["audio_path"]
        analysis.reference_script = ref_meta["reference_script"]
        ref_audio_path = ref_meta["audio_path"]
        db.commit()

    try:
        analysis.stage = "aligning"
        db.commit()

        # 3. Perform forced alignment
        alignment_data = align_speech_tracks(
            participant_words=participant_words,
            reference_audio_path=ref_audio_path,
            analysis_id=analysis_id,
        )

        analysis.alignment_json = json.dumps(alignment_data)
        analysis.stage = "aligned"
        db.commit()
        db.refresh(analysis)

        return AlignmentResponse(**alignment_data)

    except Exception as e:
        logger.exception(f"[{analysis_id}] Forced alignment error: {e}")
        analysis.stage = "alignment_failed"
        analysis.error_message = str(e)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forced alignment failed: {str(e)}",
        )


@router.get("/{analysis_id}/alignment", response_model=AlignmentResponse)
def get_alignment_results(
    analysis_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve saved forced alignment results."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID '{analysis_id}' not found.",
        )

    if not analysis.alignment_json:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alignment has not been performed yet for this analysis.",
        )

    data = json.loads(analysis.alignment_json)
    return AlignmentResponse(**data)
