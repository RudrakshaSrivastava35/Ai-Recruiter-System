"""
career_scorer.py — Scores career trajectory relevance to the JD.

Scoring logic
-------------
- Current / most recent role carries the highest weight
- Past roles (up to CAREER_HISTORY_LOOKBACK_ROLES) contribute with decay
- Industry relevance provides a secondary signal
- Total career score = weighted average of per-role title relevance
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from ranker.config import (
    CAREER_HISTORY_LOOKBACK_ROLES,
    PAST_ROLE_WEIGHT,
    RECENT_ROLE_WEIGHT,
    TITLE_RELEVANCE,
)

logger = logging.getLogger(__name__)

# Industries that are positively correlated with AI/ML product companies
_RELEVANT_INDUSTRIES = {
    "software", "technology", "it services", "saas", "fintech",
    "edtech", "healthtech", "ai", "machine learning", "data",
    "e-commerce", "internet", "cloud",
}

_LARGE_COMPANY_BONUS = 0.05   # Big tech implies higher engineering bar


def _title_score(title: str) -> float:
    """
    Return the relevance score for a job title.

    Tries exact match first, then partial/substring matching.
    Falls back to 0.05 (neutral noise) for unrecognised titles.
    """
    normalized = title.lower().strip()

    if normalized in TITLE_RELEVANCE:
        return TITLE_RELEVANCE[normalized]

    # Substring match: pick best match among known titles
    best = 0.05
    for known_title, weight in TITLE_RELEVANCE.items():
        if known_title in normalized or normalized in known_title:
            best = max(best, weight)

    return best


def _industry_bonus(industry: str) -> float:
    """Return a small bonus for relevant industries."""
    normalized = industry.lower()
    for rel in _RELEVANT_INDUSTRIES:
        if rel in normalized:
            return 0.05
    return 0.0


def _company_size_bonus(company_size: str) -> float:
    """Reward larger companies (stronger engineering culture signal)."""
    if company_size in {"1001-5000", "5001-10000", "10001+"}:
        return _LARGE_COMPANY_BONUS
    return 0.0


def score(candidate: Dict[str, Any]) -> Tuple[float, str]:
    """
    Compute the career trajectory score for a candidate.

    Returns
    -------
    score : float
        Career score in [0, 1].
    top_title : str
        The most relevant title found (for reasoning output).
    """
    career_history: List[Dict[str, Any]] = candidate.get("career_history", [])
    current_title: str = candidate.get("profile", {}).get("current_title", "")

    if not career_history:
        # Fall back to profile headline title only
        return _title_score(current_title), current_title

    # Sort: current role first, then most-recent by start_date
    sorted_history = sorted(
        career_history,
        key=lambda r: (not r.get("is_current", False), r.get("start_date", "0000")),
        reverse=True,
    )

    roles_to_consider = sorted_history[: CAREER_HISTORY_LOOKBACK_ROLES]
    n = len(roles_to_consider)

    weighted_score = 0.0
    weight_sum     = 0.0

    # First role gets RECENT_ROLE_WEIGHT; rest share PAST_ROLE_WEIGHT
    role_weights = [RECENT_ROLE_WEIGHT] + (
        [PAST_ROLE_WEIGHT / max(n - 1, 1)] * (n - 1) if n > 1 else []
    )

    best_title = current_title
    best_title_score = 0.0

    for role, w in zip(roles_to_consider, role_weights):
        title    = role.get("title", "")
        industry = role.get("industry", "")
        company_size = role.get("company_size", "")

        ts = _title_score(title)
        ts = min(ts + _industry_bonus(industry) + _company_size_bonus(company_size), 1.0)

        weighted_score += ts * w
        weight_sum     += w

        if ts > best_title_score:
            best_title_score = ts
            best_title = title

    raw_score = weighted_score / weight_sum if weight_sum > 0 else 0.0
    return min(raw_score, 1.0), best_title
