"""
comparison_service.py — Contrastive Acoustic and Temporal Comparison Engine.

Performs rigorous mathematical comparison between Participant Speech and Track A
Ideal Delivery Reference:
1. Dynamic Time Warping (DTW) on pitch (F0) and energy (RMS) contours.
2. Cosine distance on 13-dimensional MFCC vectors.
3. Contrastive statistical deviations:
   - Pace / WPM delta and ratio
   - Pause counts, pause durations, and pause-to-speech ratio deltas
   - Pitch variation (std dev ratio, semitone range delta, mean F0 delta)
   - Dynamic range and vocal projection energy ratio
   - Spectral centroid & articulation rate deltas
4. Word-by-word contrastive temporal mapping:
   - Duration ratios (stretched vs compressed words)
   - Word-level pitch and energy deviations
5. Mathematically bounded similarity indices (0 - 100%) for each vocal dimension.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import librosa
from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.schemas.comparison import (
    DTWAlignmentPoint,
    DTWMetricResult,
    PaceComparison,
    PauseComparison,
    PitchComparison,
    EnergyComparison,
    TimbreComparison,
    WordComparisonItem,
    ComparisonSummary,
    ComparisonResponse,
)
from app.services.feature_service import extract_and_store_features

logger = logging.getLogger(__name__)


def compute_dtw_1d(
    series_a: List[float],
    series_b: List[float],
    sample_points: int = 16,
) -> DTWMetricResult:
    """
    Compute Dynamic Time Warping distance between two 1D series (e.g. 100-point contours).
    Uses librosa.sequence.dtw and extracts cost, normalized distance, and downsampled warping path.
    """
    arr_a = np.nan_to_num(np.array(series_a, dtype=np.float32), nan=0.0)
    arr_b = np.nan_to_num(np.array(series_b, dtype=np.float32), nan=0.0)

    # Edge cases: empty or single-point arrays
    if len(arr_a) < 2 or len(arr_b) < 2:
        return DTWMetricResult(
            accumulated_cost=0.0,
            normalized_distance=0.0,
            path_length=max(len(arr_a), len(arr_b)),
            sample_path=[],
        )

    try:
        # librosa.sequence.dtw expects 1D arrays or 2D (d, N) matrices
        D, wp = librosa.sequence.dtw(X=arr_a, Y=arr_b, metric="euclidean")
        acc_cost = float(D[-1, -1])
        path_len = len(wp)
        norm_dist = float(acc_cost / max(path_len, 1))

        # Downsample warping path for UI rendering
        # wp is array of shape (path_len, 2) in reverse order (from end to start)
        wp_forward = wp[::-1]
        step = max(1, len(wp_forward) // sample_points)
        sampled_points: List[DTWAlignmentPoint] = []

        for idx in range(0, len(wp_forward), step):
            i_idx, j_idx = int(wp_forward[idx][0]), int(wp_forward[idx][1])
            sampled_points.append(
                DTWAlignmentPoint(
                    participant_index=i_idx,
                    reference_index=j_idx,
                    normalized_participant_time=round(float(i_idx / max(len(arr_a) - 1, 1)), 3),
                    normalized_reference_time=round(float(j_idx / max(len(arr_b) - 1, 1)), 3),
                )
            )

        # Ensure final point is included
        last_i, last_j = int(wp_forward[-1][0]), int(wp_forward[-1][1])
        if not sampled_points or (sampled_points[-1].participant_index != last_i):
            sampled_points.append(
                DTWAlignmentPoint(
                    participant_index=last_i,
                    reference_index=last_j,
                    normalized_participant_time=1.0,
                    normalized_reference_time=1.0,
                )
            )

        return DTWMetricResult(
            accumulated_cost=round(acc_cost, 3),
            normalized_distance=round(norm_dist, 4),
            path_length=path_len,
            sample_path=sampled_points,
        )
    except Exception as exc:
        logger.warning(f"DTW computation encountered error: {exc}. Using fallback Euclidean distance.")
        diff = np.abs(arr_a[: min(len(arr_a), len(arr_b))] - arr_b[: min(len(arr_a), len(arr_b))])
        cost = float(np.sum(diff))
        return DTWMetricResult(
            accumulated_cost=round(cost, 3),
            normalized_distance=round(cost / max(len(diff), 1), 4),
            path_length=len(diff),
            sample_path=[],
        )


def compute_mfcc_cosine_distance(mfcc_a: List[float], mfcc_b: List[float]) -> float:
    """Calculate cosine distance (1.0 - cosine_similarity) between two 13-dim MFCC vectors."""
    va = np.array(mfcc_a, dtype=np.float32)
    vb = np.array(mfcc_b, dtype=np.float32)

    norm_a = float(np.linalg.norm(va))
    norm_b = float(np.linalg.norm(vb))

    if norm_a < 1e-6 or norm_b < 1e-6:
        return 0.0

    cosine_sim = float(np.dot(va, vb) / (norm_a * norm_b))
    cosine_dist = float(np.clip(1.0 - cosine_sim, 0.0, 2.0))
    return round(cosine_dist, 4)


def build_word_comparison(
    aligned_words: List[Dict[str, Any]],
    p_word_features: List[Dict[str, Any]],
    r_word_features: List[Dict[str, Any]],
) -> List[WordComparisonItem]:
    """
    Correlates word-level timings and acoustic features between participant and reference tracks.
    """
    items: List[WordComparisonItem] = []

    # Map word features by approximate start timestamp and word text for quick lookup
    p_feat_map = {f"{w.get('word', '').lower().strip()}_{round(w.get('start', 0.0), 1)}": w for w in p_word_features}
    r_feat_map = {f"{w.get('word', '').lower().strip()}_{round(w.get('start', 0.0), 1)}": w for w in r_word_features}

    for idx, aw in enumerate(aligned_words):
        word_text = aw.get("word", "")
        clean_text = word_text.lower().strip()

        p_start = float(aw.get("participant_start", 0.0))
        p_end = float(aw.get("participant_end", p_start + 0.1))
        p_dur = round(max(0.05, p_end - p_start), 3)

        r_start = float(aw.get("reference_start", 0.0))
        r_end = float(aw.get("reference_end", r_start + 0.1))
        r_dur = round(max(0.05, r_end - r_start), 3)

        dur_ratio = round(p_dur / max(r_dur, 0.05), 2)
        dur_delta = round(p_dur - r_dur, 3)

        # Lookup acoustic properties if available
        p_feat = p_feat_map.get(f"{clean_text}_{round(p_start, 1)}") or (
            p_word_features[idx] if idx < len(p_word_features) else None
        )
        r_feat = r_feat_map.get(f"{clean_text}_{round(r_start, 1)}") or (
            r_word_features[idx] if idx < len(r_word_features) else None
        )

        pitch_delta: Optional[float] = None
        if p_feat and r_feat and p_feat.get("mean_f0") and r_feat.get("mean_f0"):
            pitch_delta = round(float(p_feat["mean_f0"]) - float(r_feat["mean_f0"]), 1)

        energy_ratio: Optional[float] = None
        if p_feat and r_feat and p_feat.get("mean_energy") and r_feat.get("mean_energy"):
            r_e = float(r_feat["mean_energy"])
            energy_ratio = round(float(p_feat["mean_energy"]) / max(r_e, 1e-5), 2)

        # Tempo classification
        if dur_ratio > 1.45:
            tempo_flag = "stretched"
        elif dur_ratio < 0.70:
            tempo_flag = "compressed"
        else:
            tempo_flag = "normal"

        # Emphasis classification
        if energy_ratio and energy_ratio > 1.35 and (pitch_delta is None or pitch_delta > 0):
            emphasis_flag = "accented"
        elif energy_ratio and energy_ratio < 0.65:
            emphasis_flag = "reduced"
        else:
            emphasis_flag = "normal"

        items.append(
            WordComparisonItem(
                word=word_text,
                participant_start=p_start,
                participant_end=p_end,
                participant_duration=p_dur,
                reference_start=r_start,
                reference_end=r_end,
                reference_duration=r_dur,
                duration_ratio=dur_ratio,
                duration_delta=dur_delta,
                pitch_delta_hz=pitch_delta,
                energy_ratio=energy_ratio,
                tempo_flag=tempo_flag,
                emphasis_flag=emphasis_flag,
            )
        )

    return items


def compare_tracks(
    participant_data: Dict[str, Any],
    reference_data: Dict[str, Any],
    alignment_data: Optional[Dict[str, Any]] = None,
    analysis_id: str = "unknown",
) -> ComparisonResponse:
    """
    Main contrastive computation engine between participant and reference feature sets.
    """
    p_pitch = participant_data.get("pitch", {})
    r_pitch = reference_data.get("pitch", {})

    p_energy = participant_data.get("energy", {})
    r_energy = reference_data.get("energy", {})

    p_spectral = participant_data.get("spectral", {})
    r_spectral = reference_data.get("spectral", {})

    p_mfcc = participant_data.get("mfcc", {})
    r_mfcc = reference_data.get("mfcc", {})

    p_rhythm = participant_data.get("rhythm", {})
    r_rhythm = reference_data.get("rhythm", {})

    p_words = participant_data.get("word_features", [])
    r_words = reference_data.get("word_features", [])

    flaws_detected: List[str] = []

    # -------------------------------------------------------------
    # 1. Pace / Tempo Comparison
    # -------------------------------------------------------------
    p_wpm = float(p_rhythm.get("words_per_minute", 130.0))
    r_wpm = float(r_rhythm.get("words_per_minute", 135.0))
    delta_wpm = round(p_wpm - r_wpm, 1)
    wpm_ratio = round(p_wpm / max(r_wpm, 1e-3), 2)

    p_spk_dur = float(p_rhythm.get("speaking_duration", 0.0))
    r_spk_dur = float(r_rhythm.get("speaking_duration", 0.0))
    dur_ratio = round(p_spk_dur / max(r_spk_dur, 1e-3), 2)

    if delta_wpm > 35.0:
        pace_status = "rushed"
        flaws_detected.append(f"Speech pace is rushed (+{delta_wpm} WPM faster than ideal baseline)")
    elif delta_wpm > 15.0:
        pace_status = "fast"
        flaws_detected.append(f"Speech pace is moderately brisk (+{delta_wpm} WPM above ideal)")
    elif delta_wpm < -35.0:
        pace_status = "lethargic"
        flaws_detected.append(f"Speech pace is excessively slow ({delta_wpm} WPM below ideal baseline)")
    elif delta_wpm < -15.0:
        pace_status = "slow"
        flaws_detected.append(f"Speech pace is hesitant ({delta_wpm} WPM below ideal)")
    else:
        pace_status = "optimal_tempo"

    # Deterministic Pace Score (0-100)
    pace_score = round(max(0.0, min(100.0, 100.0 - abs(delta_wpm) * 1.25)), 1)

    pace_comp = PaceComparison(
        participant_wpm=round(p_wpm, 1),
        reference_wpm=round(r_wpm, 1),
        delta_wpm=delta_wpm,
        wpm_ratio=wpm_ratio,
        participant_speaking_duration=round(p_spk_dur, 2),
        reference_speaking_duration=round(r_spk_dur, 2),
        duration_ratio=dur_ratio,
        status=pace_status,
        similarity_score=pace_score,
    )

    # -------------------------------------------------------------
    # 2. Pause & Cadence Comparison
    # -------------------------------------------------------------
    p_pauses = int(p_rhythm.get("pause_count", 0))
    r_pauses = int(r_rhythm.get("pause_count", 0))
    delta_pauses = p_pauses - r_pauses

    p_pause_dur = float(p_rhythm.get("pause_duration", 0.0))
    r_pause_dur = float(r_rhythm.get("pause_duration", 0.0))
    delta_pause_dur = round(p_pause_dur - r_pause_dur, 2)
    pause_dur_ratio = round(p_pause_dur / max(r_pause_dur, 0.001), 2)

    p_pause_ratio = float(p_rhythm.get("pause_to_speech_ratio", 0.0))
    r_pause_ratio = float(r_rhythm.get("pause_to_speech_ratio", 0.0))
    delta_pause_to_speech = round(p_pause_ratio - r_pause_ratio, 3)

    if delta_pauses >= 3 or pause_dur_ratio >= 1.6:
        pause_status = "excessive_pauses"
        flaws_detected.append(f"Excessive silence pauses ({p_pauses} vs {r_pauses} in ideal delivery)")
    elif delta_pauses <= -3 or pause_dur_ratio <= 0.4:
        pause_status = "insufficient_pauses"
        flaws_detected.append("Insufficient breathing pauses; delivery runs together without cadence")
    else:
        pause_status = "balanced_cadence"

    # Deterministic Rhythm Score (0-100)
    rhythm_score = round(
        max(
            0.0,
            min(
                100.0,
                100.0 - abs(delta_pauses) * 5.0 - min(40.0, abs(delta_pause_to_speech) * 100.0),
            ),
        ),
        1,
    )

    pause_comp = PauseComparison(
        participant_pause_count=p_pauses,
        reference_pause_count=r_pauses,
        delta_pause_count=delta_pauses,
        participant_pause_duration=round(p_pause_dur, 2),
        reference_pause_duration=round(r_pause_dur, 2),
        delta_pause_duration=delta_pause_dur,
        pause_duration_ratio=pause_dur_ratio,
        participant_pause_to_speech_ratio=round(p_pause_ratio, 3),
        reference_pause_to_speech_ratio=round(r_pause_ratio, 3),
        delta_pause_to_speech=delta_pause_to_speech,
        status=pause_status,
        similarity_score=rhythm_score,
    )

    # -------------------------------------------------------------
    # 3. Pitch & Melody DTW Comparison
    # -------------------------------------------------------------
    p_pitch_contour = p_pitch.get("contour", [])
    r_pitch_contour = r_pitch.get("contour", [])
    pitch_dtw = compute_dtw_1d(p_pitch_contour, r_pitch_contour, sample_points=16)

    p_mean_f0 = float(p_pitch.get("mean_f0", 0.0))
    r_mean_f0 = float(r_pitch.get("mean_f0", 0.0))
    delta_mean_f0 = round(p_mean_f0 - r_mean_f0, 1)

    p_std_f0 = float(p_pitch.get("std_f0", 0.0))
    r_std_f0 = float(r_pitch.get("std_f0", 0.0))
    pitch_var_ratio = round(p_std_f0 / max(r_std_f0, 0.001), 2)

    p_semitones = float(p_pitch.get("pitch_range_semitones", 0.0))
    r_semitones = float(r_pitch.get("pitch_range_semitones", 0.0))
    delta_semitones = round(p_semitones - r_semitones, 1)

    if pitch_var_ratio < 0.60 or delta_semitones < -4.0:
        pitch_status = "monotone"
        flaws_detected.append(
            f"Monotone inflection detected (pitch dynamic range {delta_semitones} semitones below baseline)"
        )
    elif pitch_var_ratio > 1.65 or delta_semitones > 6.0:
        pitch_status = "high_variation"
        flaws_detected.append("Erratic pitch variation; vocal intonation fluctuates unpredictably")
    else:
        pitch_status = "expressive_prosody"

    # Deterministic Pitch Score (0-100)
    # Penalize based on normalized DTW distance and pitch variation deviation
    pitch_dtw_penalty = min(40.0, pitch_dtw.normalized_distance * 0.5)
    pitch_var_penalty = min(35.0, abs(pitch_var_ratio - 1.0) * 35.0)
    pitch_score = round(max(0.0, min(100.0, 100.0 - pitch_dtw_penalty - pitch_var_penalty)), 1)

    pitch_comp = PitchComparison(
        participant_mean_f0=round(p_mean_f0, 1),
        reference_mean_f0=round(r_mean_f0, 1),
        delta_mean_f0=delta_mean_f0,
        participant_std_f0=round(p_std_f0, 1),
        reference_std_f0=round(r_std_f0, 1),
        pitch_variation_ratio=pitch_var_ratio,
        participant_range_semitones=round(p_semitones, 1),
        reference_range_semitones=round(r_semitones, 1),
        delta_semitones=delta_semitones,
        dtw=pitch_dtw,
        status=pitch_status,
        similarity_score=pitch_score,
    )

    # -------------------------------------------------------------
    # 4. Energy & Dynamics DTW Comparison
    # -------------------------------------------------------------
    p_energy_contour = p_energy.get("contour", [])
    r_energy_contour = r_energy.get("contour", [])
    energy_dtw = compute_dtw_1d(p_energy_contour, r_energy_contour, sample_points=16)

    p_mean_rms = float(p_energy.get("mean_rms", 0.0))
    r_mean_rms = float(r_energy.get("mean_rms", 0.0))
    energy_ratio = round(p_mean_rms / max(r_mean_rms, 1e-6), 2)

    p_dyn_db = float(p_energy.get("dynamic_range_db", 0.0))
    r_dyn_db = float(r_energy.get("dynamic_range_db", 0.0))
    delta_dyn_db = round(p_dyn_db - r_dyn_db, 1)

    if energy_ratio < 0.65:
        energy_status = "underprojected"
        flaws_detected.append(f"Vocal energy is underprojected ({round((1.0 - energy_ratio) * 100)}% quieter than ideal)")
    elif energy_ratio > 1.65:
        energy_status = "overprojected"
        flaws_detected.append("Vocal energy is strained / overprojected, risking vocal fatigue")
    else:
        energy_status = "balanced_projection"

    # Deterministic Energy Score (0-100)
    energy_dtw_penalty = min(40.0, energy_dtw.normalized_distance * 100.0)
    energy_ratio_penalty = min(35.0, abs(energy_ratio - 1.0) * 30.0)
    energy_score = round(max(0.0, min(100.0, 100.0 - energy_dtw_penalty - energy_ratio_penalty)), 1)

    energy_comp = EnergyComparison(
        participant_mean_rms=round(p_mean_rms, 4),
        reference_mean_rms=round(r_mean_rms, 4),
        energy_ratio=energy_ratio,
        participant_dynamic_range_db=round(p_dyn_db, 1),
        reference_dynamic_range_db=round(r_dyn_db, 1),
        delta_dynamic_range_db=delta_dyn_db,
        dtw=energy_dtw,
        status=energy_status,
        similarity_score=energy_score,
    )

    # -------------------------------------------------------------
    # 5. Timbre & Articulation (MFCC & Spectral)
    # -------------------------------------------------------------
    p_mean_mfcc = p_mfcc.get("mean_mfcc", [])
    r_mean_mfcc = r_mfcc.get("mean_mfcc", [])
    mfcc_dist = compute_mfcc_cosine_distance(p_mean_mfcc, r_mean_mfcc)

    p_centroid = float(p_spectral.get("mean_spectral_centroid", 0.0))
    r_centroid = float(r_spectral.get("mean_spectral_centroid", 0.0))
    delta_centroid = round(p_centroid - r_centroid, 1)

    p_art_rate = float(p_rhythm.get("articulation_rate", 0.0))
    r_art_rate = float(r_rhythm.get("articulation_rate", 0.0))
    delta_art_rate = round(p_art_rate - r_art_rate, 1)

    if mfcc_dist < 0.20:
        timbre_status = "clear_articulation"
    else:
        timbre_status = "timbral_deviation"
        flaws_detected.append(f"Acoustic spectral divergence ({mfcc_dist:.2f} MFCC cosine distance)")

    timbre_score = round(max(0.0, min(100.0, 100.0 - mfcc_dist * 110.0)), 1)

    timbre_comp = TimbreComparison(
        mfcc_cosine_distance=mfcc_dist,
        participant_spectral_centroid=round(p_centroid, 1),
        reference_spectral_centroid=round(r_centroid, 1),
        delta_spectral_centroid=delta_centroid,
        participant_articulation_rate=round(p_art_rate, 1),
        reference_articulation_rate=round(r_art_rate, 1),
        delta_articulation_rate=delta_art_rate,
        status=timbre_status,
        similarity_score=timbre_score,
    )

    # -------------------------------------------------------------
    # 6. Word-Level Contrastive Alignment
    # -------------------------------------------------------------
    aligned_words_list = []
    if alignment_data and alignment_data.get("aligned_words"):
        aligned_words_list = alignment_data["aligned_words"]
    elif p_words and r_words:
        # Fallback word pairing from word features
        min_len = min(len(p_words), len(r_words))
        for i in range(min_len):
            pw = p_words[i]
            rw = r_words[i]
            aligned_words_list.append({
                "word": pw.get("word", ""),
                "participant_start": pw.get("start", 0.0),
                "participant_end": pw.get("end", 0.0),
                "reference_start": rw.get("start", 0.0),
                "reference_end": rw.get("end", 0.0),
            })

    word_comparisons = build_word_comparison(
        aligned_words=aligned_words_list,
        p_word_features=p_words,
        r_word_features=r_words,
    )

    # -------------------------------------------------------------
    # 7. Composite Acoustic Similarity Score
    # -------------------------------------------------------------
    overall_score = round(
        0.25 * pace_score
        + 0.20 * rhythm_score
        + 0.25 * pitch_score
        + 0.15 * energy_score
        + 0.15 * timbre_score,
        1,
    )

    summary = ComparisonSummary(
        overall_similarity_score=overall_score,
        pace_score=pace_score,
        pitch_score=pitch_score,
        rhythm_score=rhythm_score,
        energy_score=energy_score,
        timbre_score=timbre_score,
        primary_delivery_flaws=flaws_detected[:5],
    )

    return ComparisonResponse(
        analysis_id=analysis_id,
        status="compared",
        summary=summary,
        pace=pace_comp,
        pause=pause_comp,
        pitch=pitch_comp,
        energy=energy_comp,
        timbre=timbre_comp,
        aligned_words_comparison=word_comparisons,
        message="Acoustic and temporal comparison completed successfully.",
    )


def compare_and_store(db: Session, analysis_id: str) -> ComparisonResponse:
    """
    Main orchestration entry point:
    1. Loads analysis record from DB.
    2. Ensures features_json is present (auto-extracts if needed).
    3. Executes contrastive comparison and DTW.
    4. Persists result in analysis.comparison_json.
    5. Sets analysis.stage = 'compared'.
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise ValueError(f"Analysis with ID '{analysis_id}' not found.")

    # Auto-extract features if not yet present
    if not analysis.features_json:
        logger.info(f"[{analysis_id}] Features not found in DB. Auto-extracting features first.")
        extract_and_store_features(db, analysis_id)
        db.refresh(analysis)

    features_dict = json.loads(analysis.features_json)
    participant_data = features_dict.get("participant_features", {})
    reference_data = features_dict.get("reference_features", {})

    alignment_data = None
    if analysis.alignment_json:
        try:
            alignment_data = json.loads(analysis.alignment_json)
        except Exception as exc:
            logger.warning(f"Failed to parse alignment_json: {exc}")

    comparison_res = compare_tracks(
        participant_data=participant_data,
        reference_data=reference_data,
        alignment_data=alignment_data,
        analysis_id=analysis_id,
    )

    # Persist in DB
    analysis.comparison_json = json.dumps(comparison_res.model_dump())
    analysis.stage = "compared"
    db.commit()
    db.refresh(analysis)

    logger.info(
        f"[{analysis_id}] Comparison stored successfully. Overall similarity: {comparison_res.summary.overall_similarity_score}%"
    )
    return comparison_res
