from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional


class GrammarErrorItem(BaseModel):
    original: str
    corrected: str
    explanation: str


class GrammarEvaluation(BaseModel):
    score: int = Field(ge=0, le=100)
    errors: List[GrammarErrorItem] = Field(default_factory=list)


class SemanticIssueItem(BaseModel):
    text: str
    issue: str
    suggestion: str


class SemanticEvaluation(BaseModel):
    score: int = Field(ge=0, le=100)
    issues: List[SemanticIssueItem] = Field(default_factory=list)


class ContentEvaluation(BaseModel):
    score: int = Field(ge=0, le=100)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class ContentEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: str
    corrected_transcript: str
    grammar: GrammarEvaluation
    semantics: SemanticEvaluation
    content: ContentEvaluation
    is_fallback: bool = False
    status_message: str = "Evaluation successful"
