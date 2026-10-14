from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Any, Optional


class ScoringDimensionItem(BaseModel):
    name: str = Field(description="Human-readable dimension name")
    track: str = Field(description="Track classification: 'delivery' (HOW) or 'content' (WHAT)")
    raw_score: float = Field(ge=0.0, le=100.0, description="Raw dimension score (0-100)")
    weight_within_track: float = Field(description="Weight of dimension within its track (0.0 to 1.0)")
    overall_weight: float = Field(description="Weight of dimension in overall composite score")
    weighted_score: float = Field(description="Weighted contribution to composite score")
    grade: str = Field(description="Letter grade (A+, A, B+, B, C+, C, D, F)")
    status: str = Field(description="Performance label (e.g. Excellent, Proficient, Needs Focus)")
    feedback: str = Field(description="Concise diagnostic feedback for this specific dimension")


class FlawDeductionItem(BaseModel):
    severity: str = Field(description="Flaw severity: high, medium, or low")
    count: int = Field(description="Number of detected flaws in this severity tier")
    penalty_per_unit: float = Field(description="Score deduction per flaw occurrence")
    total_penalty: float = Field(description="Total points deducted for this severity tier")


class DeliveryRubricBreakdown(BaseModel):
    pace_score: float = Field(ge=0.0, le=100.0)
    pitch_score: float = Field(ge=0.0, le=100.0)
    rhythm_score: float = Field(ge=0.0, le=100.0)
    energy_score: float = Field(ge=0.0, le=100.0)
    timbre_score: float = Field(ge=0.0, le=100.0)
    raw_delivery_score: float = Field(ge=0.0, le=100.0, description="Weighted acoustic baseline before flaw deductions")
    flaw_penalties: List[FlawDeductionItem] = Field(default_factory=list)
    total_flaw_deduction: float = Field(description="Total score penalty subtracted due to temporal flaws")
    net_delivery_score: float = Field(ge=0.0, le=100.0, description="Final Delivery Rubric score (Track A)")
    grade: str
    tier: str
    status: str
    archetype: Optional[str] = None


class ContentRubricBreakdown(BaseModel):
    grammar_score: float = Field(ge=0.0, le=100.0)
    semantics_score: float = Field(ge=0.0, le=100.0)
    structure_score: float = Field(ge=0.0, le=100.0)
    net_content_score: float = Field(ge=0.0, le=100.0, description="Final Content Rubric score (Track B)")
    grade: str
    tier: str
    status: str
    strengths_count: int = 0
    issues_count: int = 0


class RubricTierLevel(BaseModel):
    tier_name: str = Field(description="Identifier: Master, Proficient, Competent, Developing, Novice")
    title: str = Field(description="Descriptive title: e.g. Master Orator")
    min_score: float
    max_score: float
    delivery_standard: str
    content_standard: str


class CompositeScoreSummary(BaseModel):
    overall_score: float = Field(ge=0.0, le=100.0, description="Combined composite score (0-100)")
    grade: str = Field(description="Overall letter grade")
    tier: str = Field(description="Overall speaker mastery tier")
    tier_title: str = Field(description="Descriptive title for the mastery tier")
    delivery_weight: float = Field(default=0.50, description="Proportion allocated to Track A Delivery")
    content_weight: float = Field(default=0.50, description="Proportion allocated to Track B Content")
    weighted_delivery_score: float = Field(description="Delivery score multiplied by its weight")
    weighted_content_score: float = Field(description="Content score multiplied by its weight")
    percentile_estimate: int = Field(ge=1, le=99, description="Estimated percentile relative to benchmark population")
    summary_headline: str = Field(description="Executive headline summarizing performance")
    key_takeaway: str = Field(description="High-priority coaching takeaway")


class ScoringResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: str
    status: str = "scored"
    summary: CompositeScoreSummary
    delivery: DeliveryRubricBreakdown
    content: ContentRubricBreakdown
    dimensions: List[ScoringDimensionItem] = Field(default_factory=list)
    rubric_tiers: List[RubricTierLevel] = Field(default_factory=list)
    message: str = "Rubric scoring and composite evaluation completed successfully."
