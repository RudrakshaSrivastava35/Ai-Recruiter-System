"""
education_scorer.py — Scores education quality and field relevance.

Two signals:
  1. Institution tier (tier_1 → tier_4, as provided by Redrob)
  2. Field of study (CS, ML, Statistics, etc. score higher)

If a candidate has multiple degrees, we take the best-scoring one.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ranker.config import EDUCATION_TIER_WEIGHTS, RELEVANT_FIELDS


def _field_bonus(field_of_study: str) -> float:
    """Return 0.15 if the field is directly relevant, else 0.0."""
    normalized = field_of_study.lower().strip()
    for rel_field in RELEVANT_FIELDS:
        if rel_field in normalized or normalized in rel_field:
            return 0.15
    return 0.0


def _degree_score(degree_entry: Dict[str, Any]) -> float:
    """Compute a score for a single degree entry."""
    tier         = degree_entry.get("tier", "unknown")
    field        = degree_entry.get("field_of_study", "")

    tier_weight  = EDUCATION_TIER_WEIGHTS.get(tier, 0.60)
    field_bonus  = _field_bonus(field)

    return min(tier_weight + field_bonus, 1.0)


def score(candidate: Dict[str, Any]) -> float:
    """
    Return an education score in [0, 1].

    Takes the best score across all degrees listed by the candidate.
    Candidates with no education data receive a neutral 0.50 score.
    """
    education: List[Dict[str, Any]] = candidate.get("education", [])

    if not education:
        return 0.50  # No data — neutral rather than penalising

    best_score = max(_degree_score(deg) for deg in education)
    return best_score
