from sqlalchemy import Column, String, Float, Integer, Text, DateTime
from sqlalchemy.sql import func
import uuid

from app.models.database import Base


class Analysis(Base):
    __tablename__ = 'analyses'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String(20), default='pending', nullable=False)
    stage = Column(String(100), nullable=True)
    original_filename = Column(String(255), nullable=False)
    input_type = Column(String(10), nullable=False)  # audio/video
    duration = Column(Float, nullable=True)
    sample_rate = Column(Integer, nullable=True)
    upload_path = Column(String(500), nullable=True)
    analysis_audio_path = Column(String(500), nullable=True)
    raw_transcript = Column(Text, nullable=True)
    delivery_transcript = Column(Text, nullable=True)
    corrected_transcript = Column(Text, nullable=True)
    segments_json = Column(Text, nullable=True)
    words_json = Column(Text, nullable=True)
    content_analysis_json = Column(Text, nullable=True)
    reference_audio_path = Column(String(500), nullable=True)
    reference_script = Column(Text, nullable=True)
    improved_audio_path = Column(String(500), nullable=True)
    alignment_json = Column(Text, nullable=True)
    features_json = Column(Text, nullable=True)
    comparison_json = Column(Text, nullable=True)
    flaws_json = Column(Text, nullable=True)
    explanations_json = Column(Text, nullable=True)
    scores_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
