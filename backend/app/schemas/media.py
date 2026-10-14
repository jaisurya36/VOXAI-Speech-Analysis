"""
Pydantic schemas for media upload and analysis responses.
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class MediaUploadResponse(BaseModel):
    """Returned after a successful file upload and processing."""
    analysis_id: str
    original_filename: str
    input_type: str           # "audio" | "video"
    duration: float
    sample_rate: int
    status: str               # "ready"
    message: str


class AnalysisStatusResponse(BaseModel):
    """General analysis record status."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    stage: Optional[str] = None
    original_filename: str
    input_type: str
    duration: Optional[float] = None
    sample_rate: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
