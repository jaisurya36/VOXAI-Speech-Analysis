from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional


class AlignedWordItem(BaseModel):
    word: str
    participant_start: float
    participant_end: float
    reference_start: float
    reference_end: float
    confidence: float = 1.0


class AlignedPhraseItem(BaseModel):
    phrase_id: int
    text: str
    participant_start: float
    participant_end: float
    reference_start: float
    reference_end: float
    word_count: int


class AlignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: str
    status: str
    alignment_coverage: float = Field(ge=0.0, le=100.0)
    matched_word_count: int
    total_participant_words: int
    total_reference_words: int
    aligned_words: List[AlignedWordItem]
    aligned_phrases: List[AlignedPhraseItem]
    unmatched_participant_words: List[str] = Field(default_factory=list)
    unmatched_reference_words: List[str] = Field(default_factory=list)
    message: str = "Forced alignment completed successfully."
