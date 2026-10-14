import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.analysis import Analysis
from app.schemas.reference import ReferenceGenerationResponse
from app.services.reference_service import (
    generate_ideal_reference,
    generate_improved_preview,
)

router = APIRouter(prefix="/analysis", tags=["reference-speech"])
logger = logging.getLogger(__name__)


@router.post("/{analysis_id}/generate-reference", response_model=ReferenceGenerationResponse)
def create_ideal_reference(
    analysis_id: str,
    db: Session = Depends(get_db),
):
    """
    Automatically generate an acoustic delivery reference from Track A delivery_transcript.
    Removes the requirement for participants to manually upload a reference speech.
    Also optionally generates Track B improved speech preview for participant learning.
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID '{analysis_id}' not found.",
        )

    delivery_script = analysis.delivery_transcript or analysis.raw_transcript
    if not delivery_script:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Speech must be transcribed before generating an ideal delivery reference.",
        )

    try:
        analysis.stage = "generating_reference"
        db.commit()

        # 1. Generate Track A Ideal Delivery Reference
        logger.info(f"[{analysis_id}] Generating ideal delivery reference speech...")
        ref_meta = generate_ideal_reference(analysis_id, delivery_script)

        analysis.reference_audio_path = ref_meta["audio_path"]
        analysis.reference_script = ref_meta["reference_script"]

        # 2. Optionally generate Track B Improved Speech Preview
        has_improved = False
        if analysis.corrected_transcript:
            logger.info(f"[{analysis_id}] Generating optional Track B improved speech preview...")
            improved_path = generate_improved_preview(analysis_id, analysis.corrected_transcript)
            if improved_path and os.path.exists(improved_path):
                analysis.improved_audio_path = improved_path
                has_improved = True

        analysis.stage = "reference_generated"
        db.commit()
        db.refresh(analysis)

        return ReferenceGenerationResponse(
            analysis_id=analysis.id,
            status=analysis.status,
            reference_script=ref_meta["reference_script"],
            duration=ref_meta["duration"],
            model_name=ref_meta["model_name"],
            voice_name=ref_meta["voice_name"],
            is_fallback=ref_meta["is_fallback"],
            has_improved_audio=has_improved,
            message="Ideal delivery reference generated and standardized successfully.",
        )

    except Exception as e:
        logger.exception(f"[{analysis_id}] Reference generation error: {e}")
        analysis.stage = "reference_generation_failed"
        analysis.error_message = str(e)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ideal reference generation failed: {str(e)}",
        )


@router.get("/{analysis_id}/reference-audio")
def get_reference_audio(
    analysis_id: str,
    db: Session = Depends(get_db),
):
    """Serve the generated standardized 16 kHz mono WAV ideal delivery reference."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis or not analysis.reference_audio_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ideal reference audio has not been generated for this analysis.",
        )
    if not os.path.exists(analysis.reference_audio_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ideal reference audio file is missing from storage.",
        )
    return FileResponse(
        analysis.reference_audio_path,
        media_type="audio/wav",
        filename=f"ideal_reference_{analysis_id}.wav",
    )


@router.get("/{analysis_id}/improved-audio")
def get_improved_audio(
    analysis_id: str,
    db: Session = Depends(get_db),
):
    """Serve the optional Track B improved speech preview audio."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis or not analysis.improved_audio_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Improved content preview audio has not been generated.",
        )
    if not os.path.exists(analysis.improved_audio_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Improved content audio file is missing from storage.",
        )
    return FileResponse(
        analysis.improved_audio_path,
        media_type="audio/wav",
        filename=f"improved_speech_{analysis_id}.wav",
    )
