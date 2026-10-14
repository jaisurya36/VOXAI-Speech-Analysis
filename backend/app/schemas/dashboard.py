from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, Any, List, Optional
from datetime import datetime


class DashboardDataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: str
    status: str
    stage: Optional[str] = None
    original_filename: str
    input_type: str
    duration: Optional[float] = None
    sample_rate: Optional[int] = None
    created_at: Optional[datetime] = None
    raw_transcript: Optional[str] = None
    delivery_transcript: Optional[str] = None
    corrected_transcript: Optional[str] = None

    features: Optional[Dict[str, Any]] = None
    comparison: Optional[Dict[str, Any]] = None
    flaws: Optional[Dict[str, Any]] = None
    explanations: Optional[Dict[str, Any]] = None
    scores: Optional[Dict[str, Any]] = None

    has_audio: bool = False
    has_reference_audio: bool = False
    has_improved_audio: bool = False
    message: str = "Dashboard data assembled successfully."
