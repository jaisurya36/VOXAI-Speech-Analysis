from pydantic import BaseModel, ConfigDict
from typing import Optional


class ReferenceGenerationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: str
    status: str
    reference_script: str
    duration: float
    model_name: str
    voice_name: str
    is_fallback: bool = False
    has_improved_audio: bool = False
    message: str = "Ideal delivery reference generated successfully."
