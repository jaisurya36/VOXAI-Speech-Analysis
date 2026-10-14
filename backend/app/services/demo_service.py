"""
demo_service.py — Precomputed Contrastive Demo Dataset & Showcase Seeder.

Provides 4 distinct public speaking contrastive demo speeches:
1. "The Executive Keynote" (Dynamic Orator, Master Tier, Grade A)
2. "The Rapid Pitch" (High-Velocity Sprinter, Competent Tier, Grade C)
3. "The Analytical Monotone" (Controlled Analytical Monotone, Developing Tier, Grade D)
4. "The Deliberate Hesitator" (Deliberate Hesitator, Developing Tier, Grade D)

Generates valid standardized 16kHz mono WAV audio and seeds complete multi-track
analytic records into SQLite for instant, zero-latency one-click showcase.
"""

import os
import math
import wave
import struct
import json
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.schemas.demo import DemoSampleSummary, DemoListResponse, DemoLoadResponse
from app.services.reference_service import _synthesize_with_native_sapi
from app.services.scoring_service import compute_rubric_scores, STANDARD_RUBRIC_TIERS

logger = logging.getLogger(__name__)

DEMO_AUDIO_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "demo"

DEMO_SAMPLES_REGISTRY: Dict[str, Dict[str, Any]] = {
    "demo-keynote": {
        "analysis_id": "11111111-0000-0000-0000-000000000001",
        "sample_id": "demo-keynote",
        "title": "The Executive Keynote",
        "archetype": "The Dynamic Orator",
        "duration": 8.5,
        "sample_rate": 16000,
        "overall_score": 91.5,
        "grade": "A",
        "tier": "Master",
        "description": "Inspiring high-stakes executive keynote speech exhibiting natural cadence, rich prosodic inflection, and zero delivery flaws.",
        "transcript": "Welcome, everyone. Today we are launching a transformative platform that redefines how organizations communicate with precision and impact.",
        "corrected_transcript": "Welcome, everyone. Today we are launching a transformative platform that redefines how organizations communicate with precision and impact.",
        "key_flaws": ["None (Clean prosodic baseline)"],
        "tags": ["Keynote", "Executive", "Master Tier", "Dynamic Prosody"],
        "sapi_rate": 0,
        "comparison": {
            "summary": {
                "overall_similarity_score": 90.7,
                "pace_score": 92.0,
                "pitch_score": 90.0,
                "rhythm_score": 88.0,
                "energy_score": 94.0,
                "timbre_score": 89.0,
                "primary_delivery_flaws": [],
            },
            "pace": {
                "participant_wpm": 138.0,
                "reference_wpm": 136.0,
                "delta_wpm": 2.0,
                "wpm_ratio": 1.01,
                "participant_speaking_duration": 7.4,
                "reference_speaking_duration": 7.5,
                "duration_ratio": 0.99,
                "status": "optimal_tempo",
                "similarity_score": 92.0,
            },
            "pause": {
                "participant_pause_count": 2,
                "reference_pause_count": 2,
                "delta_pause_count": 0,
                "participant_pause_duration": 1.1,
                "reference_pause_duration": 1.0,
                "delta_pause_duration": 0.1,
                "pause_duration_ratio": 1.1,
                "participant_pause_to_speech_ratio": 0.15,
                "reference_pause_to_speech_ratio": 0.13,
                "delta_pause_to_speech": 0.02,
                "status": "balanced_cadence",
                "similarity_score": 88.0,
            },
            "pitch": {
                "participant_mean_f0": 164.2,
                "reference_mean_f0": 162.0,
                "delta_mean_f0": 2.2,
                "participant_std_f0": 28.5,
                "reference_std_f0": 27.0,
                "pitch_variation_ratio": 1.06,
                "participant_range_semitones": 8.4,
                "reference_range_semitones": 8.1,
                "delta_semitones": 0.3,
                "dtw": {"accumulated_cost": 4.2, "normalized_distance": 0.05, "path_length": 85, "sample_path": []},
                "status": "expressive_prosody",
                "similarity_score": 90.0,
            },
            "energy": {
                "participant_mean_rms": 0.068,
                "reference_mean_rms": 0.065,
                "energy_ratio": 1.05,
                "participant_dynamic_range_db": 22.4,
                "reference_dynamic_range_db": 21.8,
                "delta_dynamic_range_db": 0.6,
                "dtw": {"accumulated_cost": 2.1, "normalized_distance": 0.02, "path_length": 85, "sample_path": []},
                "status": "balanced_projection",
                "similarity_score": 94.0,
            },
            "timbre": {
                "mfcc_cosine_distance": 0.06,
                "participant_spectral_centroid": 1840.0,
                "reference_spectral_centroid": 1820.0,
                "delta_spectral_centroid": 20.0,
                "participant_articulation_rate": 4.2,
                "reference_articulation_rate": 4.1,
                "delta_articulation_rate": 0.1,
                "status": "clear_articulation",
                "similarity_score": 89.0,
            },
        },
        "flaws": {
            "summary": {
                "total_flaws": 0,
                "high_severity_count": 0,
                "medium_severity_count": 0,
                "low_severity_count": 0,
                "flaw_density_per_minute": 0.0,
                "flaws_by_category": {},
                "primary_concern": "None — Flawless Delivery Baseline",
            },
            "flaws": [],
        },
        "content_analysis": {
            "grammar": {"score": 95, "errors": []},
            "semantics": {"score": 92, "issues": []},
            "content": {
                "score": 90,
                "strengths": [
                    "Compelling opening with clear strategic thesis.",
                    "High lexical richness and persuasive rhetorical framing.",
                ],
                "weaknesses": [],
                "recommendations": ["Maintain this standard in Q&A sections."],
            },
        },
        "explanations": {
            "diagnosis": {
                "archetype": {
                    "name": "The Dynamic Orator",
                    "summary": "Masterful public speaker exhibiting natural cadence, rich prosodic inflection, and confident resonance.",
                    "key_traits": ["Optimal speaking tempo", "Wide expressive pitch variance", "Natural syntactic pauses"],
                },
                "top_root_causes": ["Consistent diaphragmatic breath support", "Intentional syntactic phrasing"],
                "acoustic_strengths": ["Optimal 138 WPM tempo", "Wide 8.4 semitone dynamic range", "Clean spectral timbre"],
                "action_roadmap": [
                    "Sustain this elite baseline across extended multi-speaker panel settings.",
                    "Incorporate subtle micro-pauses before quantitative claims.",
                    "Maintain open thoracic posture to protect resonance over extended presentations.",
                ],
            },
            "flaw_explanations": [],
            "is_gemini_generated": False,
        },
    },
    "demo-sprinter": {
        "analysis_id": "11111111-0000-0000-0000-000000000002",
        "sample_id": "demo-sprinter",
        "title": "The Rapid Pitch",
        "archetype": "The High-Velocity Sprinter",
        "duration": 5.5,
        "sample_rate": 16000,
        "overall_score": 66.0,
        "grade": "C",
        "tier": "Competent",
        "description": "High-speed startup pitch where vocal velocity outpaces listener comprehension, triggering compressed syllables and rushed transitions.",
        "transcript": "We have developed an unprecedented breakthrough technology specifically engineered to dramatically accelerate enterprise intelligence and productivity without friction.",
        "corrected_transcript": "We have developed an unprecedented breakthrough technology, specifically engineered to dramatically accelerate enterprise intelligence and productivity without friction.",
        "key_flaws": ["Compressed Syllables (-4.0 pts)", "Rushed Transition (-2.0 pts)"],
        "tags": ["Fast Pace", "Compressed Syllables", "Startup Pitch", "Sprinter"],
        "sapi_rate": 3,
        "comparison": {
            "summary": {
                "overall_similarity_score": 68.0,
                "pace_score": 62.0,
                "pitch_score": 75.0,
                "rhythm_score": 60.0,
                "energy_score": 74.0,
                "timbre_score": 70.0,
                "primary_delivery_flaws": ["compressed_syllables", "rushed_transition"],
            },
            "pace": {
                "participant_wpm": 186.0,
                "reference_wpm": 140.0,
                "delta_wpm": 46.0,
                "wpm_ratio": 1.33,
                "participant_speaking_duration": 5.1,
                "reference_speaking_duration": 6.8,
                "duration_ratio": 0.75,
                "status": "rushed",
                "similarity_score": 62.0,
            },
            "pause": {
                "participant_pause_count": 0,
                "reference_pause_count": 2,
                "delta_pause_count": -2,
                "participant_pause_duration": 0.3,
                "reference_pause_duration": 1.2,
                "delta_pause_duration": -0.9,
                "pause_duration_ratio": 0.25,
                "participant_pause_to_speech_ratio": 0.05,
                "reference_pause_to_speech_ratio": 0.18,
                "delta_pause_to_speech": -0.13,
                "status": "insufficient_pauses",
                "similarity_score": 60.0,
            },
            "pitch": {
                "participant_mean_f0": 178.5,
                "reference_mean_f0": 160.0,
                "delta_mean_f0": 18.5,
                "participant_std_f0": 26.0,
                "reference_std_f0": 28.0,
                "pitch_variation_ratio": 0.93,
                "participant_range_semitones": 6.8,
                "reference_range_semitones": 8.0,
                "delta_semitones": -1.2,
                "dtw": {"accumulated_cost": 8.4, "normalized_distance": 0.15, "path_length": 60, "sample_path": []},
                "status": "expressive_prosody",
                "similarity_score": 75.0,
            },
            "energy": {
                "participant_mean_rms": 0.062,
                "reference_mean_rms": 0.064,
                "energy_ratio": 0.97,
                "participant_dynamic_range_db": 18.2,
                "reference_dynamic_range_db": 22.0,
                "delta_dynamic_range_db": -3.8,
                "dtw": {"accumulated_cost": 5.1, "normalized_distance": 0.08, "path_length": 60, "sample_path": []},
                "status": "balanced_projection",
                "similarity_score": 74.0,
            },
            "timbre": {
                "mfcc_cosine_distance": 0.18,
                "participant_spectral_centroid": 2100.0,
                "reference_spectral_centroid": 1800.0,
                "delta_spectral_centroid": 300.0,
                "participant_articulation_rate": 5.8,
                "reference_articulation_rate": 4.3,
                "delta_articulation_rate": 1.5,
                "status": "timbral_deviation",
                "similarity_score": 70.0,
            },
        },
        "flaws": {
            "summary": {
                "total_flaws": 2,
                "high_severity_count": 1,
                "medium_severity_count": 1,
                "low_severity_count": 0,
                "flaw_density_per_minute": 21.8,
                "flaws_by_category": {"pace": 1, "pause": 1},
                "primary_concern": "Elevated speech velocity causing syllable truncation",
            },
            "flaws": [
                {
                    "id": "sprinter-flaw-1",
                    "flaw_type": "compressed_syllables",
                    "category": "pace",
                    "severity": "high",
                    "start_time": 2.1,
                    "end_time": 2.7,
                    "duration": 0.6,
                    "description": "Multi-syllabic words 'specifically engineered' delivered in 0.60s (ratio 0.48x baseline), truncating consonant release.",
                    "affected_text": "specifically engineered",
                    "metric_evidence": {"duration_ratio": 0.48, "measured_duration": 0.60, "reference_duration": 1.25},
                    "suggestion": "Articulate each syllable intentionally. Drill with a metronome at 130 BPM.",
                },
                {
                    "id": "sprinter-flaw-2",
                    "flaw_type": "rushed_transition",
                    "category": "pause",
                    "severity": "medium",
                    "start_time": 3.8,
                    "end_time": 3.9,
                    "duration": 0.1,
                    "description": "Clause boundary between 'technology' and 'specifically' bridged with only 0.10s pause, denying listener cognitive buffering.",
                    "affected_text": "technology specifically",
                    "metric_evidence": {"pause_duration": 0.10, "expected_pause": 0.45},
                    "suggestion": "Insert a 0.5-second deliberate silence at major syntactic clause boundaries.",
                },
            ],
        },
        "content_analysis": {
            "grammar": {"score": 85, "errors": []},
            "semantics": {"score": 82, "issues": [{"text": "unprecedented breakthrough", "issue": "Redundant tautology", "suggestion": "Use either 'unprecedented' or 'breakthrough'"}]},
            "content": {
                "score": 75,
                "strengths": ["High-energy value proposition", "Bold technological positioning"],
                "weaknesses": ["Dense phrasing delivered without sufficient spacing"],
                "recommendations": ["Break complex compound sentence into two concise statements."],
            },
        },
        "explanations": {
            "diagnosis": {
                "archetype": {
                    "name": "The High-Velocity Sprinter",
                    "summary": "Fast-talking speaker driven by urgency and cognitive acceleration, rushing through clause boundaries.",
                    "key_traits": ["186 WPM tempo", "Compressed phonemes", "Suppressed boundary pauses"],
                },
                "top_root_causes": ["Adrenaline-induced motor acceleration", "Fear of losing audience attention"],
                "acoustic_strengths": ["Strong vocal energy projection", "Dynamic articulation drive"],
                "action_roadmap": [
                    "Metronome Pacing Drill: Practice reading at 135 WPM tapping foot on stressed vowels.",
                    "Punctuation Pause Discipline: Force a full 1-second pause after every period.",
                    "Terminal Consonant Release: Ensure word-final 't', 'd', 'k' sounds are fully audible.",
                ],
            },
            "flaw_explanations": [
                {
                    "flaw_id": "sprinter-flaw-1",
                    "flaw_type": "compressed_syllables",
                    "start_time": 2.1,
                    "end_time": 2.7,
                    "affected_text": "specifically engineered",
                    "mathematical_cause": "Phoneme duration ratio collapsed to 0.48x ideal reference.",
                    "physiological_factor": "Rapid mandibular and lingual contact without full vowel formant steady-state formation.",
                    "perceptual_impact": "Listener cognitive load increases dramatically; audience misses key technical differentiators.",
                    "remedial_drill": "Exaggerated Staccato Drill: Pronounce 'spe-ci-fi-cal-ly en-gi-neered' with distinct syllabic beats.",
                    "confidence": 0.95,
                }
            ],
            "is_gemini_generated": False,
        },
    },
    "demo-monotone": {
        "analysis_id": "11111111-0000-0000-0000-000000000003",
        "sample_id": "demo-monotone",
        "title": "The Analytical Monotone",
        "archetype": "The Controlled Analytical Monotone",
        "duration": 9.0,
        "sample_rate": 16000,
        "overall_score": 62.0,
        "grade": "D",
        "tier": "Developing",
        "description": "Technical corporate briefing with low pitch variation and flat prosody, causing audience disengagement despite formal grammatical accuracy.",
        "transcript": "Our quarterly financial projections indicate steady margins across all operational divisions with negligible variance from baseline forecasts.",
        "corrected_transcript": "Our quarterly financial projections indicate steady margins across all operational divisions, with negligible variance from baseline forecasts.",
        "key_flaws": ["Monotone Passage (-4.0 pts)", "Trailing Energy Drop (-2.0 pts)"],
        "tags": ["Monotone", "Flat Pitch", "Corporate Briefing", "Low Inflection"],
        "sapi_rate": -1,
        "comparison": {
            "summary": {
                "overall_similarity_score": 64.0,
                "pace_score": 75.0,
                "pitch_score": 52.0,
                "rhythm_score": 70.0,
                "energy_score": 58.0,
                "timbre_score": 68.0,
                "primary_delivery_flaws": ["monotone_passage", "trailing_energy_drop"],
            },
            "pace": {
                "participant_wpm": 124.0,
                "reference_wpm": 136.0,
                "delta_wpm": -12.0,
                "wpm_ratio": 0.91,
                "participant_speaking_duration": 8.0,
                "reference_speaking_duration": 7.5,
                "duration_ratio": 1.07,
                "status": "slow",
                "similarity_score": 75.0,
            },
            "pause": {
                "participant_pause_count": 1,
                "reference_pause_count": 2,
                "delta_pause_count": -1,
                "participant_pause_duration": 0.8,
                "reference_pause_duration": 1.2,
                "delta_pause_duration": -0.4,
                "pause_duration_ratio": 0.67,
                "participant_pause_to_speech_ratio": 0.10,
                "reference_pause_to_speech_ratio": 0.16,
                "delta_pause_to_speech": -0.06,
                "status": "balanced_cadence",
                "similarity_score": 70.0,
            },
            "pitch": {
                "participant_mean_f0": 132.0,
                "reference_mean_f0": 158.0,
                "delta_mean_f0": -26.0,
                "participant_std_f0": 11.2,
                "reference_std_f0": 26.5,
                "pitch_variation_ratio": 0.42,
                "participant_range_semitones": 3.4,
                "reference_range_semitones": 7.8,
                "delta_semitones": -4.4,
                "dtw": {"accumulated_cost": 12.6, "normalized_distance": 0.22, "path_length": 90, "sample_path": []},
                "status": "monotone",
                "similarity_score": 52.0,
            },
            "energy": {
                "participant_mean_rms": 0.045,
                "reference_mean_rms": 0.065,
                "energy_ratio": 0.69,
                "participant_dynamic_range_db": 14.5,
                "reference_dynamic_range_db": 22.0,
                "delta_dynamic_range_db": -7.5,
                "dtw": {"accumulated_cost": 9.2, "normalized_distance": 0.16, "path_length": 90, "sample_path": []},
                "status": "underprojected",
                "similarity_score": 58.0,
            },
            "timbre": {
                "mfcc_cosine_distance": 0.16,
                "participant_spectral_centroid": 1520.0,
                "reference_spectral_centroid": 1780.0,
                "delta_spectral_centroid": -260.0,
                "participant_articulation_rate": 3.8,
                "reference_articulation_rate": 4.2,
                "delta_articulation_rate": -0.4,
                "status": "clear_articulation",
                "similarity_score": 68.0,
            },
        },
        "flaws": {
            "summary": {
                "total_flaws": 2,
                "high_severity_count": 1,
                "medium_severity_count": 1,
                "low_severity_count": 0,
                "flaw_density_per_minute": 13.3,
                "flaws_by_category": {"pitch": 1, "energy": 1},
                "primary_concern": "Flat fundamental frequency F0 contour across financial statement",
            },
            "flaws": [
                {
                    "id": "monotone-flaw-1",
                    "flaw_type": "monotone_passage",
                    "category": "pitch",
                    "severity": "high",
                    "start_time": 1.5,
                    "end_time": 4.8,
                    "duration": 3.3,
                    "description": "3.30s uninterrupted window with F0 standard deviation of 8.2 Hz (ratio 0.35x reference), inducing listener drowsiness.",
                    "affected_text": "projections indicate steady margins across all operational",
                    "metric_evidence": {"f0_std": 8.2, "threshold": 16.0, "duration": 3.3},
                    "suggestion": "Elevate pitch on stressed words: 'steady', 'margins', and 'operational'.",
                },
                {
                    "id": "monotone-flaw-2",
                    "flaw_type": "trailing_energy_drop",
                    "category": "energy",
                    "severity": "medium",
                    "start_time": 6.8,
                    "end_time": 8.5,
                    "duration": 1.7,
                    "description": "RMS intensity decays by 8.4 dB at sentence termination ('baseline forecasts'), projecting declining conviction.",
                    "affected_text": "from baseline forecasts",
                    "metric_evidence": {"energy_drop_db": 8.4, "threshold_db": 6.0},
                    "suggestion": "Support vocal volume through the final syllable with engaged abdominal breath support.",
                },
            ],
        },
        "content_analysis": {
            "grammar": {"score": 90, "errors": []},
            "semantics": {"score": 85, "issues": []},
            "content": {
                "score": 75,
                "strengths": ["Precise corporate financial vocabulary", "Well-formed declarative syntax"],
                "weaknesses": ["Dense phrasing without dynamic vocal coloring"],
                "recommendations": ["Emphasize key operational takeaways visually and vocally."],
            },
        },
        "explanations": {
            "diagnosis": {
                "archetype": {
                    "name": "The Controlled Analytical Monotone",
                    "summary": "Highly structured and intellectual communicator whose vocal cords maintain uniform tension, flattening prosody.",
                    "key_traits": ["Suppressed pitch range (<4 semitones)", "Trailing energy on sentence ends", "Deliberate pace"],
                },
                "top_root_causes": ["Vocal tension and rigid laryngeal position", "Over-indexing on informational precision over emotional resonance"],
                "acoustic_strengths": ["Steady unhurried tempo", "High grammatical rigor"],
                "action_roadmap": [
                    "Pitch Siren Drill: Glide voice from lowest to highest pitch on vowels to expand vocal tract flexibility.",
                    "Syllable Stepping Drill: Practice deliberately raising pitch 3 semitones on primary nouns.",
                    "Punch the Final Word Drill: Practice sustaining vocal volume through the final period of every sentence.",
                ],
            },
            "flaw_explanations": [
                {
                    "flaw_id": "monotone-flaw-1",
                    "flaw_type": "monotone_passage",
                    "start_time": 1.5,
                    "end_time": 4.8,
                    "affected_text": "projections indicate steady margins across all operational",
                    "mathematical_cause": "F0 standard deviation collapsed to 8.2 Hz across a 3.3-second continuous vocalization.",
                    "physiological_factor": "Cricothyroid muscle inactivity; vocal folds remain in static length and tension.",
                    "perceptual_impact": "Auditory habituation triggers attention dropoff within 4 seconds of speech onset.",
                    "remedial_drill": "The Rollercoaster Pitch Drill: Deliberately arc pitch upward on 'steady' and downward on 'margins'.",
                    "confidence": 0.94,
                }
            ],
            "is_gemini_generated": False,
        },
    },
    "demo-hesitant": {
        "analysis_id": "11111111-0000-0000-0000-000000000004",
        "sample_id": "demo-hesitant",
        "title": "The Deliberate Hesitator",
        "archetype": "The Deliberate Hesitator",
        "duration": 11.0,
        "sample_rate": 16000,
        "overall_score": 58.0,
        "grade": "D",
        "tier": "Developing",
        "description": "Technical presentation hindered by cognitive buffering pauses, filler words, and syllable elongation that interrupt semantic momentum.",
        "transcript": "In this phase we um analyzed the architecture and uh determined that several components require refactoring before deployment.",
        "corrected_transcript": "In this phase, we analyzed the architecture and determined that several components require refactoring before deployment.",
        "key_flaws": ["Excessive Pause (-4.0 pts)", "Drawn-Out Syllable (-2.0 pts)"],
        "tags": ["Hesitations", "Filler Words", "Excessive Pauses", "Developing Tier"],
        "sapi_rate": -2,
        "comparison": {
            "summary": {
                "overall_similarity_score": 58.0,
                "pace_score": 55.0,
                "pitch_score": 68.0,
                "rhythm_score": 45.0,
                "energy_score": 62.0,
                "timbre_score": 65.0,
                "primary_delivery_flaws": ["excessive_pause", "drawn_out_syllable"],
            },
            "pace": {
                "participant_wpm": 98.0,
                "reference_wpm": 135.0,
                "delta_wpm": -37.0,
                "wpm_ratio": 0.73,
                "participant_speaking_duration": 7.5,
                "reference_speaking_duration": 6.8,
                "duration_ratio": 1.10,
                "status": "lethargic",
                "similarity_score": 55.0,
            },
            "pause": {
                "participant_pause_count": 4,
                "reference_pause_count": 2,
                "delta_pause_count": 2,
                "participant_pause_duration": 3.5,
                "reference_pause_duration": 1.1,
                "delta_pause_duration": 2.4,
                "pause_duration_ratio": 3.18,
                "participant_pause_to_speech_ratio": 0.47,
                "reference_pause_to_speech_ratio": 0.16,
                "delta_pause_to_speech": 0.31,
                "status": "excessive_pauses",
                "similarity_score": 45.0,
            },
            "pitch": {
                "participant_mean_f0": 145.0,
                "reference_mean_f0": 155.0,
                "delta_mean_f0": -10.0,
                "participant_std_f0": 22.0,
                "reference_std_f0": 26.0,
                "pitch_variation_ratio": 0.85,
                "participant_range_semitones": 5.8,
                "reference_range_semitones": 7.6,
                "delta_semitones": -1.8,
                "dtw": {"accumulated_cost": 10.5, "normalized_distance": 0.18, "path_length": 80, "sample_path": []},
                "status": "expressive_prosody",
                "similarity_score": 68.0,
            },
            "energy": {
                "participant_mean_rms": 0.052,
                "reference_mean_rms": 0.065,
                "energy_ratio": 0.80,
                "participant_dynamic_range_db": 16.0,
                "reference_dynamic_range_db": 21.0,
                "delta_dynamic_range_db": -5.0,
                "dtw": {"accumulated_cost": 7.8, "normalized_distance": 0.12, "path_length": 80, "sample_path": []},
                "status": "balanced_projection",
                "similarity_score": 62.0,
            },
            "timbre": {
                "mfcc_cosine_distance": 0.20,
                "participant_spectral_centroid": 1650.0,
                "reference_spectral_centroid": 1820.0,
                "delta_spectral_centroid": -170.0,
                "participant_articulation_rate": 3.2,
                "reference_articulation_rate": 4.4,
                "delta_articulation_rate": -1.2,
                "status": "timbral_deviation",
                "similarity_score": 65.0,
            },
        },
        "flaws": {
            "summary": {
                "total_flaws": 2,
                "high_severity_count": 1,
                "medium_severity_count": 1,
                "low_severity_count": 0,
                "flaw_density_per_minute": 10.9,
                "flaws_by_category": {"pause": 1, "pace": 1},
                "primary_concern": "Frequent mid-clause silence gaps and filler vocalizations",
            },
            "flaws": [
                {
                    "id": "hesitant-flaw-1",
                    "flaw_type": "excessive_pause",
                    "category": "pause",
                    "severity": "high",
                    "start_time": 2.2,
                    "end_time": 3.9,
                    "duration": 1.7,
                    "description": "1.70s unnatural silence and vocal hesitation ('um') inside subject-predicate clause boundary.",
                    "affected_text": "we um analyzed",
                    "metric_evidence": {"pause_duration": 1.70, "threshold": 0.85},
                    "suggestion": "Replace verbalized filler buffering with brief 0.3s silent diaphragmatic breath.",
                },
                {
                    "id": "hesitant-flaw-2",
                    "flaw_type": "drawn_out_syllable",
                    "category": "pace",
                    "severity": "medium",
                    "start_time": 5.4,
                    "end_time": 6.3,
                    "duration": 0.9,
                    "description": "Elongated vowel phoneme on 'and uh' lasting 0.90s (ratio 2.4x reference baseline).",
                    "affected_text": "and uh",
                    "metric_evidence": {"duration_ratio": 2.4, "measured_duration": 0.90, "reference_duration": 0.38},
                    "suggestion": "Keep connector conjunctions brief and transition crisply to the operative verb.",
                },
            ],
        },
        "content_analysis": {
            "grammar": {"score": 75, "errors": [{"original": "we um analyzed", "corrected": "we analyzed", "explanation": "Verbal filler 'um' removed"}]},
            "semantics": {"score": 70, "issues": [{"text": "and uh determined", "issue": "Informal speech marker", "suggestion": "Use clean syntactic coordination"}]},
            "content": {
                "score": 65,
                "strengths": ["Clear technical subject matter", "Accurate description of engineering workflow"],
                "weaknesses": ["Cognitive buffering delays rhetorical momentum"],
                "recommendations": ["Rehearse declarative statements as complete verbal units before speaking."],
            },
        },
        "explanations": {
            "diagnosis": {
                "archetype": {
                    "name": "The Deliberate Hesitator",
                    "summary": "Analytical speaker whose cognitive retrieval outpaces verbal articulation, creating noticeable buffer gaps.",
                    "key_traits": ["Long pause durations (>1.5s)", "Elongated filler syllables", "Sub-100 WPM rate"],
                },
                "top_root_causes": ["Online cognitive reformulation during speech output", "Discomfort with brief intentional silence"],
                "acoustic_strengths": ["Clear consonant articulation when vocalizing", "Thoughtful pacing intent"],
                "action_roadmap": [
                    "The Silent Pause Drill: Practice replacing 'um' and 'uh' with closed-mouth silent nasal inhalation.",
                    "Chunking Drill: Group thoughts into 4-word verbal packages delivered without mid-sentence stopping.",
                    "Pace Acceleration Drill: Practice delivery with a 125 WPM metronome to reduce buffer latency.",
                ],
            },
            "flaw_explanations": [
                {
                    "flaw_id": "hesitant-flaw-1",
                    "flaw_type": "excessive_pause",
                    "start_time": 2.2,
                    "end_time": 3.9,
                    "affected_text": "we um analyzed",
                    "mathematical_cause": "Mid-phrase silence gap reached 1.70s exceeding maximum fluent threshold by 200%.",
                    "physiological_factor": "Phonation arrest accompanied by vocal fry as speaker searches for semantic token.",
                    "perceptual_impact": "Listener perceives uncertainty and questions speaker confidence in technical assertions.",
                    "remedial_drill": "The Continuous Breath Flow Drill: Keep airflow moving gently across vocal cords between phrases.",
                    "confidence": 0.93,
                }
            ],
            "is_gemini_generated": False,
        },
    },
}


def _generate_synthetic_speech_wav(
    output_path: Path,
    duration: float,
    sample_rate: int = 16000,
    base_f0: float = 150.0,
    f0_mod_freq: float = 0.5,
    f0_mod_amp: float = 20.0,
    pause_ranges: Optional[List[tuple]] = None,
) -> None:
    """
    Pure Python deterministic speech-like harmonic audio synthesizer.
    Generates rich acoustic speech-like phoneme waveform with modulated fundamental
    and formants (F1, F2, F3) without any external binary dependencies.
    """
    pause_ranges = pause_ranges or []
    total_samples = int(duration * sample_rate)

    formants = [(base_f0, 1.0), (base_f0 * 2.8, 0.45), (base_f0 * 5.2, 0.25)]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)

        frames = bytearray()
        for i in range(total_samples):
            t = i / sample_rate

            # Check if in a pause range
            in_pause = any(start <= t <= end for start, end in pause_ranges)
            if in_pause:
                sample_val = 0
            else:
                # Modulated fundamental F0
                f0 = base_f0 + f0_mod_amp * math.sin(2.0 * math.pi * f0_mod_freq * t)
                # Formant synthesis
                signal = 0.0
                for mult, amp in formants:
                    freq = f0 * (mult / base_f0)
                    signal += amp * math.sin(2.0 * math.pi * freq * t)

                # Envelope windowing
                envelope = 0.8 + 0.2 * math.sin(2.0 * math.pi * 3.5 * t)
                signal *= envelope

                # Clamp to 16-bit signed integer
                sample_val = int(max(-32767, min(32767, signal * 12000.0)))

            frames.extend(struct.pack("<h", sample_val))

        wav_file.writeframes(frames)


def _ensure_sample_audio_files(sample_meta: Dict[str, Any]) -> tuple:
    """
    Ensure the 16kHz mono WAV audio files for participant, reference, and improved exist.
    Tries Windows SAPI first, falling back to pure Python harmonic synthesizer.
    """
    DEMO_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    sample_id = sample_meta["sample_id"]
    participant_wav = DEMO_AUDIO_DIR / f"{sample_id}_participant.wav"
    reference_wav = DEMO_AUDIO_DIR / f"{sample_id}_reference.wav"
    improved_wav = DEMO_AUDIO_DIR / f"{sample_id}_improved.wav"

    script = sample_meta["transcript"]
    corrected = sample_meta["corrected_transcript"]
    duration = float(sample_meta["duration"])

    # Generate participant audio if missing
    if not participant_wav.exists() or participant_wav.stat().st_size < 1000:
        sapi_ok = False
        try:
            _synthesize_with_native_sapi(script, str(participant_wav))
            if participant_wav.exists() and participant_wav.stat().st_size > 1000:
                sapi_ok = True
        except Exception as exc:
            logger.debug(f"SAPI synthesis fallback triggered for {sample_id}: {exc}")

        if not sapi_ok:
            # Deterministic harmonic audio
            base_f0 = 165.0 if "keynote" in sample_id else 175.0 if "sprinter" in sample_id else 130.0 if "monotone" in sample_id else 145.0
            mod_amp = 30.0 if "keynote" in sample_id else 25.0 if "sprinter" in sample_id else 8.0 if "monotone" in sample_id else 18.0
            pauses = [(2.2, 3.9), (5.4, 6.3)] if "hesitant" in sample_id else [(1.5, 2.0)] if "keynote" in sample_id else []
            _generate_synthetic_speech_wav(
                participant_wav,
                duration=duration,
                base_f0=base_f0,
                f0_mod_amp=mod_amp,
                pause_ranges=pauses,
            )

    # Generate reference audio if missing
    if not reference_wav.exists() or reference_wav.stat().st_size < 1000:
        _generate_synthetic_speech_wav(
            reference_wav,
            duration=duration,
            base_f0=160.0,
            f0_mod_amp=26.0,
            pause_ranges=[(duration * 0.45, duration * 0.52)],
        )

    # Generate improved audio if missing
    if not improved_wav.exists() or improved_wav.stat().st_size < 1000:
        _generate_synthetic_speech_wav(
            improved_wav,
            duration=duration,
            base_f0=162.0,
            f0_mod_amp=28.0,
            pause_ranges=[(duration * 0.45, duration * 0.52)],
        )

    return str(participant_wav), str(reference_wav), str(improved_wav)


def get_demo_samples_list() -> DemoListResponse:
    """Return catalog of available contrastive demo speeches."""
    samples = []
    for s_id, s_data in DEMO_SAMPLES_REGISTRY.items():
        summary = DemoSampleSummary(
            sample_id=s_data["sample_id"],
            title=s_data["title"],
            archetype=s_data["archetype"],
            duration=s_data["duration"],
            overall_score=s_data["overall_score"],
            grade=s_data["grade"],
            tier=s_data["tier"],
            description=s_data["description"],
            transcript_preview=s_data["transcript"][:110] + ("..." if len(s_data["transcript"]) > 110 else ""),
            key_flaws=s_data["key_flaws"],
            tags=s_data["tags"],
        )
        samples.append(summary)

    return DemoListResponse(samples=samples, count=len(samples))


def load_demo_sample(db: Session, sample_id: str) -> DemoLoadResponse:
    """
    Load or seed the chosen demo speech into the database with full precomputed analyses:
    Track A acoustic comparisons, Track B content evaluations, temporal flaws,
    causal explanations, and rubric scores.
    Returns analysis_id ready for instant navigation to ResultsPage.
    """
    if sample_id not in DEMO_SAMPLES_REGISTRY:
        raise ValueError(f"Unknown demo sample ID '{sample_id}'. Available: {list(DEMO_SAMPLES_REGISTRY.keys())}")

    meta = DEMO_SAMPLES_REGISTRY[sample_id]
    analysis_id = meta["analysis_id"]

    # Ensure audio files exist on disk
    participant_audio, reference_audio, improved_audio = _ensure_sample_audio_files(meta)

    # Check if analysis already exists in DB
    existing = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not existing:
        # Precompute rubric scores using our mathematical scoring service
        rubric_response = compute_rubric_scores(
            comparison_data=meta["comparison"],
            flaws_data=meta["flaws"],
            content_data=meta["content_analysis"],
            archetype=meta["archetype"],
            analysis_id=analysis_id,
        )

        # Generate synthetic time axis and contours for visual dashboard
        duration = float(meta["duration"])
        steps = int(duration * 20)  # 50ms intervals
        time_axis = [round(i * 0.05, 2) for i in range(steps)]
        f0_base = meta["comparison"]["pitch"]["participant_mean_f0"]
        f0_std = meta["comparison"]["pitch"]["participant_std_f0"]
        rms_base = meta["comparison"]["energy"]["participant_mean_rms"]

        features_data = {
            "time_axis": time_axis,
            "participant_features": {
                "pitch": {
                    "mean_f0": f0_base,
                    "std_f0": f0_std,
                    "contour": [round(f0_base + f0_std * math.sin(i * 0.3), 1) for i in range(steps)],
                },
                "energy": {
                    "mean_rms": rms_base,
                    "contour": [round(max(0.01, rms_base + 0.02 * math.sin(i * 0.2)), 3) for i in range(steps)],
                },
                "rhythm": {
                    "words_per_minute": meta["comparison"]["pace"]["participant_wpm"],
                    "total_duration": duration,
                },
            },
            "reference_features": {
                "pitch": {
                    "mean_f0": meta["comparison"]["pitch"]["reference_mean_f0"],
                    "std_f0": meta["comparison"]["pitch"]["reference_std_f0"],
                    "contour": [round(meta["comparison"]["pitch"]["reference_mean_f0"] + 25.0 * math.sin(i * 0.25), 1) for i in range(steps)],
                },
                "energy": {
                    "mean_rms": meta["comparison"]["energy"]["reference_mean_rms"],
                    "contour": [round(max(0.01, meta["comparison"]["energy"]["reference_mean_rms"] + 0.015 * math.sin(i * 0.15)), 3) for i in range(steps)],
                },
                "rhythm": {
                    "words_per_minute": meta["comparison"]["pace"]["reference_wpm"],
                    "total_duration": duration,
                },
            },
        }

        # Build word timestamps
        words = meta["transcript"].split()
        word_dur = duration / max(1, len(words))
        words_data = [
            {
                "word": w,
                "start": round(i * word_dur, 2),
                "end": round((i + 0.85) * word_dur, 2),
                "probability": 0.98,
            }
            for i, w in enumerate(words)
        ]

        # Create record
        record = Analysis(
            id=analysis_id,
            status="completed",
            stage="scored",
            original_filename=f"{sample_id}.wav",
            input_type="audio",
            duration=duration,
            sample_rate=meta["sample_rate"],
            upload_path=participant_audio,
            analysis_audio_path=participant_audio,
            raw_transcript=meta["transcript"],
            delivery_transcript=meta["transcript"],
            corrected_transcript=meta["corrected_transcript"],
            words_json=json.dumps(words_data),
            segments_json=json.dumps([{"start": 0.0, "end": duration, "text": meta["transcript"]}]),
            content_analysis_json=json.dumps(meta["content_analysis"]),
            reference_audio_path=reference_audio,
            reference_script=meta["transcript"],
            alignment_json=json.dumps({
                "analysis_id": analysis_id,
                "status": "aligned",
                "alignment_coverage": 100.0,
                "total_words_participant": len(words_data),
                "total_words_reference": len(words_data),
                "aligned_words": [
                    {
                        "word": w["word"],
                        "participant_start": w["start"],
                        "participant_end": w["end"],
                        "reference_start": w["start"],
                        "reference_end": w["end"],
                        "match_score": 1.0,
                    }
                    for w in words_data
                ],
                "aligned_phrases": [],
                "message": "Demo forced alignment precomputed successfully.",
            }),
            features_json=json.dumps(features_data),
            comparison_json=json.dumps(meta["comparison"]),
            flaws_json=json.dumps(meta["flaws"]),
            explanations_json=json.dumps(meta["explanations"]),
            scores_json=json.dumps(rubric_response.model_dump()),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        logger.info(f"Demo sample '{sample_id}' seeded successfully with ID {analysis_id}.")
    else:
        # Ensure paths are updated in case storage paths moved
        existing.analysis_audio_path = participant_audio
        existing.reference_audio_path = reference_audio
        existing.improved_audio_path = improved_audio
        if not existing.alignment_json:
            existing.alignment_json = json.dumps({
                "analysis_id": analysis_id,
                "status": "aligned",
                "alignment_coverage": 100.0,
                "total_words_participant": len(meta["transcript"].split()),
                "total_words_reference": len(meta["transcript"].split()),
                "aligned_words": [],
                "aligned_phrases": [],
                "message": "Demo forced alignment precomputed successfully.",
            })
        db.commit()

    return DemoLoadResponse(
        sample_id=sample_id,
        analysis_id=analysis_id,
        status="ready",
        title=meta["title"],
        message=f"Demo sample '{meta['title']}' loaded and ready for analysis.",
    )
