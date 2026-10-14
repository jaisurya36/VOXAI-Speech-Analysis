from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class PipelineStageInfo(BaseModel):
    stage_id: str
    name: str
    status: str  # "pending", "running", "completed", "failed", "skipped"
    description: str
    detail: Optional[str] = None


class PipelineProgressResponse(BaseModel):
    analysis_id: str
    status: str  # "pending", "processing", "completed", "failed"
    current_stage: str
    current_step: int
    total_steps: int = 10
    progress_percent: int
    stages: List[PipelineStageInfo]
    error_message: Optional[str] = None


class ProcessAllRequest(BaseModel):
    delivery_weight: float = Field(default=0.50, ge=0.0, le=1.0)
    content_weight: float = Field(default=0.50, ge=0.0, le=1.0)


class ProcessAllResponse(BaseModel):
    analysis_id: str
    status: str  # "completed" | "failed"
    original_filename: str
    duration: Optional[float] = None
    total_words: int
    total_flaws: int
    overall_score: Optional[float] = None
    letter_grade: Optional[str] = None
    tier: Optional[str] = None
    tier_title: Optional[str] = None
    archetype: Optional[str] = None
    stages_completed: int
    total_stages: int = 10
    results_url: str
    message: str
