"""
signal_scorer.py — Scores the 23 Redrob behavioral platform signals.

Behavioral signals are often more predictive of hireability than the
static profile. A perfect-on-paper candidate who hasn't logged in for
6 months with a 5% recruiter response rate is — for practical hiring
purposes — not actually available.

Sub-components and their weights are defined in config.SIGNAL_WEIGHTS.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict

from ranker.config import (
    GITHUB_NOT_LINKED_SCORE,
    NOTICE_PERIOD_THRESHOLDS,
    RECENCY_STALE_DAYS,
    RECENCY_THRESHOLD_DAYS,
    SIGNAL_WEIGHTS,
)

logger = logging.getLogger(__name__)

_TODAY = date.today()


def _days_since(date_str: str) -> int:
    """Return the number of days between today and a YYYY-MM-DD date string."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (_TODAY - d).days
    except (ValueError, TypeError):
        return 9999  # Treat unparseable dates as very stale


def _recency_score(last_active: str) -> float:
    """Score recency of platform activity on a [0, 1] scale."""
    days = _days_since(last_active)
    if days <= RECENCY_THRESHOLD_DAYS:
        return 1.0
    if days <= RECENCY_STALE_DAYS:
        # Linear decay from 1.0 → 0.50 between threshold and stale
        ratio = (days - RECENCY_THRESHOLD_DAYS) / (RECENCY_STALE_DAYS - RECENCY_THRESHOLD_DAYS)
        return max(1.0 - ratio * 0.50, 0.50)
    # Very stale: linear decay toward 0.10
    ratio = min((days - RECENCY_STALE_DAYS) / 365, 1.0)
    return max(0.50 - ratio * 0.40, 0.10)


def _github_score(raw: float) -> float:
    """Normalise GitHub activity score to [0, 1]; handle -1 (not linked)."""
    if raw < 0:
        return GITHUB_NOT_LINKED_SCORE  # No GitHub is a mild negative signal for AI Eng
    return raw / 100.0


def _notice_period_score(days: int) -> float:
    """Score notice period: shorter is better for quick hiring."""
    for lo, hi, score_val in NOTICE_PERIOD_THRESHOLDS:
        if lo <= days < hi:
            return score_val
    return 0.50  # Fallback


def _search_visibility_score(appearances: int, saved_by: int) -> float:
    """
    Combine search appearances and saved-by-recruiters into a market-
    demand proxy score.  Both signals cap out at reasonable maxima.
    """
    appearance_score = min(appearances / 500.0, 1.0)
    saved_score      = min(saved_by / 20.0, 1.0)
    return 0.6 * appearance_score + 0.4 * saved_score


def score(candidate: Dict[str, Any]) -> float:
    """
    Compute the behavioral signal score for a candidate.

    Returns a normalized score in [0, 1].
    """
    sig: Dict[str, Any] = candidate.get("redrob_signals", {})
    if not sig:
        return 0.30  # No signals → pessimistic default

    sub_scores: Dict[str, float] = {
        "response_rate": float(sig.get("recruiter_response_rate", 0.0)),
        "github_activity": _github_score(float(sig.get("github_activity_score", -1))),
        "recency": _recency_score(sig.get("last_active_date", "")),
        "interview_completion": float(sig.get("interview_completion_rate", 0.0)),
        "profile_completeness": float(sig.get("profile_completeness_score", 0.0)) / 100.0,
        "search_visibility": _search_visibility_score(
            int(sig.get("search_appearance_30d", 0)),
            int(sig.get("saved_by_recruiters_30d", 0)),
        ),
        "notice_period": _notice_period_score(int(sig.get("notice_period_days", 90))),
    }

    weighted = sum(
        SIGNAL_WEIGHTS[key] * val for key, val in sub_scores.items()
    )

    return min(weighted, 1.0)


def availability_multiplier(candidate: Dict[str, Any]) -> float:
    """
    Return an availability multiplier based on open-to-work flag and recency.

    This is applied on top of the base composite score in scorer.py.
    """
    from ranker.config import AVAILABILITY_MULTIPLIERS  # local import to avoid circular

    sig              = candidate.get("redrob_signals", {})
    open_to_work     = bool(sig.get("open_to_work_flag", False))
    days_since_active = _days_since(sig.get("last_active_date", ""))
    recently_active   = days_since_active <= RECENCY_THRESHOLD_DAYS

    if open_to_work and recently_active:
        return AVAILABILITY_MULTIPLIERS["fully_available"]
    if open_to_work or recently_active:
        return AVAILABILITY_MULTIPLIERS["partially_available"]
    return AVAILABILITY_MULTIPLIERS["unavailable"]
