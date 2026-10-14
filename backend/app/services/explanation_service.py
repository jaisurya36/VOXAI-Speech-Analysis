"""
explanation_service.py — Causal Explanations & Reasoning Engine.

Maps timestamped delivery flaws and acoustic deviations to:
1. Mathematical Signal-Processing Causes (The exact "Why")
2. Physiological & Behavioral Drivers (breath, vocal tension, cognitive buffering)
3. Perceptual Impact on Listeners (retention, credibility, clarity)
4. Prescriptive Actionable Drills
5. Executive Delivery Archetype & Sequential Action Roadmap

Features hybrid execution:
- Uses Google Gemini (gemini-2.0-flash) with structured JSON schema when GEMINI_API_KEY is available.
- Features a rich deterministic causal reasoning engine as an automatic fallback when offline.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.analysis import Analysis
from app.schemas.explanations import (
    CausalFlawExplanation,
    DeliveryArchetype,
    CausalDiagnosis,
    ExplanationsResponse,
)
from app.services.flaw_detection_service import detect_and_store_flaws

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an elite speech scientist, acoustic phonetician, and executive vocal coach.
Your mission is to provide deep, mathematically grounded causal explanations for detected speech flaws.
Do not just repeat what happened; explain WHY it happened physiologically and cognitively, the psychological effect on the listener, and the exact physical drill to fix it.

CRITICAL INSTRUCTIONS:
1. Explain each provided flaw with rigorous scientific attribution.
2. Determine an accurate Delivery Archetype (e.g. 'High-Velocity Sprinter', 'Controlled Analytical Monotone', 'Deliberate Hesitator', 'Dynamic Orator').
3. Identify top 3 physiological/cognitive root causes.
4. Highlight genuine acoustic strengths.
5. Provide a 3-step actionable coaching roadmap.
6. Return ONLY valid JSON adhering strictly to the requested schema.
"""


def _generate_gemini_explanations(
    flaws: List[Dict[str, Any]],
    comparison: Dict[str, Any],
    transcript: str,
    analysis_id: str,
) -> Optional[ExplanationsResponse]:
    """Call Google Gemini 2.0 Flash to synthesize structured causal reasoning."""
    if not settings.gemini_api_key or not settings.gemini_api_key.strip():
        logger.info(f"[{analysis_id}] GEMINI_API_KEY not configured. Using deterministic causal engine.")
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.gemini_api_key)

        prompt_data = {
            "analysis_id": analysis_id,
            "transcript_sample": transcript[:500],
            "comparison_summary": comparison.get("summary", {}),
            "pace_metrics": comparison.get("pace", {}),
            "pitch_metrics": comparison.get("pitch", {}),
            "pause_metrics": comparison.get("pause", {}),
            "energy_metrics": comparison.get("energy", {}),
            "detected_flaws": flaws[:10],  # Top 10 flaws for concise prompt
        }

        user_content = f"Analyze these speech analytics results and generate causal explanations:\n\n{json.dumps(prompt_data, indent=2)}"

        response = client.models.generate_content(
            model=settings.gemini_text_model,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )

        raw_json = json.loads(response.text.strip())

        # Construct and validate response
        diagnosis_data = raw_json.get("diagnosis", {})
        archetype_data = diagnosis_data.get("archetype", {})

        archetype = DeliveryArchetype(
            name=archetype_data.get("name", "Dynamic Speaker"),
            summary=archetype_data.get("summary", "Balanced vocal delivery with focused refinement areas."),
            key_traits=archetype_data.get("key_traits", ["Clear projection", "Moderate pacing"]),
        )

        diagnosis = CausalDiagnosis(
            archetype=archetype,
            top_root_causes=diagnosis_data.get("top_root_causes", ["Breath pacing", "Pitch modulation"]),
            acoustic_strengths=diagnosis_data.get("acoustic_strengths", ["Consistent vocal energy"]),
            action_roadmap=diagnosis_data.get("action_roadmap", ["Practice diaphragmatic pacing", "Vary pitch on operative words"]),
        )

        flaw_explanations: List[CausalFlawExplanation] = []
        for fe in raw_json.get("flaw_explanations", []):
            flaw_explanations.append(
                CausalFlawExplanation(
                    flaw_id=fe.get("flaw_id", "unknown"),
                    flaw_type=fe.get("flaw_type", "unspecified"),
                    start_time=float(fe.get("start_time", 0.0)),
                    end_time=float(fe.get("end_time", 0.0)),
                    affected_text=fe.get("affected_text", ""),
                    mathematical_cause=fe.get("mathematical_cause", "Acoustic deviation from baseline"),
                    physiological_factor=fe.get("physiological_factor", "Vocal habit"),
                    perceptual_impact=fe.get("perceptual_impact", "Impacts delivery clarity"),
                    remedial_drill=fe.get("remedial_drill", "Practice pacing drill"),
                    confidence=float(fe.get("confidence", 0.95)),
                )
            )

        return ExplanationsResponse(
            analysis_id=analysis_id,
            status="explained",
            diagnosis=diagnosis,
            flaw_explanations=flaw_explanations,
            is_gemini_generated=True,
            message="Causal explanations generated by Gemini 2.0 Flash AI.",
        )

    except Exception as exc:
        logger.warning(f"[{analysis_id}] Gemini causal explanation failed: {exc}. Falling back to deterministic engine.")
        return None


def _deterministic_causal_reasoning(
    flaws: List[Dict[str, Any]],
    comparison: Dict[str, Any],
    features: Dict[str, Any],
    analysis_id: str,
) -> ExplanationsResponse:
    """
    100% deterministic, rule-based mathematical causal reasoning engine.
    Ensures complete explainability even in offline mode.
    """
    pace_comp = comparison.get("pace", {})
    pitch_comp = comparison.get("pitch", {})
    pause_comp = comparison.get("pause", {})
    energy_comp = comparison.get("energy", {})

    delta_wpm = float(pace_comp.get("delta_wpm", 0.0))
    pitch_var_ratio = float(pitch_comp.get("pitch_variation_ratio", 1.0))
    delta_pauses = int(pause_comp.get("delta_pause_count", 0))
    energy_ratio = float(energy_comp.get("energy_ratio", 1.0))

    # 1. Determine Delivery Archetype
    if delta_wpm > 25.0:
        archetype_name = "The High-Velocity Sprinter"
        archetype_summary = (
            f"Delivers content at an accelerated tempo (+{delta_wpm} WPM above baseline). "
            "Exhibits strong enthusiasm but risks syllable compression and clipped phrasing."
        )
        traits = ["Rapid speech tempo", "Occasional phonetic rushing", "Compressed transition pauses"]
    elif pitch_var_ratio < 0.65:
        archetype_name = "The Controlled Analytical Monotone"
        archetype_summary = (
            f"Exhibits steady composure, but vocal melody is restricted ({round(pitch_var_ratio * 100)}% of ideal pitch variation). "
            "Tone sounds overly dry or academic, risking audience disengagement."
        )
        traits = ["Flat fundamental frequency", "Predictable cadence", "Under-modulated key words"]
    elif delta_pauses >= 3:
        archetype_name = "The Hesitant Deliberator"
        archetype_summary = (
            f"Shows thoughtful formulation but is interrupted by frequent pauses (+{delta_pauses} pauses above ideal). "
            "Momentum fluctuates, signaling possible cognitive friction."
        )
        traits = ["Extended formulation gaps", "Uneven speaking rhythm", "Intermittent cadence stops"]
    elif energy_ratio < 0.70:
        archetype_name = "The Reserved Underprojector"
        archetype_summary = (
            "Articulates concepts carefully but vocal projection is subdued (30%+ below reference RMS). "
            "Delivery lacks acoustic authority."
        )
        traits = ["Low subglottic pressure", "Muffled acoustic presence", "Sentence-ending fadeouts"]
    else:
        archetype_name = "The Adaptive Dynamic Communicator"
        archetype_summary = (
            "Demonstrates well-calibrated pacing, expressive prosody, and balanced vocal energy. "
            "Minor isolated opportunities for refinement."
        )
        traits = ["Balanced speaking rate", "Engaging intonation", "Controlled breathing pauses"]

    archetype = DeliveryArchetype(name=archetype_name, summary=archetype_summary, key_traits=traits)

    # 2. Derive Ranked Root Causes
    root_causes: List[str] = []
    if delta_pauses > 2:
        root_causes.append("Cognitive Buffering Latency: Accessing complex vocabulary on-the-fly rather than pre-buffering phrases.")
    if pitch_var_ratio < 0.70:
        root_causes.append("Laryngeal Muscle Tension: Constricted vocal folds suppressing melodic inflection across operative nouns.")
    if abs(delta_wpm) > 20:
        root_causes.append("Pacing Decoupling: Articulation speed decoupled from listener comprehension bandwidth.")
    if energy_ratio < 0.75:
        root_causes.append("Subglottic Pressure Depletion: Shallow chest breathing exhausting air volume prior to phrase completion.")
    if not root_causes:
        root_causes.append("Subtle Cadence Variance: Minor micro-timing fluctuations between phrase boundaries.")
        root_causes.append("Fricative Articulation Balance: Occasional consonant softening on fast transitions.")

    # 3. Identify Mathematically Verified Strengths
    strengths: List[str] = []
    if abs(delta_wpm) <= 15:
        strengths.append(f"Optimal speech tempo calibrated near standard conversational benchmarks ({pace_comp.get('participant_wpm', 130)} WPM).")
    if pitch_var_ratio >= 0.85:
        strengths.append("Expressive melodic prosody with dynamic pitch variations matching ideal reference norms.")
    if pause_comp.get("delta_pause_count", 0) <= 1:
        strengths.append("Controlled cadence without excessive conversational hesitation gaps.")
    if energy_ratio >= 0.80:
        strengths.append("Solid acoustic vocal projection with strong root-mean-square energy support.")
    if not strengths:
        strengths.append("Clear acoustic presence with intelligible core message delivery.")

    # 4. Action Roadmap
    roadmap = [
        "Phase 1 Pacing: Practice the 3-second breathing reset at paragraph transitions to prevent rushed speech.",
        "Phase 2 Pitch Modulation: Apply the 'Staircase Method' — step pitch up by 15-20 Hz on verbs and core takeaways.",
        "Phase 3 Projection Anchor: Sustain diaphragmatic pressure through the final syllable of every sentence.",
    ]

    diagnosis = CausalDiagnosis(
        archetype=archetype,
        top_root_causes=root_causes[:3],
        acoustic_strengths=strengths,
        action_roadmap=roadmap,
    )

    # 5. Build Causal Explanations for Each Flaw
    explanations_list: List[CausalFlawExplanation] = []
    for f in flaws:
        fid = f.get("id", "unknown")
        ftype = f.get("flaw_type", "")
        t_start = float(f.get("start_time", 0.0))
        t_end = float(f.get("end_time", 0.0))
        dur = float(f.get("duration", round(t_end - t_start, 2)))
        text = f.get("affected_text", "")
        ev = f.get("metric_evidence", {})

        if ftype == "excessive_pause":
            math_cause = (
                f"Silence duration of {dur}s exceeds standard reference breath pause ({ev.get('reference_pause_duration', 0.25)}s), "
                f"yielding a {round(dur - ev.get('reference_pause_duration', 0.25), 2)}s acoustic void."
            )
            phys_factor = "Cognitive formulation latency; searching for upcoming phrasing mid-sentence rather than buffering thoughts."
            impact = "Creates psychological dead air that dilutes listener engagement and weakens speaker authority."
            drill = "Pre-Buffering Drill: Train mind to formulate 4 words ahead before opening vocal tract."

        elif ftype == "rushed_transition":
            math_cause = (
                f"Inter-word gap of {dur}s is below the 0.30s phonetic reset requirement for clause boundaries."
            )
            phys_factor = "Breath holding and anticipatory rush; failure to release subglottic tension at punctuation."
            impact = "Listener cognitive overload; ideas collide without time for concept consolidation."
            drill = "Stoplight Drill: Enforce a full deliberate 0.4s silence pause on every comma and period."

        elif ftype == "compressed_syllables":
            math_cause = (
                f"Word duration {dur}s is {ev.get('duration_ratio', 0.5)}× of ideal phoneme duration, below the acoustic clarity threshold."
            )
            phys_factor = "Incomplete lingual contact; tongue and alveolar ridge fail to complete consonant closure."
            impact = "Causes word blur and phonetic clipping, forcing the listener to infer missed syllables."
            drill = "Staccato Articulation Drill: Practice speaking polysyllabic words at 0.75× speed with exaggerated consonant hits."

        elif ftype == "drawn_out_syllable":
            math_cause = (
                f"Word duration of {dur}s is {ev.get('duration_ratio', 1.8)}× longer than standard reference pacing."
            )
            phys_factor = "Involuntary phonatory prolongation while cognitive planning occurs simultaneously."
            impact = "Sounds hesitant or dragging, imparting an impression of doubt."
            drill = "Crisp Release Drill: Release vowel sounds immediately upon syllable stress."

        elif ftype == "monotone_passage":
            math_cause = (
                f"Fundamental frequency variance restricted to {ev.get('participant_f0_std', 5.0)} Hz (vs {ev.get('reference_f0_std', 20.0)} Hz ideal) over {dur}s."
            )
            phys_factor = "Cricothyroid muscle inactivity; vocal folds remain locked at uniform tension throughout speech."
            impact = "Hypnotic or flat acoustic delivery, precipitating rapid audience attention decay."
            drill = "Operative Word Pitch Jump: Pick the most important noun in the sentence and elevate pitch by 2 semitones."

        elif ftype == "trailing_energy_drop":
            math_cause = (
                f"Acoustic RMS energy dropped by {ev.get('drop_percentage', 65)}% across the terminal syllables."
            )
            phys_factor = "Expiratory air depletion; speaker fails to replenish breath prior to long syntactic structures."
            impact = "Sentence endings sound timid, uncertain, or fading away."
            drill = "Tail Anchor Drill: Consciously project the final word 10% louder than the first word."

        elif ftype == "overprojection_burst":
            math_cause = (
                f"Peak RMS energy spiked to {ev.get('peak_rms', 0.1)} ({round(float(ev.get('peak_rms', 0.1)) / max(float(ev.get('mean_rms', 0.04)), 1e-4), 1)}× mean amplitude)."
            )
            phys_factor = "Sudden abdominal push forcing excessive air volume through vocal folds."
            impact = "Sounds harsh or startling on audio playback."
            drill = "Smooth Vocal Attack Exercise: Practice gentle phonation onsets without explosive aspiration."

        else:
            math_cause = f"Acoustic deviation observed during interval {t_start}s–{t_end}s."
            phys_factor = "Habitual speech motor pattern."
            impact = "Subtle distraction from core message clarity."
            drill = "Mirror rehearsal drill with temporal pacing focus."

        explanations_list.append(
            CausalFlawExplanation(
                flaw_id=fid,
                flaw_type=ftype,
                start_time=t_start,
                end_time=t_end,
                affected_text=text,
                mathematical_cause=math_cause,
                physiological_factor=phys_factor,
                perceptual_impact=impact,
                remedial_drill=drill,
                confidence=0.92,
            )
        )

    return ExplanationsResponse(
        analysis_id=analysis_id,
        status="explained",
        diagnosis=diagnosis,
        flaw_explanations=explanations_list,
        is_gemini_generated=False,
        message="Deterministic mathematical causal explanations computed successfully.",
    )


def explain_and_store(db: Session, analysis_id: str) -> ExplanationsResponse:
    """
    Main orchestration entry point:
    1. Loads analysis record.
    2. Ensures flaws_json is present (auto-triggers detect_and_store_flaws if missing).
    3. Attempts Gemini AI structured explanation.
    4. Falls back to deterministic causal engine if Gemini unavailable.
    5. Persists in analysis.explanations_json.
    6. Sets analysis.stage = 'explained'.
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise ValueError(f"Analysis with ID '{analysis_id}' not found.")

    # Auto-detect flaws if not yet present
    if not analysis.flaws_json:
        logger.info(f"[{analysis_id}] Flaws not found in DB. Auto-running flaw detection first.")
        detect_and_store_flaws(db, analysis_id)
        db.refresh(analysis)

    flaws_dict = json.loads(analysis.flaws_json)
    flaws_list = flaws_dict.get("flaws", [])

    comparison_dict = {}
    if analysis.comparison_json:
        try:
            comparison_dict = json.loads(analysis.comparison_json)
        except Exception as exc:
            logger.warning(f"Failed to parse comparison_json: {exc}")

    features_dict = {}
    if analysis.features_json:
        try:
            features_dict = json.loads(analysis.features_json)
        except Exception as exc:
            logger.warning(f"Failed to parse features_json: {exc}")

    transcript = analysis.raw_transcript or ""

    # Attempt Gemini explanation first
    explanations_resp = _generate_gemini_explanations(
        flaws=flaws_list,
        comparison=comparison_dict,
        transcript=transcript,
        analysis_id=analysis_id,
    )

    # Fallback to deterministic causal reasoning if Gemini unavailable
    if not explanations_resp:
        explanations_resp = _deterministic_causal_reasoning(
            flaws=flaws_list,
            comparison=comparison_dict,
            features=features_dict,
            analysis_id=analysis_id,
        )

    # Persist in DB
    analysis.explanations_json = json.dumps(explanations_resp.model_dump())
    analysis.stage = "explained"
    db.commit()
    db.refresh(analysis)

    logger.info(
        f"[{analysis_id}] Causal explanations stored successfully. Archetype: '{explanations_resp.diagnosis.archetype.name}'"
    )
    return explanations_resp
