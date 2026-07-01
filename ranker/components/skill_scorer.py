"""
skill_scorer.py — Scores a candidate's skills against the JD skill taxonomy.

Algorithm
---------
For each skill in the candidate's profile:
  1. Normalize the skill name (lowercase, strip)
  2. Look it up in the taxonomy (exact match, then substring match)
  3. Multiply taxonomy weight × proficiency multiplier
  4. Apply an endorsement bonus and a duration bonus
  5. Store the best match for each taxonomy slot (avoid double-counting)

Final score is the sum of matched skill scores, normalized to [0, 1]
by dividing by the theoretical maximum for a perfect profile.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from ranker.config import (
    IRRELEVANT_SKILLS,
    PROFICIENCY_MULTIPLIERS,
    SKILL_TAXONOMY,
)

logger = logging.getLogger(__name__)

# Pre-build a lookup: normalized_name → weight (for O(1) exact lookups)
_TAXONOMY_NORMALIZED: Dict[str, float] = {k.lower(): v for k, v in SKILL_TAXONOMY.items()}


def _taxonomy_weight(skill_name: str) -> float:
    """
    Return the taxonomy weight for a skill name.

    First tries exact match, then checks whether any taxonomy key is a
    substring of the skill name or vice versa (catches "Apache Spark"
    matching "spark", "NLP" matching "natural language processing", etc.).
    Returns 0.0 if no match is found.
    """
    normalized = skill_name.lower().strip()

    # 1. Exact match
    if normalized in _TAXONOMY_NORMALIZED:
        return _TAXONOMY_NORMALIZED[normalized]

    # 2. Substring match: taxonomy key inside skill name
    best = 0.0
    for key, weight in _TAXONOMY_NORMALIZED.items():
        if key in normalized or normalized in key:
            best = max(best, weight)

    return best


def _endorsement_bonus(endorsements: int) -> float:
    """Map endorsement count to a small multiplier bonus."""
    if endorsements >= 50:
        return 1.20
    if endorsements >= 11:
        return 1.10
    if endorsements >= 1:
        return 1.00
    return 0.90  # No endorsements — slight discount


def _duration_bonus(duration_months: int) -> float:
    """Map usage duration (months) to a multiplier reflecting depth of experience."""
    if duration_months >= 48:
        return 1.20
    if duration_months >= 24:
        return 1.10
    if duration_months >= 12:
        return 1.00
    if duration_months >= 6:
        return 0.90
    return 0.80


def _assessment_bonus(skill_name: str, assessment_scores: Dict[str, float]) -> float:
    """
    If the candidate completed a Redrob platform assessment for this skill,
    return a bonus multiplier based on their score.
    """
    normalized = skill_name.lower()
    for assessed_skill, score in assessment_scores.items():
        if assessed_skill.lower() == normalized or normalized in assessed_skill.lower():
            # Score is 0–100; convert to a multiplier in [0.90, 1.30]
            return 0.90 + (score / 100) * 0.40
    return 1.00  # No assessment → neutral


def score(candidate: Dict[str, Any]) -> Tuple[float, List[str]]:
    """
    Compute the skill score for a candidate.

    Returns
    -------
    score : float
        Normalized skill score in [0, 1].
    matched_skills : List[str]
        Names of the candidate's skills that matched the taxonomy (for reasoning).
    """
    skills: List[Dict[str, Any]] = candidate.get("skills", [])
    assessment_scores: Dict[str, float] = (
        candidate.get("redrob_signals", {}).get("skill_assessment_scores", {})
    )

    if not skills:
        return 0.0, []

    total_skill_score  = 0.0
    matched_skills: List[str] = []
    irrelevant_count   = 0

    for skill_entry in skills:
        skill_name  = skill_entry.get("name", "")
        proficiency = skill_entry.get("proficiency", "beginner")
        endorsements = int(skill_entry.get("endorsements", 0))
        duration_months = int(skill_entry.get("duration_months", 0))

        tax_weight = _taxonomy_weight(skill_name)

        if tax_weight == 0.0:
            if skill_name.lower().strip() in IRRELEVANT_SKILLS:
                irrelevant_count += 1
            continue  # No contribution to skill score

        prof_mult  = PROFICIENCY_MULTIPLIERS.get(proficiency, 0.40)
        endorse_b  = _endorsement_bonus(endorsements)
        duration_b = _duration_bonus(duration_months)
        assess_b   = _assessment_bonus(skill_name, assessment_scores)

        contribution = tax_weight * prof_mult * endorse_b * duration_b * assess_b
        total_skill_score += contribution
        matched_skills.append(skill_name)

    # Theoretical max: 10 skills all at weight=1.0, expert, 50+ endorsements,
    # 48+ months, 100% assessment. Multipliers: 1.0 × 1.0 × 1.2 × 1.2 × 1.3 = 1.872
    theoretical_max = 10 * 1.0 * 1.0 * 1.20 * 1.20 * 1.30  # ≈ 18.72

    normalized = min(total_skill_score / theoretical_max, 1.0)

    # Penalize profiles dominated by irrelevant skills
    if skills:
        irrelevant_fraction = irrelevant_count / len(skills)
        normalized *= max(0.0, 1.0 - irrelevant_fraction * 0.4)

    return normalized, matched_skills
