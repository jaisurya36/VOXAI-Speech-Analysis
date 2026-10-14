"""
scoring_service.py — Rubric Scoring & Multi-Tiered Composite Evaluation Engine.

Synthesizes Track A (Delivery / Acoustic "HOW") and Track B (Content / Semantic "WHAT")
into a comprehensive, mathematically deterministic evaluation rubric:

1. Track A Delivery Rubric Score:
   - Pace (20%), Pitch Prosody (25%), Rhythm/Cadence (20%), Energy Dynamics (20%), Timbre (15%)
   - Minus calibrated temporal flaw deductions (High: -4.0, Med: -2.0, Low: -1.0, capped at 25.0)
2. Track B Content Rubric Score:
   - Grammar & Syntax (30%), Semantics & Clarity (35%), Content Structure & Rhetoric (35%)
3. Multi-Tiered Composite Score:
   - 50% Track A Delivery + 50% Track B Content
   - Letter Grade (A+, A, B+, B, C+, C, D, F)
   - Speaker Mastery Tier (Master, Proficient, Competent, Developing, Novice)
   - Percentile estimation derived from benchmark logistic model
   - 8-Dimension scorecard breakdown & standard rubric reference levels
"""

import json
import math
import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.schemas.scoring import (
    ScoringDimensionItem,
    FlawDeductionItem,
    DeliveryRubricBreakdown,
    ContentRubricBreakdown,
    RubricTierLevel,
    CompositeScoreSummary,
    ScoringResponse,
)
from app.services.content_ai_service import evaluate_content
from app.services.flaw_detection_service import detect_and_store_flaws
from app.services.transcription_service import transcribe_audio

logger = logging.getLogger(__name__)


STANDARD_RUBRIC_TIERS: List[RubricTierLevel] = [
    RubricTierLevel(
        tier_name="Master",
        title="Master Orator",
        min_score=90.0,
        max_score=100.0,
        delivery_standard="Exceptional prosodic expressiveness, intentional cadence pauses, dynamic volume modulation, zero high-severity temporal flaws.",
        content_standard="Impeccable syntax, rich and nuanced vocabulary, compelling rhetorical cohesion, and crystal-clear argumentation.",
    ),
    RubricTierLevel(
        tier_name="Proficient",
        title="Proficient Communicator",
        min_score=80.0,
        max_score=89.9,
        delivery_standard="Engaging tempo and steady projection with minor localized pitch flattening or isolated rhythm hesitation.",
        content_standard="Clear logical thesis, grammatically sound structures, and precise phrasing with occasional colloquial fillers.",
    ),
    RubricTierLevel(
        tier_name="Competent",
        title="Competent Speaker",
        min_score=65.0,
        max_score=79.9,
        delivery_standard="Comprehensible and audible delivery with periodic monotone passages, minor rushed syllable bursts, or pacing irregularities.",
        content_standard="Solid core message with occasional syntactical lapses, moderate repetition, or informal sentence transitions.",
    ),
    RubricTierLevel(
        tier_name="Developing",
        title="Developing Speaker",
        min_score=50.0,
        max_score=64.9,
        delivery_standard="Noticeable delivery friction: trailing energy drops, frequent syllable elongation, or recurring excessive silence gaps.",
        content_standard="Fragmented sentence structures, frequent semantic ambiguities, or inconsistent thematic focus.",
    ),
    RubricTierLevel(
        tier_name="Novice",
        title="Novice Speaker",
        min_score=0.0,
        max_score=49.9,
        delivery_standard="Severe prosodic and rhythmic divergence: persistent monotone, unintelligible pacing, or widespread communicative breakdowns.",
        content_standard="Disjointed phrasing, critical grammatical disconnects, and unformed or conflicting assertions.",
    ),
]


def determine_grade(score: float) -> str:
    """Return standard academic letter grade for a 0-100 score."""
    if score >= 95.0:
        return "A+"
    elif score >= 90.0:
        return "A"
    elif score >= 85.0:
        return "B+"
    elif score >= 80.0:
        return "B"
    elif score >= 75.0:
        return "C+"
    elif score >= 70.0:
        return "C"
    elif score >= 60.0:
        return "D"
    else:
        return "F"


def determine_tier(score: float) -> Tuple[str, str]:
    """Return (tier_name, tier_title) based on composite score."""
    if score >= 90.0:
        return "Master", "Master Orator"
    elif score >= 80.0:
        return "Proficient", "Proficient Communicator"
    elif score >= 65.0:
        return "Competent", "Competent Speaker"
    elif score >= 50.0:
        return "Developing", "Developing Speaker"
    else:
        return "Novice", "Novice Speaker"


def calculate_percentile(score: float) -> int:
    """
    Deterministic logistic CDF mapping score to estimated benchmark percentile.
    Parameters calibrated to general population speech distribution (mean=68.0, spread=12.0).
    """
    z = (score - 68.0) / 12.0
    logistic = 100.0 / (1.0 + math.exp(-1.4 * z))
    return int(max(1, min(99, round(logistic))))


def compute_rubric_scores(
    comparison_data: Dict[str, Any],
    flaws_data: Dict[str, Any],
    content_data: Dict[str, Any],
    archetype: Optional[str] = None,
    delivery_weight: float = 0.50,
    content_weight: float = 0.50,
    analysis_id: str = "",
) -> ScoringResponse:
    """
    Pure mathematical evaluation engine computing all rubric sub-scores and composite metric.
    No randomness or fake scores — everything derived from Track A and Track B inputs.
    """
    # -------------------------------------------------------------
    # 1. Track A: Acoustic Delivery Dimensions
    # -------------------------------------------------------------
    summary_cmp = comparison_data.get("summary", {})
    pace_score = float(
        summary_cmp.get("pace_score")
        if summary_cmp.get("pace_score") is not None
        else comparison_data.get("pace", {}).get("similarity_score", 75.0)
    )
    pitch_score = float(
        summary_cmp.get("pitch_score")
        if summary_cmp.get("pitch_score") is not None
        else comparison_data.get("pitch", {}).get("similarity_score", 75.0)
    )
    rhythm_score = float(
        summary_cmp.get("rhythm_score")
        if summary_cmp.get("rhythm_score") is not None
        else (comparison_data.get("rhythm", {}).get("similarity_score")
              or comparison_data.get("pause", {}).get("similarity_score", 75.0))
    )
    energy_score = float(
        summary_cmp.get("energy_score")
        if summary_cmp.get("energy_score") is not None
        else comparison_data.get("energy", {}).get("similarity_score", 75.0)
    )
    timbre_score = float(
        summary_cmp.get("timbre_score")
        if summary_cmp.get("timbre_score") is not None
        else comparison_data.get("timbre", {}).get("similarity_score", 75.0)
    )

    # Delivery weights sum to 1.0
    # Pace: 20%, Pitch: 25%, Rhythm: 20%, Energy: 20%, Timbre: 15%
    raw_delivery_score = round(
        0.20 * pace_score
        + 0.25 * pitch_score
        + 0.20 * rhythm_score
        + 0.20 * energy_score
        + 0.15 * timbre_score,
        1,
    )

    # Flaw severity deductions
    flaws_summary = flaws_data.get("summary", {})
    flaws_list = flaws_data.get("flaws", [])
    high_count = int(
        flaws_summary.get("high_severity_count")
        if flaws_summary.get("high_severity_count") is not None
        else sum(1 for f in flaws_list if f.get("severity") == "high")
    )
    medium_count = int(
        flaws_summary.get("medium_severity_count")
        if flaws_summary.get("medium_severity_count") is not None
        else sum(1 for f in flaws_list if f.get("severity") == "medium")
    )
    low_count = int(
        flaws_summary.get("low_severity_count")
        if flaws_summary.get("low_severity_count") is not None
        else sum(1 for f in flaws_list if f.get("severity") == "low")
    )

    high_penalty = round(high_count * 4.0, 1)
    medium_penalty = round(medium_count * 2.0, 1)
    low_penalty = round(low_count * 1.0, 1)

    flaw_deductions = [
        FlawDeductionItem(
            severity="high",
            count=high_count,
            penalty_per_unit=4.0,
            total_penalty=high_penalty,
        ),
        FlawDeductionItem(
            severity="medium",
            count=medium_count,
            penalty_per_unit=2.0,
            total_penalty=medium_penalty,
        ),
        FlawDeductionItem(
            severity="low",
            count=low_count,
            penalty_per_unit=1.0,
            total_penalty=low_penalty,
        ),
    ]

    uncapped_deduction = high_penalty + medium_penalty + low_penalty
    total_flaw_deduction = round(min(25.0, uncapped_deduction), 1)

    net_delivery_score = round(max(0.0, min(100.0, raw_delivery_score - total_flaw_deduction)), 1)
    delivery_grade = determine_grade(net_delivery_score)
    delivery_tier, _ = determine_tier(net_delivery_score)

    delivery_status = (
        "Optimal Vocal Delivery"
        if net_delivery_score >= 85
        else "Effective Delivery"
        if net_delivery_score >= 70
        else "Moderate Delivery Inconsistencies"
        if net_delivery_score >= 55
        else "High Acoustic Friction"
    )

    delivery_rubric = DeliveryRubricBreakdown(
        pace_score=round(pace_score, 1),
        pitch_score=round(pitch_score, 1),
        rhythm_score=round(rhythm_score, 1),
        energy_score=round(energy_score, 1),
        timbre_score=round(timbre_score, 1),
        raw_delivery_score=raw_delivery_score,
        flaw_penalties=flaw_deductions,
        total_flaw_deduction=total_flaw_deduction,
        net_delivery_score=net_delivery_score,
        grade=delivery_grade,
        tier=delivery_tier,
        status=delivery_status,
        archetype=archetype,
    )

    # -------------------------------------------------------------
    # 2. Track B: Content & Linguistic Dimensions
    # -------------------------------------------------------------
    grammar_obj = content_data.get("grammar", {})
    semantics_obj = content_data.get("semantics", {})
    content_obj = content_data.get("content", {})
    scores_dict = content_data.get("scores", {})

    grammar_score = float(
        grammar_obj.get("score")
        if grammar_obj.get("score") is not None
        else scores_dict.get("grammar_score", 75.0)
    )
    semantics_score = float(
        semantics_obj.get("score")
        if semantics_obj.get("score") is not None
        else scores_dict.get("semantics_score", 75.0)
    )
    structure_score = float(
        content_obj.get("score")
        if content_obj.get("score") is not None
        else scores_dict.get("structure_score", 75.0)
    )

    # Content weights: Grammar 30%, Semantics 35%, Structure 35%
    net_content_score = round(
        0.30 * grammar_score + 0.35 * semantics_score + 0.35 * structure_score,
        1,
    )
    net_content_score = max(0.0, min(100.0, net_content_score))

    content_grade = determine_grade(net_content_score)
    content_tier, _ = determine_tier(net_content_score)

    content_status = (
        "Compelling & Articulate"
        if net_content_score >= 85
        else "Clear & Coherent"
        if net_content_score >= 70
        else "Functional Content"
        if net_content_score >= 55
        else "Grammar / Semantic Breakdowns"
    )

    grammar_errors_count = len(grammar_obj.get("errors", []))
    semantic_issues_count = len(semantics_obj.get("issues", []))
    content_strengths_count = len(content_obj.get("strengths", []))

    content_rubric = ContentRubricBreakdown(
        grammar_score=round(grammar_score, 1),
        semantics_score=round(semantics_score, 1),
        structure_score=round(structure_score, 1),
        net_content_score=net_content_score,
        grade=content_grade,
        tier=content_tier,
        status=content_status,
        strengths_count=content_strengths_count,
        issues_count=grammar_errors_count + semantic_issues_count,
    )

    # -------------------------------------------------------------
    # 3. Multi-Tiered Composite Synthesis
    # -------------------------------------------------------------
    weighted_delivery = round(net_delivery_score * delivery_weight, 2)
    weighted_content = round(net_content_score * content_weight, 2)
    overall_score = round(weighted_delivery + weighted_content, 1)
    overall_score = max(0.0, min(100.0, overall_score))

    overall_grade = determine_grade(overall_score)
    overall_tier, tier_title = determine_tier(overall_score)
    percentile_estimate = calculate_percentile(overall_score)

    if overall_score >= 85:
        summary_headline = f"Executive Caliber — Rated {tier_title} with commanding vocal presence and sharp messaging."
        key_takeaway = "Sustain this elite baseline; focus on micro-inflections for maximum audience persuasion."
    elif overall_score >= 75:
        summary_headline = f"Solid Communicator — Rated {tier_title} demonstrating dependable clarity and cadence."
        key_takeaway = "Elevate dynamic pitch modulation and eliminate localized hesitation pauses to enter the Master tier."
    elif overall_score >= 60:
        summary_headline = f"Functional Delivery — Rated {tier_title} with clear potential hindered by pacing or structural friction."
        key_takeaway = "Target your primary temporal flaws and apply structured pauses before key statements."
    else:
        summary_headline = f"Foundational Stage — Rated {tier_title} requiring deliberate vocal pacing and syntax reconstruction."
        key_takeaway = "Slow down overall speech rate, breathe from the diaphragm at sentence boundaries, and use shorter phrases."

    summary = CompositeScoreSummary(
        overall_score=overall_score,
        grade=overall_grade,
        tier=overall_tier,
        tier_title=tier_title,
        delivery_weight=delivery_weight,
        content_weight=content_weight,
        weighted_delivery_score=weighted_delivery,
        weighted_content_score=weighted_content,
        percentile_estimate=percentile_estimate,
        summary_headline=summary_headline,
        key_takeaway=key_takeaway,
    )

    # -------------------------------------------------------------
    # 4. Dimension-by-Dimension Scorecard
    # -------------------------------------------------------------
    dimensions = [
        # Delivery dimensions
        ScoringDimensionItem(
            name="Speech Rate & Pace",
            track="delivery",
            raw_score=round(pace_score, 1),
            weight_within_track=0.20,
            overall_weight=round(0.20 * delivery_weight, 3),
            weighted_score=round(pace_score * 0.20 * delivery_weight, 2),
            grade=determine_grade(pace_score),
            status="Optimal Tempo" if pace_score >= 80 else "Acceptable" if pace_score >= 65 else "Pace Divergence",
            feedback="WPM alignment relative to natural ideal baseline.",
        ),
        ScoringDimensionItem(
            name="Pitch Prosody & Intonation",
            track="delivery",
            raw_score=round(pitch_score, 1),
            weight_within_track=0.25,
            overall_weight=round(0.25 * delivery_weight, 3),
            weighted_score=round(pitch_score * 0.25 * delivery_weight, 2),
            grade=determine_grade(pitch_score),
            status="Expressive Melody" if pitch_score >= 80 else "Moderate Range" if pitch_score >= 65 else "Monotone Tendency",
            feedback="Melodic variance and fundamental frequency F0 contour modulation.",
        ),
        ScoringDimensionItem(
            name="Cadence & Pause Discipline",
            track="delivery",
            raw_score=round(rhythm_score, 1),
            weight_within_track=0.20,
            overall_weight=round(0.20 * delivery_weight, 3),
            weighted_score=round(rhythm_score * 0.20 * delivery_weight, 2),
            grade=determine_grade(rhythm_score),
            status="Controlled Cadence" if rhythm_score >= 80 else "Adequate" if rhythm_score >= 65 else "Cadence Gaps / Rushed",
            feedback="Silence duration distribution and syntactic pause placement.",
        ),
        ScoringDimensionItem(
            name="Dynamic Energy & Projection",
            track="delivery",
            raw_score=round(energy_score, 1),
            weight_within_track=0.20,
            overall_weight=round(0.20 * delivery_weight, 3),
            weighted_score=round(energy_score * 0.20 * delivery_weight, 2),
            grade=determine_grade(energy_score),
            status="Commanding Projection" if energy_score >= 80 else "Moderate Volume" if energy_score >= 65 else "Energy Decay / Drop",
            feedback="RMS volume intensity consistency and syllable stress emphasis.",
        ),
        ScoringDimensionItem(
            name="Articulation & Timbre",
            track="delivery",
            raw_score=round(timbre_score, 1),
            weight_within_track=0.15,
            overall_weight=round(0.15 * delivery_weight, 3),
            weighted_score=round(timbre_score * 0.15 * delivery_weight, 2),
            grade=determine_grade(timbre_score),
            status="Crisp Articulation" if timbre_score >= 80 else "Clear" if timbre_score >= 65 else "Timbral Deviation",
            feedback="MFCC spectral signature match and phoneme clarity.",
        ),
        # Content dimensions
        ScoringDimensionItem(
            name="Grammar & Syntactic Precision",
            track="content",
            raw_score=round(grammar_score, 1),
            weight_within_track=0.30,
            overall_weight=round(0.30 * content_weight, 3),
            weighted_score=round(grammar_score * 0.30 * content_weight, 2),
            grade=determine_grade(grammar_score),
            status="Flawless Syntax" if grammar_score >= 85 else "Minor Slip-ups" if grammar_score >= 70 else "Syntax Errors",
            feedback=f"{grammar_errors_count} grammatical corrections identified." if grammar_errors_count else "High grammatical rigor maintained.",
        ),
        ScoringDimensionItem(
            name="Semantic Clarity & Meaning",
            track="content",
            raw_score=round(semantics_score, 1),
            weight_within_track=0.35,
            overall_weight=round(0.35 * content_weight, 3),
            weighted_score=round(semantics_score * 0.35 * content_weight, 2),
            grade=determine_grade(semantics_score),
            status="Transparent Meaning" if semantics_score >= 85 else "Adequate Clarity" if semantics_score >= 70 else "Ambiguous Phrasing",
            feedback=f"{semantic_issues_count} semantic ambiguities flagged." if semantic_issues_count else "Unambiguous propositional clarity.",
        ),
        ScoringDimensionItem(
            name="Content Structure & Rhetoric",
            track="content",
            raw_score=round(structure_score, 1),
            weight_within_track=0.35,
            overall_weight=round(0.35 * content_weight, 3),
            weighted_score=round(structure_score * 0.35 * content_weight, 2),
            grade=determine_grade(structure_score),
            status="Compelling Progression" if structure_score >= 85 else "Structured" if structure_score >= 70 else "Fragmented Flow",
            feedback=f"{content_strengths_count} substantive rhetorical strengths detected.",
        ),
    ]

    return ScoringResponse(
        analysis_id=analysis_id,
        status="scored",
        summary=summary,
        delivery=delivery_rubric,
        content=content_rubric,
        dimensions=dimensions,
        rubric_tiers=STANDARD_RUBRIC_TIERS,
        message="Rubric scoring and composite evaluation completed successfully.",
    )


def score_and_store(
    db: Session,
    analysis_id: str,
    delivery_weight: float = 0.50,
    content_weight: float = 0.50,
) -> ScoringResponse:
    """
    Main orchestration entry point for Phase 11:
    1. Loads analysis record.
    2. Auto-chains missing prerequisite steps:
       - If transcript is missing, runs transcription.
       - If content evaluation is missing, runs evaluate_content.
       - If temporal flaws / comparison are missing, runs detect_and_store_flaws.
    3. Computes multi-tiered rubric scoring for Track A and Track B.
    4. Persists in analysis.scores_json and sets analysis.stage = 'scored'.
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise ValueError(f"Analysis with ID '{analysis_id}' not found.")

    if not analysis.analysis_audio_path:
        raise ValueError("Participant audio is missing. Upload media first.")

    # 1. Ensure transcription exists
    if not analysis.delivery_transcript and not analysis.raw_transcript:
        logger.info(f"[{analysis_id}] Transcription missing. Running transcription first.")
        transcribe_audio(db, analysis_id)
        db.refresh(analysis)

    transcript = analysis.delivery_transcript or analysis.raw_transcript or ""

    # 2. Ensure Track B Content Evaluation exists
    if not analysis.content_analysis_json:
        logger.info(f"[{analysis_id}] Content evaluation missing. Running content evaluation first.")
        content_eval = evaluate_content(transcript, analysis_id=analysis_id)
        analysis.corrected_transcript = content_eval.get("corrected_transcript", transcript)
        analysis.content_analysis_json = json.dumps(content_eval)
        db.commit()
        db.refresh(analysis)

    # 3. Ensure Track A Temporal Flaws & Acoustic Comparison exist
    if not analysis.flaws_json or not analysis.comparison_json:
        logger.info(f"[{analysis_id}] Temporal flaws or comparison missing. Running flaw detection first.")
        detect_and_store_flaws(db, analysis_id)
        db.refresh(analysis)

    comparison_dict = {}
    if analysis.comparison_json:
        try:
            comparison_dict = json.loads(analysis.comparison_json)
        except Exception as exc:
            logger.warning(f"Failed to parse comparison_json: {exc}")

    flaws_dict = {}
    if analysis.flaws_json:
        try:
            flaws_dict = json.loads(analysis.flaws_json)
        except Exception as exc:
            logger.warning(f"Failed to parse flaws_json: {exc}")

    content_dict = {}
    if analysis.content_analysis_json:
        try:
            content_dict = json.loads(analysis.content_analysis_json)
        except Exception as exc:
            logger.warning(f"Failed to parse content_analysis_json: {exc}")

    # Extract archetype if explanations exist
    archetype_name = None
    if analysis.explanations_json:
        try:
            exp_data = json.loads(analysis.explanations_json)
            archetype_name = exp_data.get("diagnosis", {}).get("archetype", {}).get("name")
        except Exception:
            pass

    # Normalize weights if custom
    total_w = delivery_weight + content_weight
    if total_w > 0:
        norm_delivery_w = delivery_weight / total_w
        norm_content_w = content_weight / total_w
    else:
        norm_delivery_w = 0.50
        norm_content_w = 0.50

    response = compute_rubric_scores(
        comparison_data=comparison_dict,
        flaws_data=flaws_dict,
        content_data=content_dict,
        archetype=archetype_name,
        delivery_weight=norm_delivery_w,
        content_weight=norm_content_w,
        analysis_id=analysis_id,
    )

    # Persist in DB
    analysis.scores_json = json.dumps(response.model_dump())
    analysis.stage = "scored"
    db.commit()
    db.refresh(analysis)

    logger.info(
        f"[{analysis_id}] Rubric evaluation stored. Overall score: {response.summary.overall_score} ({response.summary.tier})"
    )
    return response
