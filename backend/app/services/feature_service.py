import os
import json
import wave
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import soundfile as sf
import librosa
from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.schemas.features import (
    PitchFeatures,
    EnergyFeatures,
    SpectralFeatures,
    MFCCFeatures,
    RhythmFeatures,
    WordAcousticFeature,
    TrackFeatures,
    FeaturesResponse,
)

logger = logging.getLogger(__name__)


def load_audio_array(file_path: str, target_sr: int = 16000) -> Tuple[np.ndarray, int]:
    """
    Robust audio loader that reads linear PCM WAV or general audio formats,
    converting to mono float32 normalized to [-1.0, 1.0].
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    # Method 1: Try soundfile
    try:
        data, sr = sf.read(file_path, dtype="float32")
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        if sr != target_sr:
            data = librosa.resample(data, orig_sr=sr, target_sr=target_sr)
            sr = target_sr
        return data, sr
    except Exception as sf_err:
        logger.warning(f"Soundfile failed on {file_path} ({sf_err}), attempting standard wave fallback.")

    # Method 2: Fallback to wave module for standard PCM WAV
    try:
        with wave.open(file_path, "rb") as wf:
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            frames = wf.readframes(n_frames)

        if sampwidth == 2:
            data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        elif sampwidth == 1:
            data = (np.frombuffer(frames, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
        elif sampwidth == 4:
            data = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            raise ValueError(f"Unsupported sample width: {sampwidth}")

        if channels > 1:
            data = data.reshape(-1, channels).mean(axis=1)

        if framerate != target_sr:
            data = librosa.resample(data, orig_sr=framerate, target_sr=target_sr)

        return data, target_sr
    except Exception as wave_err:
        raise RuntimeError(f"Failed to load audio file {file_path}: {wave_err}")


def extract_pitch_features(
    y: np.ndarray,
    sr: int = 16000,
    hop_length: int = 512,
    fmin: float = 65.0,
    fmax: float = 500.0,
) -> PitchFeatures:
    """
    Extracts fundamental frequency (F0) using the YIN algorithm, computing
    central tendency, pitch dispersion, semitone range, and contour.
    """
    if len(y) < hop_length * 2:
        return PitchFeatures(
            mean_f0=0.0,
            median_f0=0.0,
            std_f0=0.0,
            min_f0=0.0,
            max_f0=0.0,
            pitch_range_semitones=0.0,
            voiced_fraction=0.0,
            contour=[0.0] * 100,
        )

    # Compute RMS energy for silence/voicing gating
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    max_rms = float(np.max(rms)) if len(rms) > 0 else 0.0

    try:
        f0 = librosa.yin(y, fmin=fmin, fmax=fmax, sr=sr, hop_length=hop_length)
    except Exception as err:
        logger.warning(f"Pitch extraction failed: {err}")
        f0 = np.zeros_like(rms)

    # Voiced frame mask: energy must be above background noise and pitch within boundary bounds
    min_energy_thresh = max(0.005, 0.04 * max_rms)
    voiced_mask = (rms > min_energy_thresh) & (f0 > fmin + 5.0) & (f0 < fmax - 5.0)
    voiced_f0 = f0[voiced_mask]

    total_frames = len(f0)
    if len(voiced_f0) > 0 and total_frames > 0:
        mean_f0 = float(np.mean(voiced_f0))
        median_f0 = float(np.median(voiced_f0))
        std_f0 = float(np.std(voiced_f0))
        min_f0 = float(np.min(voiced_f0))
        max_f0 = float(np.max(voiced_f0))
        pitch_range_semitones = float(12.0 * np.log2((max_f0 + 1e-6) / (min_f0 + 1e-6)))
        voiced_fraction = float(len(voiced_f0) / total_frames)
    else:
        mean_f0 = median_f0 = std_f0 = min_f0 = max_f0 = pitch_range_semitones = voiced_fraction = 0.0

    # Downsample / interpolate contour to 100 normalized points
    f0_masked = np.where(voiced_mask, f0, 0.0)
    if len(f0_masked) > 1:
        x_orig = np.linspace(0.0, 1.0, len(f0_masked))
        x_target = np.linspace(0.0, 1.0, 100)
        contour = np.interp(x_target, x_orig, f0_masked)
        contour_list = [round(float(v), 1) for v in contour]
    else:
        contour_list = [round(mean_f0, 1)] * 100

    return PitchFeatures(
        mean_f0=round(mean_f0, 1),
        median_f0=round(median_f0, 1),
        std_f0=round(std_f0, 1),
        min_f0=round(min_f0, 1),
        max_f0=round(max_f0, 1),
        pitch_range_semitones=round(pitch_range_semitones, 2),
        voiced_fraction=round(voiced_fraction, 3),
        contour=contour_list,
    )


def extract_energy_features(
    y: np.ndarray,
    hop_length: int = 512,
) -> EnergyFeatures:
    """
    Extracts frame-level root-mean-square (RMS) energy, dynamic range (dB), and contour.
    """
    if len(y) < hop_length:
        return EnergyFeatures(
            mean_rms=0.0,
            std_rms=0.0,
            max_rms=0.0,
            dynamic_range_db=0.0,
            contour=[0.0] * 100,
        )

    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    mean_rms = float(np.mean(rms))
    std_rms = float(np.std(rms))
    max_rms = float(np.max(rms))
    median_rms = float(np.median(rms))

    dynamic_range_db = float(20.0 * np.log10((max_rms + 1e-6) / (median_rms + 1e-6)))

    # 100-point contour
    if len(rms) > 1:
        x_orig = np.linspace(0.0, 1.0, len(rms))
        x_target = np.linspace(0.0, 1.0, 100)
        contour = np.interp(x_target, x_orig, rms)
        contour_list = [round(float(v), 4) for v in contour]
    else:
        contour_list = [round(mean_rms, 4)] * 100

    return EnergyFeatures(
        mean_rms=round(mean_rms, 4),
        std_rms=round(std_rms, 4),
        max_rms=round(max_rms, 4),
        dynamic_range_db=round(dynamic_range_db, 1),
        contour=contour_list,
    )


def extract_spectral_features(
    y: np.ndarray,
    sr: int = 16000,
    hop_length: int = 512,
) -> SpectralFeatures:
    """
    Extracts timbre, vocal brightness (spectral centroid), frequency spread,
    high-frequency roll-off, and zero-crossing rate.
    """
    if len(y) < hop_length * 2:
        return SpectralFeatures(
            mean_spectral_centroid=0.0,
            mean_spectral_bandwidth=0.0,
            mean_spectral_rolloff=0.0,
            mean_zero_crossing_rate=0.0,
        )

    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr, hop_length=hop_length)[0]
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop_length, roll_percent=0.85)[0]
    zcr = librosa.feature.zero_crossing_rate(y=y, hop_length=hop_length)[0]

    return SpectralFeatures(
        mean_spectral_centroid=round(float(np.mean(centroid)), 1),
        mean_spectral_bandwidth=round(float(np.mean(bandwidth)), 1),
        mean_spectral_rolloff=round(float(np.mean(rolloff)), 1),
        mean_zero_crossing_rate=round(float(np.mean(zcr)), 4),
    )


def extract_mfcc_features(
    y: np.ndarray,
    sr: int = 16000,
    n_mfcc: int = 13,
    hop_length: int = 512,
) -> MFCCFeatures:
    """
    Extracts 13-dimensional Mel-Frequency Cepstral Coefficients (MFCCs).
    """
    if len(y) < hop_length * 2:
        return MFCCFeatures(
            mean_mfcc=[0.0] * n_mfcc,
            std_mfcc=[0.0] * n_mfcc,
        )

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc, hop_length=hop_length)
    mean_vec = [round(float(v), 3) for v in np.mean(mfcc, axis=1)]
    std_vec = [round(float(v), 3) for v in np.std(mfcc, axis=1)]

    return MFCCFeatures(
        mean_mfcc=mean_vec,
        std_mfcc=std_vec,
    )


def extract_rhythm_features(
    y: np.ndarray,
    sr: int = 16000,
    word_count: int = 0,
    hop_length: int = 512,
) -> RhythmFeatures:
    """
    Computes speech temporal dynamics, silence pauses (>= 200ms),
    words per minute (WPM), and articulation rate.
    """
    total_duration = float(len(y) / sr)
    if total_duration <= 0.05:
        return RhythmFeatures(
            total_duration=0.0,
            speaking_duration=0.0,
            pause_duration=0.0,
            pause_count=0,
            mean_pause_duration=0.0,
            pause_to_speech_ratio=0.0,
            words_per_minute=0.0,
            articulation_rate=0.0,
        )

    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    frame_dur = hop_length / float(sr)  # ~0.032s at sr=16000, hop=512

    # Silence threshold: 10% of mean RMS or absolute quiet
    pause_thresh = max(0.005, 0.12 * float(np.mean(rms)))
    is_silent = rms < pause_thresh

    # Group contiguous silent frames
    pauses: List[float] = []
    current_run = 0
    for silent in is_silent:
        if silent:
            current_run += 1
        else:
            if current_run > 0:
                dur = current_run * frame_dur
                if dur >= 0.20:  # Pauses >= 200 ms
                    pauses.append(dur)
                current_run = 0
    if current_run > 0:
        dur = current_run * frame_dur
        if dur >= 0.20:
            pauses.append(dur)

    pause_count = len(pauses)
    pause_duration = float(sum(pauses))
    speaking_duration = max(0.05, total_duration - pause_duration)
    mean_pause_duration = pause_duration / pause_count if pause_count > 0 else 0.0
    pause_to_speech_ratio = pause_duration / speaking_duration

    if word_count > 0:
        words_per_minute = (word_count / total_duration) * 60.0
        articulation_rate = (word_count / speaking_duration) * 60.0
    else:
        words_per_minute = 0.0
        articulation_rate = 0.0

    return RhythmFeatures(
        total_duration=round(total_duration, 2),
        speaking_duration=round(speaking_duration, 2),
        pause_duration=round(pause_duration, 2),
        pause_count=pause_count,
        mean_pause_duration=round(mean_pause_duration, 2),
        pause_to_speech_ratio=round(pause_to_speech_ratio, 2),
        words_per_minute=round(words_per_minute, 1),
        articulation_rate=round(articulation_rate, 1),
    )


def extract_word_acoustic_features(
    y: np.ndarray,
    sr: int,
    words: List[Dict[str, Any]],
) -> List[WordAcousticFeature]:
    """
    Calculates word-level acoustic features (pitch and energy) for timestamped word intervals.
    """
    results: List[WordAcousticFeature] = []
    total_samples = len(y)

    for item in words:
        word_text = str(item.get("word", "")).strip()
        start = float(item.get("start", 0.0))
        end = float(item.get("end", start + 0.1))
        duration = max(0.01, end - start)

        start_samp = max(0, min(total_samples - 1, int(start * sr)))
        end_samp = max(start_samp + 1, min(total_samples, int(end * sr)))
        y_slice = y[start_samp:end_samp]

        if len(y_slice) == 0:
            continue

        mean_energy = float(np.sqrt(np.mean(y_slice ** 2)))

        # Word pitch calculation (if slice has sufficient length)
        mean_f0: Optional[float] = None
        max_f0: Optional[float] = None
        if len(y_slice) >= 320:  # >= 20ms
            try:
                hop = min(256, max(64, len(y_slice) // 4))
                f0_slice = librosa.yin(y_slice, fmin=65.0, fmax=500.0, sr=sr, hop_length=hop)
                v_slice = f0_slice[(f0_slice > 70.0) & (f0_slice < 495.0)]
                if len(v_slice) > 0:
                    mean_f0 = round(float(np.mean(v_slice)), 1)
                    max_f0 = round(float(np.max(v_slice)), 1)
            except Exception:
                pass

        results.append(
            WordAcousticFeature(
                word=word_text,
                start=round(start, 2),
                end=round(end, 2),
                duration=round(duration, 2),
                mean_f0=mean_f0,
                max_f0=max_f0,
                mean_energy=round(mean_energy, 4),
            )
        )

    return results


def extract_track_features(
    audio_path: str,
    word_timestamps: Optional[List[Dict[str, Any]]] = None,
) -> TrackFeatures:
    """
    Full acoustic feature extraction pipeline for a single audio track.
    """
    y, sr = load_audio_array(audio_path, target_sr=16000)
    word_count = len(word_timestamps) if word_timestamps else 0

    pitch = extract_pitch_features(y, sr=sr)
    energy = extract_energy_features(y)
    spectral = extract_spectral_features(y, sr=sr)
    mfcc = extract_mfcc_features(y, sr=sr)
    rhythm = extract_rhythm_features(y, sr=sr, word_count=word_count)

    word_features: List[WordAcousticFeature] = []
    if word_timestamps:
        word_features = extract_word_acoustic_features(y, sr, word_timestamps)

    return TrackFeatures(
        pitch=pitch,
        energy=energy,
        spectral=spectral,
        mfcc=mfcc,
        rhythm=rhythm,
        word_features=word_features,
    )


def extract_and_store_features(db: Session, analysis_id: str) -> FeaturesResponse:
    """
    Orchestrates acoustic feature extraction for both participant audio and
    Track A reference audio, mapping timestamps via forced alignment.
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise ValueError(f"Analysis '{analysis_id}' not found.")

    if not analysis.analysis_audio_path or not os.path.exists(analysis.analysis_audio_path):
        raise ValueError("Standardized participant audio not found. Please upload media first.")

    if not analysis.reference_audio_path or not os.path.exists(analysis.reference_audio_path):
        raise ValueError("Ideal reference audio not found. Please run reference generation first.")

    # Prepare word timestamps for both tracks from alignment or ASR words
    participant_words: List[Dict[str, Any]] = []
    reference_words: List[Dict[str, Any]] = []

    if analysis.alignment_json:
        try:
            alignment_data = json.loads(analysis.alignment_json)
            aligned_list = alignment_data.get("aligned_words", [])
            for item in aligned_list:
                participant_words.append({
                    "word": item["word"],
                    "start": item["participant_start"],
                    "end": item["participant_end"],
                })
                reference_words.append({
                    "word": item["word"],
                    "start": item["reference_start"],
                    "end": item["reference_end"],
                })
        except Exception as err:
            logger.warning(f"Failed to parse alignment_json: {err}")

    # Fallback if alignment was not yet run or empty
    if not participant_words and analysis.words_json:
        try:
            participant_words = json.loads(analysis.words_json)
        except Exception:
            participant_words = []

    logger.info(f"Extracting acoustic features for participant: {analysis.analysis_audio_path}")
    part_features = extract_track_features(analysis.analysis_audio_path, participant_words)

    logger.info(f"Extracting acoustic features for reference: {analysis.reference_audio_path}")
    ref_features = extract_track_features(analysis.reference_audio_path, reference_words)

    time_axis = [round(i / 99.0, 3) for i in range(100)]

    response_data = FeaturesResponse(
        analysis_id=analysis.id,
        status="completed",
        participant_features=part_features,
        reference_features=ref_features,
        time_axis=time_axis,
        message="Acoustic feature extraction completed successfully.",
    )

    # Persist in DB
    analysis.features_json = json.dumps(response_data.model_dump(), indent=2)
    analysis.stage = "features_extracted"
    db.commit()

    return response_data
