"""
pipeline.py — End-to-End Orchestration Endpoints.

Provides 1-click execution for the full 10-stage contrastive speech analytics pipeline,
direct upload-and-process, and real-time stage progress polling.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.analysis import Analysis
from app.schemas.pipeline import (
    PipelineProgressResponse,
    ProcessAllRequest,
    ProcessAllResponse,
)
from app.services.pipeline_service import run_pipeline, get_pipeline_progress
from app.services.media_service import process_upload, MediaError

router = APIRouter(prefix="/analysis", tags=["orchestration"])
logger = logging.getLogger(__name__)


@router.post("/{analysis_id}/process-all", response_model=ProcessAllResponse)
def process_entire_pipeline(
    analysis_id: str,
    req: ProcessAllRequest = ProcessAllRequest(),
    db: Session = Depends(get_db),
):
    """
    Executes the entire speech analytics pipeline from its current state to completion:
    standardization -> ASR -> Gemini content -> reference TTS -> forced alignment ->
    acoustic features -> DTW comparison -> temporal flaws -> causal explanations -> rubric scoring.
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID '{analysis_id}' not found.",
        )

    try:
        response = run_pipeline(
            analysis_id=analysis_id,
            db=db,
            delivery_weight=req.delivery_weight,
            content_weight=req.content_weight,
        )
        return response
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        logger.exception(f"[{analysis_id}] Pipeline execution failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline processing failed: {str(exc)}",
        )


@router.post("/upload-and-process", response_model=ProcessAllResponse, status_code=status.HTTP_201_CREATED)
async def upload_and_process_media(
    file: UploadFile = File(...),
    delivery_weight: float = Form(0.50),
    content_weight: float = Form(0.50),
    db: Session = Depends(get_db),
):
    """
    1-Click All-in-One Entry Point:
    Uploads audio/video, converts to 16 kHz WAV, and executes all 10 analysis stages
    sequentially, returning the complete final scorecard and dashboard route.
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

        # Run complete pipeline
        response = run_pipeline(
            analysis_id=analysis.id,
            db=db,
            delivery_weight=delivery_weight,
            content_weight=content_weight,
        )
        return response

    except MediaError as med_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(med_err),
        )
    except Exception as exc:
        logger.exception(f"Upload and process failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload and process failed: {str(exc)}",
        )


@router.get("/{analysis_id}/progress", response_model=PipelineProgressResponse)
def get_analysis_progress(
    analysis_id: str,
    db: Session = Depends(get_db),
):
    """
    Returns real-time progression status for all 10 stages of the pipeline.
    Suitable for frontend polling to render live step indicators and progress bars.
    """
    try:
        return get_pipeline_progress(analysis_id, db)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err),
        )
    except Exception as exc:
        logger.exception(f"[{analysis_id}] Progress check failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check progress: {str(exc)}",
        )
