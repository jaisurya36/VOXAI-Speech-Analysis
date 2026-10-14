import os
import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.analysis import Analysis
from app.schemas.media import MediaUploadResponse, AnalysisStatusResponse
from app.services.media_service import process_upload, MediaError

router = APIRouter(prefix="/media", tags=["media"])
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload an audio or video file for speech analysis.
    Validates file, extracts/normalizes audio to 16 kHz mono WAV,
    and initializes an Analysis record.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    try:
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty (0 bytes).",
            )

        metadata = process_upload(
            file_bytes=content,
            original_filename=file.filename,
        )

        analysis = Analysis(
            id=metadata.analysis_id,
            status="pending",
            stage="media_ready",
            original_filename=metadata.original_filename,
            input_type=metadata.input_type,
            duration=metadata.duration,
            sample_rate=metadata.sample_rate,
            upload_path=metadata.upload_path,
            analysis_audio_path=metadata.analysis_audio_path,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        return MediaUploadResponse(
            analysis_id=metadata.analysis_id,
            original_filename=metadata.original_filename,
            input_type=metadata.input_type,
            duration=metadata.duration,
            sample_rate=metadata.sample_rate,
            status="ready",
            message="Media ready for analysis.",
        )

    except MediaError as e:
        logger.warning(f"Media validation/processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error during media upload")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Media processing failed: {str(e)}",
        )


@router.get("/{analysis_id}/status", response_model=AnalysisStatusResponse)
def get_media_status(
    analysis_id: str,
    db: Session = Depends(get_db),
):
    """Get current status and metadata of an analysis run."""
    record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID '{analysis_id}' not found.",
        )
    return record


@router.get("/{analysis_id}/audio")
def get_analysis_audio(
    analysis_id: str,
    db: Session = Depends(get_db),
):
    """Serve the normalized 16kHz mono WAV analysis audio."""
    record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not record or not record.analysis_audio_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis audio not found.",
        )
    if not os.path.exists(record.analysis_audio_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file missing from server storage.",
        )
    return FileResponse(
        record.analysis_audio_path,
        media_type="audio/wav",
        filename=f"analysis_{analysis_id}.wav",
    )


@router.get("/{analysis_id}/original")
def get_original_media(
    analysis_id: str,
    db: Session = Depends(get_db),
):
    """Serve the original uploaded file."""
    record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not record or not record.upload_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original media not found.",
        )
    if not os.path.exists(record.upload_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original file missing from server storage.",
        )
    media_type = "video/mp4" if record.input_type == "video" else "audio/mpeg"
    return FileResponse(
        record.upload_path,
        media_type=media_type,
        filename=record.original_filename,
    )
