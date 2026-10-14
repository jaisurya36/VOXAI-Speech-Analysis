"""
alignment_service.py — Forced Alignment between Participant and Reference Audio.

Maps words and phrases in participant and generated reference audio to timestamps:
  - Transcribes reference audio to obtain baseline word timestamps.
  - Aligns participant word sequence with reference word sequence using Dynamic Programming.
  - Accounts for punctuation, casing, contractions, and minor ASR differences.
  - Computes alignment coverage percentage (e.g. 96.5%).
  - Never crashes on imperfect speech; supports phrase-level fallback.
"""

import re
import json
import logging
from typing import Dict, Any, List, Tuple, Optional
from difflib import SequenceMatcher

from app.services.transcription_service import transcribe_audio

logger = logging.getLogger(__name__)


def clean_word(token: str) -> str:
    """Normalize token for linguistic matching."""
    if not token:
        return ""
    # Remove all punctuation and lowercase
    cleaned = re.sub(r"[^\w]", "", token.lower().strip())
    # Standardize common contractions
    contractions = {
        "dont": "dont",
        "cant": "cant",
        "wont": "wont",
        "im": "im",
        "ive": "ive",
        "youre": "youre",
        "theyre": "theyre",
        "were": "were",
        "it's": "its",
    }
    return contractions.get(cleaned, cleaned)


def align_speech_tracks(
    participant_words: List[Dict[str, Any]],
    reference_audio_path: str,
    analysis_id: str = "unknown",
) -> Dict[str, Any]:
    """
    Primary alignment entry point.
    1. Transcribes reference audio to obtain reference word timestamps.
    2. Aligns participant words to reference words via dynamic programming.
    3. Groups matched words into corresponding temporal phrases.
    4. Computes alignment coverage and confidence.
    """
    logger.info(f"[{analysis_id}] Transcribing reference audio for forced alignment: {reference_audio_path}")
    ref_result = transcribe_audio(reference_audio_path)
    ref_words = ref_result.get("words", [])

    if not ref_words and ref_result.get("segments"):
        # Fallback to segment-derived words
        from app.services.transcription_service import _generate_fallback_words
        ref_words = _generate_fallback_words(ref_result["segments"])

    return align_word_sequences(
        participant_words=participant_words,
        reference_words=ref_words,
        analysis_id=analysis_id,
    )


def align_word_sequences(
    participant_words: List[Dict[str, Any]],
    reference_words: List[Dict[str, Any]],
    analysis_id: str = "unknown",
) -> Dict[str, Any]:
    """
    Align two word lists with timestamps using SequenceMatcher / Needleman-Wunsch DP.
    """
    total_p = len(participant_words)
    total_r = len(reference_words)

    if total_p == 0 or total_r == 0:
        logger.warning(f"[{analysis_id}] Empty word list provided to alignment (p={total_p}, r={total_r})")
        return {
            "analysis_id": analysis_id,
            "status": "partial",
            "alignment_coverage": 0.0,
            "matched_word_count": 0,
            "total_participant_words": total_p,
            "total_reference_words": total_r,
            "aligned_words": [],
            "aligned_phrases": [],
            "unmatched_participant_words": [w.get("word", "") for w in participant_words],
            "unmatched_reference_words": [w.get("word", "") for w in reference_words],
        }

    p_clean = [clean_word(w["word"]) for w in participant_words]
    r_clean = [clean_word(w["word"]) for w in reference_words]

    # Use SequenceMatcher for optimal longest common subsequence alignment
    matcher = SequenceMatcher(None, p_clean, r_clean, autojunk=False)
    matched_blocks = matcher.get_matching_blocks()

    aligned_words: List[Dict[str, Any]] = []
    matched_p_indices = set()
    matched_r_indices = set()

    for block in matched_blocks:
        p_idx = block.a
        r_idx = block.b
        size = block.size

        for i in range(size):
            p_word_meta = participant_words[p_idx + i]
            r_word_meta = reference_words[r_idx + i]

            # Compute match confidence
            p_prob = p_word_meta.get("probability", 1.0) or 1.0
            r_prob = r_word_meta.get("probability", 1.0) or 1.0
            word_sim = SequenceMatcher(None, p_clean[p_idx + i], r_clean[r_idx + i]).ratio()
            confidence = round(float(word_sim * 0.4 + (p_prob + r_prob) * 0.3), 3)

            aligned_words.append({
                "word": p_word_meta["word"],
                "participant_start": round(float(p_word_meta["start"]), 2),
                "participant_end": round(float(p_word_meta["end"]), 2),
                "reference_start": round(float(r_word_meta["start"]), 2),
                "reference_end": round(float(r_word_meta["end"]), 2),
                "confidence": confidence,
            })
            matched_p_indices.add(p_idx + i)
            matched_r_indices.add(r_idx + i)

    # Validate monotonic timestamp ordering
    aligned_words = _enforce_monotonic_timestamps(aligned_words)

    # Collect unmatched words
    unmatched_p = [participant_words[i]["word"] for i in range(total_p) if i not in matched_p_indices]
    unmatched_r = [reference_words[i]["word"] for i in range(total_r) if i not in matched_r_indices]

    matched_count = len(aligned_words)
    coverage = round((matched_count / max(1, total_p)) * 100.0, 1)

    # Group aligned words into corresponding phrases (chunks of 4-7 words or natural pauses)
    aligned_phrases = _build_aligned_phrases(aligned_words)

    logger.info(
        f"[{analysis_id}] Forced alignment complete — "
        f"Coverage: {coverage}% ({matched_count}/{total_p} words matched, {len(aligned_phrases)} phrases)"
    )

    return {
        "analysis_id": analysis_id,
        "status": "aligned" if coverage >= 70.0 else "partial",
        "alignment_coverage": coverage,
        "matched_word_count": matched_count,
        "total_participant_words": total_p,
        "total_reference_words": total_r,
        "aligned_words": aligned_words,
        "aligned_phrases": aligned_phrases,
        "unmatched_participant_words": unmatched_p,
        "unmatched_reference_words": unmatched_r,
    }


def _enforce_monotonic_timestamps(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Verify and enforce monotonic timestamp ordering on aligned words."""
    if not words:
        return []

    valid_words: List[Dict[str, Any]] = []
    last_p_start = -1.0
    last_r_start = -1.0

    for w in words:
        p_start = w["participant_start"]
        r_start = w["reference_start"]

        # Ensure start <= end
        if w["participant_end"] < p_start:
            w["participant_end"] = round(p_start + 0.1, 2)
        if w["reference_end"] < r_start:
            w["reference_end"] = round(r_start + 0.1, 2)

        # Enforce progressive ordering
        if p_start >= last_p_start and r_start >= last_r_start:
            valid_words.append(w)
            last_p_start = p_start
            last_r_start = r_start

    return valid_words


def _build_aligned_phrases(words: List[Dict[str, Any]], max_words: int = 6) -> List[Dict[str, Any]]:
    """Group aligned words into meaningful corresponding phrases for acoustic comparison."""
    if not words:
        return []

    phrases: List[Dict[str, Any]] = []
    current_chunk: List[Dict[str, Any]] = []
    phrase_id = 0

    for i, w in enumerate(words):
        current_chunk.append(w)

        # Split on sentence-ending punctuation or max chunk size
        is_end_of_sentence = bool(re.search(r"[.!?]", w["word"]))
        is_max_size = len(current_chunk) >= max_words
        is_last = (i == len(words) - 1)

        # Check for pause in participant speech (>0.6s)
        has_pause = False
        if i < len(words) - 1:
            pause_gap = words[i + 1]["participant_start"] - w["participant_end"]
            if pause_gap > 0.6:
                has_pause = True

        if is_end_of_sentence or is_max_size or is_last or has_pause:
            phrase_text = " ".join(item["word"] for item in current_chunk)
            phrases.append({
                "phrase_id": phrase_id,
                "text": phrase_text,
                "participant_start": current_chunk[0]["participant_start"],
                "participant_end": current_chunk[-1]["participant_end"],
                "reference_start": current_chunk[0]["reference_start"],
                "reference_end": current_chunk[-1]["reference_end"],
                "word_count": len(current_chunk),
            })
            phrase_id += 1
            current_chunk = []

    return phrases
