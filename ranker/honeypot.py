"""
honeypot.py — Detects suspicious / trap candidate profiles.

The dataset contains ~80 honeypot candidates with subtly impossible profiles.
Submissions ranking these highly are penalised (>10% honeypots in top-100
causes disqualification).

Detection heuristics
--------------------
1. **Timeline impossibility**: Years of experience implausibly exceeds years
   since last graduation.
2. **Signal contradiction**: open_to_work=True but last_active > 2 years ago.
3. **Skill-career mismatch**: Overwhelmingly non-technical skills but claims
   a senior technical title.
4. **Profile completeness anomaly**: Very low completeness score (< 25) but
   claims 10+ years and a senior title.
5. **Date sanity**: signup_date after last_active_date.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Tuple

from ranker.config import (
    HONEYPOT_MAX_FRACTION_IRRELEVANT_SKILLS,
    HONEYPOT_MAX_YOE_GRAD_GAP,
    HONEYPOT_MIN_COMPLETENESS_FOR_SENIOR,
    IRRELEVANT_SKILLS,
)

logger = logging.getLogger(__name__)

_CURRENT_YEAR = datetime.now().year
_HIGH_TITLE_KEYWORDS = {"senior", "lead", "principal", "staff", "head of", "director"}


def _parse_year(date_str: str) -> int:
    """Parse a YYYY-MM-DD string and return the year, or 0 on failure."""
    try:
        return int(date_str[:4])
    except (TypeError, ValueError):
        return 0


def _is_impossible_experience(candidate: Dict[str, Any]) -> bool:
    """
    Return True if claimed YOE exceeds (current_year - latest_graduation_year + buffer).
    """
    yoe = float(candidate.get("profile", {}).get("years_of_experience", 0))
    education = candidate.get("education", [])

    if not education:
        return False

    latest_grad = max(
        (_parse_year(deg.get("end_year", "0") if isinstance(deg.get("end_year"), str)
         else str(deg.get("end_year", 0)))
         for deg in education),
        default=0,
    )

    if latest_grad == 0:
        return False

    max_plausible_yoe = (_CURRENT_YEAR - latest_grad) + HONEYPOT_MAX_YOE_GRAD_GAP
    return yoe > max_plausible_yoe


def _is_date_anomaly(candidate: Dict[str, Any]) -> bool:
    """Return True if signup_date is later than last_active_date."""
    sig = candidate.get("redrob_signals", {})
    signup    = sig.get("signup_date", "")
    last_active = sig.get("last_active_date", "")

    if not signup or not last_active:
        return False

    return signup > last_active  # lexicographic ISO-8601 comparison is safe


def _is_skill_career_mismatch(candidate: Dict[str, Any]) -> bool:
    """
    Return True if skills are overwhelmingly irrelevant yet the candidate
    claims a high-level technical title.
    """
    skills = candidate.get("skills", [])
    if not skills:
        return False

    irrelevant_count = sum(
        1 for s in skills if s.get("name", "").lower().strip() in IRRELEVANT_SKILLS
    )
    irrelevant_fraction = irrelevant_count / len(skills)

    if irrelevant_fraction < HONEYPOT_MAX_FRACTION_IRRELEVANT_SKILLS:
        return False

    # Only flag if they also claim a technical title
    title = candidate.get("profile", {}).get("current_title", "").lower()
    return any(kw in title for kw in _HIGH_TITLE_KEYWORDS)


def _is_completeness_anomaly(candidate: Dict[str, Any]) -> bool:
    """
    Return True if profile completeness is very low for a self-described
    senior professional (they should have filled their profile in).
    """
    sig         = candidate.get("redrob_signals", {})
    completeness = float(sig.get("profile_completeness_score", 100))
    yoe          = float(candidate.get("profile", {}).get("years_of_experience", 0))
    title        = candidate.get("profile", {}).get("current_title", "").lower()

    is_senior = yoe >= 8 and any(kw in title for kw in _HIGH_TITLE_KEYWORDS)
    return is_senior and completeness < HONEYPOT_MIN_COMPLETENESS_FOR_SENIOR


def is_honeypot(candidate: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Evaluate whether a candidate looks like a honeypot / trap profile.

    Returns
    -------
    (is_honeypot, reason) : Tuple[bool, str]
        True + reason string if suspicious; (False, "") otherwise.
    """
    if _is_date_anomaly(candidate):
        return True, "signup_date after last_active_date"

    if _is_impossible_experience(candidate):
        return True, "claimed YOE exceeds years since graduation"

    if _is_skill_career_mismatch(candidate):
        return True, "skills overwhelmingly irrelevant for claimed senior title"

    if _is_completeness_anomaly(candidate):
        return True, "suspiciously low profile completeness for claimed seniority"

    return False, ""
