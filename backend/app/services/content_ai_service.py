"""
content_ai_service.py — AI Grammar, Semantic & Content Evaluation using Gemini.

Evaluates WHAT the participant said:
  - Grammar & sentence structure
  - Semantic clarity & relevance
  - Content quality, coherence, vocabulary
  - Produces Track B: Corrected / Improved Transcript
  - Provides deterministic offline fallback when GEMINI_API_KEY is not set or API fails
"""

import os
import re
import json
import logging
from typing import Dict, Any, List

from app.config.settings import settings
from app.schemas.content_ai import (
    ContentEvaluationResponse,
    GrammarEvaluation,
    GrammarErrorItem,
    SemanticEvaluation,
    SemanticIssueItem,
    ContentEvaluation,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert speech evaluation and linguistic analysis AI for a professional speech assessment system.
Evaluate WHAT the participant said based on three distinct dimensions:
1. Grammar & Syntax: sentence structure, verb-tense agreement, clause coordination, and grammatical errors.
2. Semantics & Clarity: ambiguity, redundant phrasing, contradictory statements, or unclear expressions.
3. Content & Rhetoric: vocabulary richness, logical flow, persuasiveness, repetition, strengths, and actionable recommendations.

CRITICAL INSTRUCTIONS:
- You must produce Track B: 'corrected_transcript' which is a polished, professional, improved version of the transcript that corrects grammatical errors, enhances clarity, and improves sentence structure while retaining the participant's original core message.
- Scores must be integers between 0 and 100.
- Every deduction must be justified by concrete evidence from the transcript.
- Return ONLY valid JSON adhering strictly to the required schema with no extra text or markdown formatting outside the JSON object.
"""

USER_PROMPT_TEMPLATE = """Analyze the following participant transcript:

\"\"\"
{transcript}
\"\"\"

Produce a JSON response conforming strictly to this structure:
{{
  "corrected_transcript": "<improved, grammatically polished, and rhetorically refined version of the speech>",
  "grammar": {{
    "score": <0-100 integer based on grammatical accuracy>,
    "errors": [
      {{
        "original": "<problematic phrase or sentence from transcript>",
        "corrected": "<grammatically correct version>",
        "explanation": "<specific linguistic reason for correction>"
      }}
    ]
  }},
  "semantics": {{
    "score": <0-100 integer based on semantic clarity and coherence>,
    "issues": [
      {{
        "text": "<vague, redundant, or confusing excerpt>",
        "issue": "<explanation of semantic ambiguity or redundancy>",
        "suggestion": "<clearer phrasing alternative>"
      }}
    ]
  }},
  "content": {{
    "score": <0-100 integer based on vocabulary, logical flow, and depth>,
    "strengths": ["<key rhetorical or topical strength 1>", "<key strength 2>"],
    "weaknesses": ["<content or vocabulary limitation 1>", "<weakness 2>"],
    "recommendations": ["<actionable advice to elevate speech content 1>", "<actionable advice 2>"]
  }}
}}
"""


def evaluate_content(transcript: str, analysis_id: str = "unknown") -> Dict[str, Any]:
    """
    Evaluate transcript using Gemini or fallback to deterministic analyzer.
    Validates output with Pydantic.
    """
    if not transcript or not transcript.strip():
        return _empty_evaluation(analysis_id)

    api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY", "")

    if not api_key:
        logger.info(f"[{analysis_id}] GEMINI_API_KEY not provided. Using deterministic fallback evaluation.")
        return _deterministic_fallback(transcript, analysis_id, "API key not configured.")

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        model_name = settings.gemini_text_model or "gemini-2.0-flash"

        logger.info(f"[{analysis_id}] Sending transcript to Gemini ({model_name})...")
        prompt = USER_PROMPT_TEMPLATE.format(transcript=transcript)

        response = client.models.generate_content(
            model=model_name,
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )

        response_text = response.text.strip()
        # Parse JSON
        parsed_json = json.loads(response_text)

        # Validate with Pydantic
        evaluation = ContentEvaluationResponse(
            analysis_id=analysis_id,
            corrected_transcript=parsed_json.get("corrected_transcript", transcript),
            grammar=GrammarEvaluation(**parsed_json.get("grammar", {"score": 85, "errors": []})),
            semantics=SemanticEvaluation(**parsed_json.get("semantics", {"score": 85, "issues": []})),
            content=ContentEvaluation(**parsed_json.get("content", {"score": 85, "strengths": [], "weaknesses": [], "recommendations": []})),
            is_fallback=False,
            status_message="Evaluated by Gemini AI",
        )
        return evaluation.model_dump()

    except Exception as e:
        logger.warning(f"[{analysis_id}] Gemini API evaluation failed: {e}. Falling back to deterministic analysis.")
        return _deterministic_fallback(transcript, analysis_id, f"Gemini API unavailable: {str(e)}")


def _deterministic_fallback(transcript: str, analysis_id: str, reason: str) -> Dict[str, Any]:
    """
    Deterministic rule-based fallback when Gemini API key is missing or unavailable.
    Guarantees that delivery analysis and pipeline continue smoothly.
    """
    words = transcript.split()
    total_words = len(words)

    # 1. Grammar Heuristics
    grammar_errors: List[GrammarErrorItem] = []
    grammar_score = 100

    # Check for repeated consecutive words ("the the", "that that")
    repeated_words = re.findall(r"\b(\w+)\s+\1\b", transcript, flags=re.IGNORECASE)
    for rep in set(repeated_words):
        grammar_errors.append(
            GrammarErrorItem(
                original=f"{rep} {rep}",
                corrected=rep,
                explanation=f"Duplicated word '{rep}' repeated consecutively.",
            )
        )
        grammar_score -= 5

    # Check for lowercase 'i'
    if re.search(r"\bi\b", transcript):
        grammar_errors.append(
            GrammarErrorItem(
                original="i",
                corrected="I",
                explanation="Standalone pronoun 'I' must always be capitalized.",
            )
        )
        grammar_score -= 4

    # 2. Semantic Heuristics
    semantic_issues: List[SemanticIssueItem] = []
    semantic_score = 100

    filler_words = ["um", "uh", "like", "so basically", "you know", "kind of"]
    for filler in filler_words:
        matches = len(re.findall(r"\b" + re.escape(filler) + r"\b", transcript, flags=re.IGNORECASE))
        if matches > 0:
            semantic_issues.append(
                SemanticIssueItem(
                    text=filler,
                    issue=f"Filler phrase used {matches} time(s), which dilutes message clarity.",
                    suggestion="Replace with a deliberate pause or concise transitional phrase.",
                )
            )
            semantic_score -= min(10, matches * 3)

    # 3. Content Heuristics
    content_strengths = []
    content_weaknesses = []
    content_recommendations = []
    content_score = 80

    if total_words > 30:
        content_strengths.append("Sufficient speech length to establish topical context.")
        content_score += 5
    else:
        content_weaknesses.append("Speech length is relatively brief for in-depth rhetorical analysis.")
        content_recommendations.append("Elaborate on core claims with supporting examples.")
        content_score -= 10

    unique_words = len(set(w.lower() for w in words))
    ttr = (unique_words / max(1, total_words))
    if ttr > 0.65:
        content_strengths.append("High lexical diversity with strong vocabulary variation.")
        content_score += 5
    else:
        content_weaknesses.append("Moderate vocabulary repetition observed.")
        content_recommendations.append("Incorporate more varied synonyms and precise terminology.")

    # Generate a polished corrected transcript
    corrected = transcript.strip()
    corrected = re.sub(r"\s+", " ", corrected)
    for filler in ["um, ", "um ", "uh, ", "uh ", "like, "]:
        corrected = re.sub(r"\b" + re.escape(filler), "", corrected, flags=re.IGNORECASE)
    corrected = re.sub(r"\bi\b", "I", corrected)
    if corrected and corrected[-1] not in ".!?":
        corrected += "."

    grammar_score = max(40, min(100, grammar_score))
    semantic_score = max(40, min(100, semantic_score))
    content_score = max(40, min(100, content_score))

    evaluation = ContentEvaluationResponse(
        analysis_id=analysis_id,
        corrected_transcript=corrected,
        grammar=GrammarEvaluation(score=grammar_score, errors=grammar_errors),
        semantics=SemanticEvaluation(score=semantic_score, issues=semantic_issues),
        content=ContentEvaluation(
            score=content_score,
            strengths=content_strengths or ["Clear speech intent and foundational structure."],
            weaknesses=content_weaknesses or ["Could benefit from stronger structural signposting."],
            recommendations=content_recommendations or ["Expand on supporting arguments and refine vocabulary."],
        ),
        is_fallback=True,
        status_message=f"Deterministic evaluation (Fallback: {reason})",
    )
    return evaluation.model_dump()


def _empty_evaluation(analysis_id: str) -> Dict[str, Any]:
    """Empty evaluation for empty transcripts."""
    return ContentEvaluationResponse(
        analysis_id=analysis_id,
        corrected_transcript="",
        grammar=GrammarEvaluation(score=0, errors=[]),
        semantics=SemanticEvaluation(score=0, issues=[]),
        content=ContentEvaluation(
            score=0,
            strengths=[],
            weaknesses=["No speech content provided."],
            recommendations=["Record or upload a speech sample to evaluate."],
        ),
        is_fallback=True,
        status_message="Empty speech transcript",
    ).model_dump()
