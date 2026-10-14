from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Any, Optional


class CausalFlawExplanation(BaseModel):
    flaw_id: str = Field(description="ID of the associated temporal flaw")
    flaw_type: str = Field(description="Standard flaw type code")
    start_time: float = Field(description="Flaw onset timestamp in seconds")
    end_time: float = Field(description="Flaw termination timestamp in seconds")
    affected_text: str = Field(default="", description="Words spoken during this interval")
    mathematical_cause: str = Field(
        description="The mathematical and signal-processing causal reason explaining why the flaw occurred"
    )
    physiological_factor: str = Field(
        description="Physiological or behavioral driver (e.g., breath exhaustion, vocal fold tension, cognitive buffering)"
    )
    perceptual_impact: str = Field(
        description="Effect on audience perception, retention, and clarity"
    )
    remedial_drill: str = Field(
        description="Concrete, actionable exercise or drill to eliminate the flaw"
    )
    confidence: float = Field(default=0.92, description="Causal attribution confidence (0.0 to 1.0)")


class DeliveryArchetype(BaseModel):
    name: str = Field(description="Archetype title, e.g. 'Dynamic Orator', 'Fast-Paced Sprinter', 'Monotone Presenter'")
    summary: str = Field(description="Diagnostic summary of this delivery persona")
    key_traits: List[str] = Field(default_factory=list, description="Core behavioral traits observed")


class CausalDiagnosis(BaseModel):
    archetype: DeliveryArchetype
    top_root_causes: List[str] = Field(
        description="Ranked underlying root causes driving detected speech flaws"
    )
    acoustic_strengths: List[str] = Field(
        description="Positive acoustic attributes identified in the participant recording"
    )
    action_roadmap: List[str] = Field(
        description="3-step actionable progression for vocal improvement"
    )


class ExplanationsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: str
    status: str
    diagnosis: CausalDiagnosis
    flaw_explanations: List[CausalFlawExplanation] = Field(default_factory=list)
    is_gemini_generated: bool = Field(
        default=False, description="True if generated via Gemini 2.0 Flash; False if generated via deterministic causal engine"
    )
    message: str = "Causal explanations generated successfully."
