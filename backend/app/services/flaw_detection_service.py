"""
flaw_detection_service.py — Temporal Speech Flaw Finding & Grounding Engine.

Detects concrete, timestamped, mathematically explainable speech flaws by contrasting
participant speech against Track A Ideal Delivery Reference:
1. Pace & Tempo Flaws: Local rushed words, compressed syllables, drawn-out hesitations.
2. Pause & Cadence Flaws: Unintended awkward silence gaps, missing breath pauses, word collisions.
3. Pitch & Prosody Flaws: Monotone melodic segments, flat inflections on key keywords.
4. Energy Dynamics Flaws: Sentence-ending energy fadeouts, abrupt vocal volume bursts.
5. Fluency & Articulation Flaws: Syllable slurring, inaudible consonant drops.

Every detected flaw has:
- Precise start and end timestamps (seconds)
- Affected words / phrase context
- Quantitative metric evidence (actual participant value vs reference benchmark)
- Severity classification (low, medium, high)
- Actionable improvement suggestion
"""

import json
import logging
import uuid
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.schemas.flaws import (
    TemporalFlawItem,
    FlawsSummary,
    FlawsResponse,
    FlawSeverity,
    FlawCategory,
)
from app.services.comparison_service import compare_and_store

logger = logging.getLogger(__name__)


def detect_pause_flaws(
    aligned_words: List[Dict[str, Any]],
    total_duration: float,
) -> List[TemporalFlawItem]:
    """
    Detects excessive hesitation silences and rushed colliding transitions between words.
    """
    flaws: List[TemporalFlawItem] = []
    if len(aligned_words) < 2:
        return flaws

    for i in range(len(aligned_words) - 1):
        w_curr = aligned_words[i]
        w_next = aligned_words[i + 1]

        p_end = float(w_curr.get("participant_end", 0.0))
        p_start_next = float(w_next.get("participant_start", 0.0))
        p_gap = round(p_start_next - p_end, 3)

        r_end = float(w_curr.get("reference_end", 0.0))
        r_start_next = float(w_next.get("reference_start", 0.0))
        r_gap = round(r_start_next - r_end, 3)

        curr_text = w_curr.get("word", "")
        next_text = w_next.get("word", "")
        context_phrase = f"{curr_text} ... {next_text}"

        # 1. Excessive silence gap
        if p_gap > 0.75 and r_gap < 0.40:
            if p_gap >= 1.6:
                severity = FlawSeverity.HIGH.value
            elif p_gap >= 1.0:
                severity = FlawSeverity.MEDIUM.value
            else:
                severity = FlawSeverity.LOW.value

            flaws.append(
                TemporalFlawItem(
                    id=f"flaw-pause-{uuid.uuid4().hex[:6]}",
                    flaw_type="excessive_pause",
                    category=FlawCategory.PAUSE.value,
                    severity=severity,
                    start_time=round(p_end, 2),
                    end_time=round(p_start_next, 2),
                    duration=p_gap,
                    description=f"Unintended silence pause of {p_gap}s between '{curr_text}' and '{next_text}' disrupts speech flow.",
                    affected_text=context_phrase,
                    metric_evidence={
                        "participant_pause_duration": p_gap,
                        "reference_pause_duration": max(0.0, r_gap),
                        "pause_discrepancy": round(p_gap - r_gap, 3),
                    },
                    suggestion="Keep breath control steady. Reduce hesitation between these words to preserve listener momentum.",
                )
            )

        # 2. Rushed collision / missing pause at clause end
        is_sentence_boundary = curr_text.endswith((".", "!", "?", ";", ":", ","))
        if is_sentence_boundary and p_gap < 0.05 and r_gap >= 0.30:
            flaws.append(
                TemporalFlawItem(
                    id=f"flaw-rush-{uuid.uuid4().hex[:6]}",
                    flaw_type="rushed_transition",
                    category=FlawCategory.PAUSE.value,
                    severity=FlawSeverity.MEDIUM.value,
                    start_time=round(p_end, 2),
                    end_time=round(p_start_next + 0.1, 2),
                    duration=round(p_gap, 2),
                    description=f"Sentence boundary after '{curr_text}' rushed without a breathing pause ({p_gap}s gap vs {r_gap}s ideal).",
                    affected_text=context_phrase,
                    metric_evidence={
                        "participant_pause_duration": p_gap,
                        "reference_pause_duration": r_gap,
                    },
                    suggestion="Insert a brief deliberate pause (0.3s–0.5s) at punctuation marks to let key ideas settle.",
                )
            )

    return flaws


def detect_word_tempo_flaws(
    aligned_words_comp: List[Dict[str, Any]],
) -> List[TemporalFlawItem]:
    """
    Detects individual words that are rushed/slurred or excessively drawn out.
    """
    flaws: List[TemporalFlawItem] = []

    for item in aligned_words_comp:
        word = item.get("word", "")
        p_dur = float(item.get("participant_duration", 0.0))
        r_dur = float(item.get("reference_duration", 0.0))
        dur_ratio = float(item.get("duration_ratio", 1.0))
        tempo_flag = item.get("tempo_flag", "normal")
        p_start = float(item.get("participant_start", 0.0))
        p_end = float(item.get("participant_end", 0.0))

        # Ignore tiny filler tokens (<3 letters) unless severely warped
        is_short_word = len(word.strip(".,!?")) <= 2

        # Rushed word / phonetic compression
        if tempo_flag == "compressed" and dur_ratio < 0.58 and p_dur < 0.18 and not is_short_word:
            severity = FlawSeverity.MEDIUM.value if dur_ratio < 0.45 else FlawSeverity.LOW.value
            flaws.append(
                TemporalFlawItem(
                    id=f"flaw-word-rush-{uuid.uuid4().hex[:6]}",
                    flaw_type="compressed_syllables",
                    category=FlawCategory.PACE.value,
                    severity=severity,
                    start_time=round(p_start, 2),
                    end_time=round(p_end, 2),
                    duration=round(p_dur, 3),
                    description=f"Word '{word}' was spoken at {round(p_dur, 2)}s ({dur_ratio}× of ideal delivery duration). High risk of syllable clipping.",
                    affected_text=word,
                    metric_evidence={
                        "participant_duration": p_dur,
                        "reference_duration": r_dur,
                        "duration_ratio": dur_ratio,
                    },
                    suggestion=f"Articulate '{word}' fully before transitioning into the next syllable.",
                )
            )

        # Prolonged word / drawn-out hesitation
        elif tempo_flag == "stretched" and dur_ratio > 1.70 and p_dur > 0.65:
            severity = FlawSeverity.MEDIUM.value if dur_ratio > 2.2 else FlawSeverity.LOW.value
            flaws.append(
                TemporalFlawItem(
                    id=f"flaw-word-drag-{uuid.uuid4().hex[:6]}",
                    flaw_type="drawn_out_syllable",
                    category=FlawCategory.PACE.value,
                    severity=severity,
                    start_time=round(p_start, 2),
                    end_time=round(p_end, 2),
                    duration=round(p_dur, 3),
                    description=f"Word '{word}' was prolonged to {round(p_dur, 2)}s ({dur_ratio}× of reference pace). Causes pacing drag.",
                    affected_text=word,
                    metric_evidence={
                        "participant_duration": p_dur,
                        "reference_duration": r_dur,
                        "duration_ratio": dur_ratio,
                    },
                    suggestion=f"Deliver '{word}' crisply without lingering on vowel extensions.",
                )
            )

    return flaws


def detect_monotone_passages(
    p_pitch_contour: List[float],
    r_pitch_contour: List[float],
    total_duration: float,
    words_list: List[Dict[str, Any]],
    window_frames: int = 15,
) -> List[TemporalFlawItem]:
    """
    Scans pitch contour with a sliding window to identify extended intervals of flat/monotone delivery.
    """
    flaws: List[TemporalFlawItem] = []
    p_arr = np.array(p_pitch_contour, dtype=np.float32)
    r_arr = np.array(r_pitch_contour, dtype=np.float32)

    if len(p_arr) < window_frames or total_duration <= 0:
        return flaws

    step = 5
    raw_monotone_spans: List[Tuple[int, int, float, float]] = []

    for start_idx in range(0, len(p_arr) - window_frames + 1, step):
        end_idx = start_idx + window_frames
        p_win = p_arr[start_idx:end_idx]
        r_win = r_arr[start_idx:end_idx]

        # Consider only voiced frames (>50 Hz)
        p_voiced = p_win[p_win > 50.0]
        r_voiced = r_win[r_win > 50.0]

        if len(p_voiced) >= 6:
            p_std = float(np.std(p_voiced))
            r_std = float(np.std(r_voiced)) if len(r_voiced) >= 4 else 20.0

            # Flaw condition: participant pitch variation is under 40% of reference and std < 8 Hz
            if p_std < 0.40 * max(r_std, 15.0) and p_std < 8.5:
                raw_monotone_spans.append((start_idx, end_idx, p_std, r_std))

    if not raw_monotone_spans:
        return flaws

    # Merge overlapping monotone spans
    merged_spans: List[Tuple[int, int, float, float]] = []
    curr_start, curr_end, min_std, ref_std_avg = raw_monotone_spans[0]

    for next_start, next_end, n_std, r_std in raw_monotone_spans[1:]:
        if next_start <= curr_end:
            curr_end = max(curr_end, next_end)
            min_std = min(min_std, n_std)
        else:
            merged_spans.append((curr_start, curr_end, min_std, ref_std_avg))
            curr_start, curr_end, min_std, ref_std_avg = next_start, next_end, n_std, r_std

    merged_spans.append((curr_start, curr_end, min_std, ref_std_avg))

    for span_start_idx, span_end_idx, std_val, r_std_val in merged_spans:
        t_start = round(float(span_start_idx / len(p_arr)) * total_duration, 2)
        t_end = round(float(span_end_idx / len(p_arr)) * total_duration, 2)
        dur = round(t_end - t_start, 2)

        # Ignore tiny segments (<1.2s)
        if dur < 1.2:
            continue

        # Extract words spoken in interval
        spoken_words = [
            w.get("word", "")
            for w in words_list
            if float(w.get("participant_start", w.get("start", 0.0))) >= t_start - 0.2
            and float(w.get("participant_end", w.get("end", 0.0))) <= t_end + 0.2
        ]
        excerpt = " ".join(spoken_words[:8])
        if len(spoken_words) > 8:
            excerpt += "..."

        severity = FlawSeverity.HIGH.value if std_val < 4.0 else FlawSeverity.MEDIUM.value

        flaws.append(
            TemporalFlawItem(
                id=f"flaw-pitch-mono-{uuid.uuid4().hex[:6]}",
                flaw_type="monotone_passage",
                category=FlawCategory.PITCH.value,
                severity=severity,
                start_time=t_start,
                end_time=t_end,
                duration=dur,
                description=f"Monotone delivery between {t_start}s and {t_end}s (pitch variation: {round(std_val, 1)} Hz vs {round(r_std_val, 1)} Hz in ideal delivery).",
                affected_text=excerpt or "Sustained monotone segment",
                metric_evidence={
                    "participant_f0_std": round(std_val, 1),
                    "reference_f0_std": round(r_std_val, 1),
                    "variation_ratio": round(std_val / max(r_std_val, 0.001), 2),
                },
                suggestion="Inject vocal color: emphasize key operational nouns and verbs with upward or downward pitch shifts.",
            )
        )

    return flaws


def detect_energy_dynamics_flaws(
    p_energy_contour: List[float],
    total_duration: float,
    phrases_list: List[Dict[str, Any]],
) -> List[TemporalFlawItem]:
    """
    Detects vocal fadeout (trailing off at phrase endings) and sudden harsh volume spikes.
    """
    flaws: List[TemporalFlawItem] = []
    e_arr = np.array(p_energy_contour, dtype=np.float32)

    if len(e_arr) < 20 or total_duration <= 0:
        return flaws

    mean_rms = float(np.mean(e_arr))

    # 1. Trailing off at phrase endings
    for phrase in phrases_list:
        p_start = float(phrase.get("participant_start", 0.0))
        p_end = float(phrase.get("participant_end", 0.0))
        dur = p_end - p_start

        if dur >= 1.5:
            # Check last 20% of phrase
            idx_start = int((p_start / total_duration) * len(e_arr))
            idx_end = min(len(e_arr), int((p_end / total_duration) * len(e_arr)))

            if idx_end - idx_start >= 5:
                tail_len = max(2, int((idx_end - idx_start) * 0.25))
                phrase_head_rms = float(np.mean(e_arr[idx_start : idx_end - tail_len]))
                phrase_tail_rms = float(np.mean(e_arr[idx_end - tail_len : idx_end]))

                # Tail is under 35% of head RMS
                if phrase_tail_rms < 0.35 * phrase_head_rms and phrase_head_rms > 0.02:
                    t_tail_start = round(p_end - (dur * 0.25), 2)
                    flaws.append(
                        TemporalFlawItem(
                            id=f"flaw-energy-fade-{uuid.uuid4().hex[:6]}",
                            flaw_type="trailing_energy_drop",
                            category=FlawCategory.ENERGY.value,
                            severity=FlawSeverity.MEDIUM.value,
                            start_time=t_tail_start,
                            end_time=round(p_end, 2),
                            duration=round(p_end - t_tail_start, 2),
                            description=f"Vocal energy dropped by {round((1.0 - phrase_tail_rms / phrase_head_rms) * 100)}% at phrase ending '{phrase.get('text', '')[:30]}...'.",
                            affected_text=phrase.get("text", "")[:45],
                            metric_evidence={
                                "phrase_body_rms": round(phrase_head_rms, 4),
                                "phrase_tail_rms": round(phrase_tail_rms, 4),
                                "drop_percentage": round((1.0 - phrase_tail_rms / phrase_head_rms) * 100, 1),
                            },
                            suggestion="Maintain diaphragmatic breath support until the final word to prevent sentence conclusions from fading.",
                        )
                    )

    # 2. Volume bursts / Overprojection spikes
    spike_indices = np.where(e_arr > 2.4 * max(mean_rms, 0.01))[0]
    if len(spike_indices) > 0:
        # Group contiguous spike frames
        groups: List[List[int]] = []
        curr_g = [int(spike_indices[0])]
        for idx in spike_indices[1:]:
            if idx == curr_g[-1] + 1:
                curr_g.append(int(idx))
            else:
                groups.append(curr_g)
                curr_g = [int(idx)]
        groups.append(curr_g)

        for g in groups:
            # Must last at least 2 frames (~0.3s)
            if len(g) >= 2:
                t_s = round((g[0] / len(e_arr)) * total_duration, 2)
                t_e = round(((g[-1] + 1) / len(e_arr)) * total_duration, 2)
                peak_val = float(np.max(e_arr[g]))
                flaws.append(
                    TemporalFlawItem(
                        id=f"flaw-energy-spike-{uuid.uuid4().hex[:6]}",
                        flaw_type="overprojection_burst",
                        category=FlawCategory.ENERGY.value,
                        severity=FlawSeverity.LOW.value,
                        start_time=t_s,
                        end_time=t_e,
                        duration=round(t_e - t_s, 2),
                        description=f"Vocal spike at {t_s}s ({round(peak_val / max(mean_rms, 1e-4), 1)}× above average energy). Risks jarring the listener.",
                        affected_text="Sudden volume burst",
                        metric_evidence={
                            "peak_rms": round(peak_val, 4),
                            "mean_rms": round(mean_rms, 4),
                        },
                        suggestion="Smooth out vocal attacks. Emphasize concepts through cadence and pitch rather than sudden volume increases.",
                    )
                )

    return flaws


def scan_temporal_flaws(
    features_data: Dict[str, Any],
    comparison_data: Dict[str, Any],
    alignment_data: Optional[Dict[str, Any]] = None,
    analysis_id: str = "unknown",
) -> FlawsResponse:
    """
    Main orchestration engine to scan, detect, filter, and score temporal flaws.
    """
    p_feats = features_data.get("participant_features", {})
    r_feats = features_data.get("reference_features", {})

    p_pitch = p_feats.get("pitch", {})
    r_pitch = r_feats.get("pitch", {})
    p_energy = p_feats.get("energy", {})
    p_rhythm = p_feats.get("rhythm", {})

    total_duration = float(p_rhythm.get("total_duration", 0.0))

    aligned_words = []
    aligned_phrases = []
    if alignment_data:
        aligned_words = alignment_data.get("aligned_words", [])
        aligned_phrases = alignment_data.get("aligned_phrases", [])

    aligned_words_comp = comparison_data.get("aligned_words_comparison", [])

    all_flaws: List[TemporalFlawItem] = []

    # 1. Pause & Cadence flaws
    all_flaws.extend(detect_pause_flaws(aligned_words, total_duration))

    # 2. Word tempo flaws (compressed vs prolonged words)
    all_flaws.extend(detect_word_tempo_flaws(aligned_words_comp))

    # 3. Monotone pitch spans
    all_flaws.extend(
        detect_monotone_passages(
            p_pitch_contour=p_pitch.get("contour", []),
            r_pitch_contour=r_pitch.get("contour", []),
            total_duration=total_duration,
            words_list=aligned_words,
            window_frames=15,
        )
    )

    # 4. Energy dynamics flaws (fadeouts & spikes)
    all_flaws.extend(
        detect_energy_dynamics_flaws(
            p_energy_contour=p_energy.get("contour", []),
            total_duration=total_duration,
            phrases_list=aligned_phrases,
        )
    )

    # Sort flaws chronologically
    all_flaws.sort(key=lambda x: x.start_time)

    # Calculate summary metrics
    high_count = sum(1 for f in all_flaws if f.severity == FlawSeverity.HIGH.value)
    med_count = sum(1 for f in all_flaws if f.severity == FlawSeverity.MEDIUM.value)
    low_count = sum(1 for f in all_flaws if f.severity == FlawSeverity.LOW.value)

    category_counts: Dict[str, int] = {}
    for f in all_flaws:
        category_counts[f.category] = category_counts.get(f.category, 0) + 1

    dur_mins = max(total_duration / 60.0, 0.05)
    density = round(len(all_flaws) / dur_mins, 1)

    # Determine primary concern
    if high_count > 0:
        high_categories = [f.category for f in all_flaws if f.severity == FlawSeverity.HIGH.value]
        top_cat = max(set(high_categories), key=high_categories.count)
        primary_concern = f"High severity {top_cat} irregularities requiring immediate attention"
    elif med_count > 0:
        med_categories = [f.category for f in all_flaws if f.severity == FlawSeverity.MEDIUM.value]
        top_cat = max(set(med_categories), key=med_categories.count)
        primary_concern = f"Noticeable {top_cat} inconsistencies impacting delivery clarity"
    elif len(all_flaws) > 0:
        primary_concern = "Minor delivery deviations; overall cadence is solid"
    else:
        primary_concern = "Excellent delivery; speech closely aligns with ideal delivery benchmarks"

    summary = FlawsSummary(
        total_flaws=len(all_flaws),
        high_severity_count=high_count,
        medium_severity_count=med_count,
        low_severity_count=low_count,
        flaw_density_per_minute=density,
        flaws_by_category=category_counts,
        primary_concern=primary_concern,
    )

    return FlawsResponse(
        analysis_id=analysis_id,
        status="flaws_detected",
        summary=summary,
        flaws=all_flaws,
        message=f"Detected {len(all_flaws)} temporal speech flaws across {len(category_counts)} categories.",
    )


def detect_and_store_flaws(db: Session, analysis_id: str) -> FlawsResponse:
    """
    Primary DB orchestration entry point:
    1. Loads analysis record.
    2. Ensures comparison_json is present (auto-triggers compare_and_store if missing).
    3. Executes temporal flaw detection.
    4. Persists result in analysis.flaws_json.
    5. Sets analysis.stage = 'flaws_detected'.
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise ValueError(f"Analysis with ID '{analysis_id}' not found.")

    # Auto-run comparison if not present
    if not analysis.comparison_json:
        logger.info(f"[{analysis_id}] Comparison not found in DB. Auto-running comparison first.")
        compare_and_store(db, analysis_id)
        db.refresh(analysis)

    features_dict = json.loads(analysis.features_json)
    comparison_dict = json.loads(analysis.comparison_json)

    alignment_dict = None
    if analysis.alignment_json:
        try:
            alignment_dict = json.loads(analysis.alignment_json)
        except Exception as exc:
            logger.warning(f"Failed to parse alignment_json: {exc}")

    flaws_response = scan_temporal_flaws(
        features_data=features_dict,
        comparison_data=comparison_dict,
        alignment_data=alignment_dict,
        analysis_id=analysis_id,
    )

    # Persist in DB
    analysis.flaws_json = json.dumps(flaws_response.model_dump())
    analysis.stage = "flaws_detected"
    db.commit()
    db.refresh(analysis)

    logger.info(
        f"[{analysis_id}] Flaws stored successfully. Total flaws detected: {flaws_response.summary.total_flaws}"
    )
    return flaws_response
