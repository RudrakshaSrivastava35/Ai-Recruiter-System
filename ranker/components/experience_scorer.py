"""
experience_scorer.py — Bell-curve scoring for years of experience.

The JD targets 5–9 years ("what we mean by this" section is explicit).
We model this as a Gaussian centred at EXPERIENCE_PEAK with a standard
deviation of EXPERIENCE_SIGMA, giving a smooth score rather than a hard
bracket cutoff.
"""

from __future__ import annotations

import math
from typing import Any, Dict

from ranker.config import (
    EXPERIENCE_PEAK,
    EXPERIENCE_SIGMA,
    EXPERIENCE_SWEET_SPOT_MAX,
    EXPERIENCE_SWEET_SPOT_MIN,
)


def _gaussian(x: float, mu: float, sigma: float) -> float:
    """Standard Gaussian, normalised so peak = 1.0."""
    return math.exp(-0.5 * ((x - mu) / sigma) ** 2)


def score(candidate: Dict[str, Any]) -> float:
    """
    Return an experience score in [0, 1].

    Candidates within [EXPERIENCE_SWEET_SPOT_MIN, EXPERIENCE_SWEET_SPOT_MAX]
    score near-linearly by how close they are to EXPERIENCE_PEAK.
    Very junior (<2y) and very senior (>15y) candidates receive lower scores,
    but are never scored at 0 — they may still contribute to other dimensions.
    """
    yoe: float = float(candidate.get("profile", {}).get("years_of_experience", 0))
    yoe = max(0.0, yoe)

    return _gaussian(yoe, EXPERIENCE_PEAK, EXPERIENCE_SIGMA)
