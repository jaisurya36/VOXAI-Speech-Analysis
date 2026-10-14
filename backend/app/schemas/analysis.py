from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from enum import Enum


class AnalysisStatus(str, Enum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'


class HealthResponse(BaseModel):
    status: str
    application: str
    version: str


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: AnalysisStatus
    stage: Optional[str] = None
    original_filename: str
    input_type: str
    duration: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
