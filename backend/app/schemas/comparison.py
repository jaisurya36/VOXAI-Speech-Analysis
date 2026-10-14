from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional


class DTWAlignmentPoint(BaseModel):
    participant_index: int
    reference_index: int
    normalized_participant_time: float
    normalized_reference_time: float


class DTWMetricResult(BaseModel):
    accumulated_cost: float = Field(description="Total DTW accumulated cost along optimal path")
    normalized_distance: float = Field(description="DTW distance normalized by warping path length")
    path_length: int = Field(description="Number of coordinate steps in optimal warping path")
    sample_path: List[DTWAlignmentPoint] = Field(
        default_factory=list, description="Downsampled warping path for visual alignment"
    )


class PaceComparison(BaseModel):
    participant_wpm: float = Field(description="Participant words per minute")
    reference_wpm: float = Field(description="Track A reference words per minute")
    delta_wpm: float = Field(description="Participant WPM minus Reference WPM")
    wpm_ratio: float = Field(description="Participant WPM divided by Reference WPM")
    participant_speaking_duration: float = Field(description="Participant active speaking duration in seconds")
    reference_speaking_duration: float = Field(description="Reference active speaking duration in seconds")
    duration_ratio: float = Field(description="Participant speaking duration / Reference speaking duration")
    status: str = Field(description="Classification: optimal_tempo, fast, slow, rushed, or lethargic")
    similarity_score: float = Field(ge=0.0, le=100.0, description="Pace similarity score (0-100)")


class PauseComparison(BaseModel):
    participant_pause_count: int
    reference_pause_count: int
    delta_pause_count: int = Field(description="Participant pauses minus Reference pauses")
    participant_pause_duration: float
    reference_pause_duration: float
    delta_pause_duration: float
    pause_duration_ratio: float
    participant_pause_to_speech_ratio: float
    reference_pause_to_speech_ratio: float
    delta_pause_to_speech: float
    status: str = Field(description="Classification: balanced_cadence, excessive_pauses, or insufficient_pauses")
    similarity_score: float = Field(ge=0.0, le=100.0, description="Rhythm/pause similarity score (0-100)")


class PitchComparison(BaseModel):
    participant_mean_f0: float = Field(description="Participant mean F0 in Hz")
    reference_mean_f0: float = Field(description="Reference mean F0 in Hz")
    delta_mean_f0: float = Field(description="Participant mean F0 minus Reference mean F0")
    participant_std_f0: float = Field(description="Participant F0 standard deviation in Hz")
    reference_std_f0: float = Field(description="Reference F0 standard deviation in Hz")
    pitch_variation_ratio: float = Field(description="Participant std F0 / Reference std F0")
    participant_range_semitones: float
    reference_range_semitones: float
    delta_semitones: float
    dtw: DTWMetricResult
    status: str = Field(description="Classification: expressive_prosody, monotone, or high_variation")
    similarity_score: float = Field(ge=0.0, le=100.0, description="Pitch and melody similarity score (0-100)")


class EnergyComparison(BaseModel):
    participant_mean_rms: float
    reference_mean_rms: float
    energy_ratio: float = Field(description="Participant RMS / Reference RMS")
    participant_dynamic_range_db: float
    reference_dynamic_range_db: float
    delta_dynamic_range_db: float
    dtw: DTWMetricResult
    status: str = Field(description="Classification: balanced_projection, underprojected, or overprojected")
    similarity_score: float = Field(ge=0.0, le=100.0, description="Energy and projection similarity score (0-100)")


class TimbreComparison(BaseModel):
    mfcc_cosine_distance: float = Field(description="Cosine distance between mean 13-dim MFCC vectors (0 to 1)")
    participant_spectral_centroid: float
    reference_spectral_centroid: float
    delta_spectral_centroid: float
    participant_articulation_rate: float
    reference_articulation_rate: float
    delta_articulation_rate: float
    status: str = Field(description="Classification: clear_articulation or timbral_deviation")
    similarity_score: float = Field(ge=0.0, le=100.0, description="Timbral and spectral similarity score (0-100)")


class WordComparisonItem(BaseModel):
    word: str
    participant_start: float
    participant_end: float
    participant_duration: float
    reference_start: float
    reference_end: float
    reference_duration: float
    duration_ratio: float
    duration_delta: float
    pitch_delta_hz: Optional[float] = None
    energy_ratio: Optional[float] = None
    tempo_flag: str = "normal"  # compressed, stretched, normal
    emphasis_flag: str = "normal"  # accented, reduced, normal


class ComparisonSummary(BaseModel):
    overall_similarity_score: float = Field(
        ge=0.0, le=100.0, description="Composite weighted acoustic similarity score (0-100)"
    )
    pace_score: float = Field(ge=0.0, le=100.0)
    pitch_score: float = Field(ge=0.0, le=100.0)
    rhythm_score: float = Field(ge=0.0, le=100.0)
    energy_score: float = Field(ge=0.0, le=100.0)
    timbre_score: float = Field(ge=0.0, le=100.0)
    primary_delivery_flaws: List[str] = Field(default_factory=list)


class ComparisonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: str
    status: str
    summary: ComparisonSummary
    pace: PaceComparison
    pause: PauseComparison
    pitch: PitchComparison
    energy: EnergyComparison
    timbre: TimbreComparison
    aligned_words_comparison: List[WordComparisonItem] = Field(default_factory=list)
    message: str = "Acoustic comparison completed successfully."
