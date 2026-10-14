from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional


class PitchFeatures(BaseModel):
    mean_f0: float = Field(description="Mean fundamental frequency in Hz for voiced segments")
    median_f0: float = Field(description="Median fundamental frequency in Hz for voiced segments")
    std_f0: float = Field(description="Standard deviation of F0 in Hz (pitch variation)")
    min_f0: float = Field(description="Minimum voiced F0 in Hz")
    max_f0: float = Field(description="Maximum voiced F0 in Hz")
    pitch_range_semitones: float = Field(description="Pitch dynamic range in musical semitones")
    voiced_fraction: float = Field(description="Ratio of voiced frames to total audio frames (0.0 to 1.0)")
    contour: List[float] = Field(default_factory=list, description="Downsampled pitch contour in Hz (100 points)")


class EnergyFeatures(BaseModel):
    mean_rms: float = Field(description="Mean root-mean-square energy")
    std_rms: float = Field(description="Standard deviation of RMS energy")
    max_rms: float = Field(description="Peak RMS energy")
    dynamic_range_db: float = Field(description="Estimated energy dynamic range in decibels")
    contour: List[float] = Field(default_factory=list, description="Downsampled RMS energy contour (100 points)")


class SpectralFeatures(BaseModel):
    mean_spectral_centroid: float = Field(description="Mean spectral centroid in Hz (brightness/sharpness)")
    mean_spectral_bandwidth: float = Field(description="Mean spectral spread/bandwidth in Hz")
    mean_spectral_rolloff: float = Field(description="Mean 85% roll-off frequency in Hz")
    mean_zero_crossing_rate: float = Field(description="Mean zero-crossing rate (noisiness/fricative density)")


class MFCCFeatures(BaseModel):
    mean_mfcc: List[float] = Field(default_factory=list, description="Mean 13-dimensional MFCC vector")
    std_mfcc: List[float] = Field(default_factory=list, description="Standard deviation 13-dimensional MFCC vector")


class RhythmFeatures(BaseModel):
    total_duration: float = Field(description="Total audio duration in seconds")
    speaking_duration: float = Field(description="Active speaking duration in seconds (excluding pauses)")
    pause_duration: float = Field(description="Total pause duration in seconds")
    pause_count: int = Field(description="Total number of detected silence pauses (>= 200ms)")
    mean_pause_duration: float = Field(description="Average duration of pauses in seconds")
    pause_to_speech_ratio: float = Field(description="Ratio of pause duration to speaking duration")
    words_per_minute: float = Field(description="Overall speech tempo in words per minute")
    articulation_rate: float = Field(description="Articulation speed (WPM excluding pause time)")


class WordAcousticFeature(BaseModel):
    word: str
    start: float
    end: float
    duration: float
    mean_f0: Optional[float] = None
    max_f0: Optional[float] = None
    mean_energy: float = 0.0


class TrackFeatures(BaseModel):
    pitch: PitchFeatures
    energy: EnergyFeatures
    spectral: SpectralFeatures
    mfcc: MFCCFeatures
    rhythm: RhythmFeatures
    word_features: List[WordAcousticFeature] = Field(default_factory=list)


class FeaturesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: str
    status: str
    participant_features: TrackFeatures
    reference_features: TrackFeatures
    time_axis: List[float] = Field(default_factory=list, description="Normalized time points [0.0 ... 1.0] for contour charts")
    message: str = "Acoustic feature extraction completed successfully."
