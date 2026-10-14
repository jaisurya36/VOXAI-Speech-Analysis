from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional


class DemoSampleSummary(BaseModel):
    sample_id: str = Field(description="Unique identifier for demo speech, e.g. demo-keynote")
    title: str = Field(description="Display title for the demo sample")
    archetype: str = Field(description="Speaker archetype classification")
    duration: float = Field(description="Duration in seconds")
    overall_score: float = Field(description="Composite score (0-100)")
    grade: str = Field(description="Academic letter grade")
    tier: str = Field(description="Speaker mastery tier")
    description: str = Field(description="Brief overview of the speech and acoustic characteristics")
    transcript_preview: str = Field(description="Preview excerpt of the spoken words")
    key_flaws: List[str] = Field(default_factory=list, description="Primary temporal flaws showcased")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")


class DemoListResponse(BaseModel):
    samples: List[DemoSampleSummary] = Field(default_factory=list)
    count: int = Field(description="Total number of showcase demo speeches")


class DemoLoadResponse(BaseModel):
    sample_id: str
    analysis_id: str
    status: str = "ready"
    title: str
    message: str = "Demo sample loaded successfully."
