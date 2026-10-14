from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Any, Optional
from enum import Enum


class FlawSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FlawCategory(str, Enum):
    PACE = "pace"
    PAUSE = "pause"
    PITCH = "pitch"
    ENERGY = "energy"
    ARTICULATION = "articulation"


class TemporalFlawItem(BaseModel):
    id: str = Field(description="Unique identifier for the detected flaw")
    flaw_type: str = Field(description="Standardized flaw type code, e.g. monotone_passage, excessive_pause")
    category: str = Field(description="Dimension: pace, pause, pitch, energy, or articulation")
    severity: str = Field(description="Severity classification: low, medium, or high")
    start_time: float = Field(description="Start timestamp in seconds within audio")
    end_time: float = Field(description="End timestamp in seconds within audio")
    duration: float = Field(description="Duration in seconds of the affected interval")
    description: str = Field(description="Human-readable explanation of the flaw backed by mathematical evidence")
    affected_text: str = Field(default="", description="Words spoken during this temporal interval")
    metric_evidence: Dict[str, Any] = Field(
        default_factory=dict, description="Numerical values justifying the detection"
    )
    suggestion: str = Field(description="Actionable coaching advice to resolve the flaw")


class FlawsSummary(BaseModel):
    total_flaws: int = Field(description="Total number of temporal flaws identified")
    high_severity_count: int
    medium_severity_count: int
    low_severity_count: int
    flaw_density_per_minute: float = Field(description="Average flaw occurrences per minute of speech")
    flaws_by_category: Dict[str, int] = Field(default_factory=dict)
    primary_concern: str = Field(description="Most impactful flaw pattern detected")


class FlawsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: str
    status: str
    summary: FlawsSummary
    flaws: List[TemporalFlawItem] = Field(default_factory=list)
    message: str = "Temporal flaw detection completed successfully."
