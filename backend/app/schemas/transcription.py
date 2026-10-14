from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float
    probability: Optional[float] = None


class SegmentTimestamp(BaseModel):
    id: int
    start: float
    end: float
    text: str


class TranscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: str
    status: str
    language: str
    duration: float
    raw_transcript: str
    delivery_transcript: str
    segments: List[SegmentTimestamp]
    words: List[WordTimestamp]
