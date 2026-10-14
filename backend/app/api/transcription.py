import os
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.analysis import Analysis
from app.schemas.transcription import TranscriptionResponse
from app.services.transcription_service import transcribe_audio

router = APIRouter(prefix="/analysis", tags=["transcription"])
logger = logging.getLogger(__name__)


@router.post("/{analysis_id}/transcribe", response_model=TranscriptionResponse)
def transcribe_speech(
    analysis_id: str,
    db: Session = Depends(get_db),
):
    """
    Run Faster-Whisper automatic speech recognition on the standardized audio.
    Generates raw transcript, Track A delivery reference transcript,
    and word/segment timestamps.
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID '{analysis_id}' not found.",
        )

    audio_path = analysis.analysis_audio_path
    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Standardized analysis audio is missing for this recording.",
        )

    try:
        # Update stage
        analysis.stage = "transcribing"
        db.commit()

        # Run transcription
        logger.info(f"[{analysis_id}] Beginning transcription of {audio_path}")
        result = transcribe_audio(audio_path)

        # Store results
        analysis.raw_transcript = result["text"]
        analysis.delivery_transcript = result["delivery_transcript"]
        analysis.segments_json = json.dumps(result["segments"])
        analysis.words_json = json.dumps(result["words"])
        analysis.duration = result["duration"]
        analysis.stage = "transcription_complete"
        analysis.status = "processing"

        db.commit()
        db.refresh(analysis)

        return TranscriptionResponse(
            analysis_id=analysis.id,
            status=analysis.status,
            language=result["language"],
            duration=result["duration"],
            raw_transcript=analysis.raw_transcript,
            delivery_transcript=analysis.delivery_transcript,
            segments=result["segments"],
            words=result["words"],
        )

    except Exception as e:
        logger.exception(f"[{analysis_id}] Transcription error: {e}")
        analysis.stage = "transcription_failed"
        analysis.error_message = str(e)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}",
        )


@router.get("/{analysis_id}/transcript", response_model=TranscriptionResponse)
def get_transcript(
    analysis_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve saved transcript and timestamps for an analysis run."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID '{analysis_id}' not found.",
        )

    if not analysis.raw_transcript:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcription has not been performed yet for this analysis.",
        )

    segments = json.loads(analysis.segments_json or "[]")
    words = json.loads(analysis.words_json or "[]")

    return TranscriptionResponse(
        analysis_id=analysis.id,
        status=analysis.status,
        language="en",
        duration=analysis.duration or 0.0,
        raw_transcript=analysis.raw_transcript or "",
        delivery_transcript=analysis.delivery_transcript or "",
        segments=segments,
        words=words,
    )
