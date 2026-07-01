"""
scorer.py — Orchestrates all scoring components into a final ranked list.

Pipeline for each candidate
----------------------------
1. Run all 5 scoring components independently
2. Compute weighted base score (COMPONENT_WEIGHTS from config)
3. Apply availability multiplier (open_to_work + recency)
4. Apply honeypot penalty if detected
5. Generate reasoning string for top-K results
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from ranker import honeypot as honeypot_detector
from ranker import reasoning as reasoning_builder
from ranker.components import (
    career_scorer,
    education_scorer,
    experience_scorer,
    signal_scorer,
    skill_scorer,
)
from ranker.config import COMPONENT_WEIGHTS

logger = logging.getLogger(__name__)

# Honeypot candidates are ranked near the bottom
_HONEYPOT_PENALTY = 0.20


class CandidateScorer:
    """
    Stateless scorer that processes a list of candidates and returns
    a list of result dicts ready for submission CSV generation.
    """

    def score_one(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score a single candidate and return a result dict.

        Result dict keys
        ----------------
        candidate_id : str
        score        : float   — final composite score in [0, 1]
        components   : dict    — per-component scores (for debugging)
        matched_skills : list  — skills that matched the JD taxonomy
        best_title   : str     — most relevant career title found
        is_honeypot  : bool
        reasoning    : str     — empty string; filled in later for top-K
        profile      : dict    — original profile (reference for reasoning)
        """
        cid = candidate.get("candidate_id", "")

        # ── 1. Component scores ──────────────────────────────────────────
        skill_score, matched_skills = skill_scorer.score(candidate)
        career_score, best_title    = career_scorer.score(candidate)
        exp_score                   = experience_scorer.score(candidate)
        edu_score                   = education_scorer.score(candidate)
        sig_score                   = signal_scorer.score(candidate)

        components = {
            "skills":     skill_score,
            "career":     career_score,
            "experience": exp_score,
            "education":  edu_score,
            "signals":    sig_score,
        }

        # ── 2. Weighted base score ───────────────────────────────────────
        base_score = sum(
            COMPONENT_WEIGHTS[k] * v for k, v in components.items()
        )

        # ── 3. Availability multiplier ───────────────────────────────────
        avail_mult = signal_scorer.availability_multiplier(candidate)
        adjusted   = base_score * avail_mult

        # ── 4. Honeypot detection ────────────────────────────────────────
        flag, _reason = honeypot_detector.is_honeypot(candidate)
        if flag:
            adjusted *= _HONEYPOT_PENALTY

        return {
            "candidate_id":   cid,
            "score":          round(adjusted, 6),
            "components":     components,
            "matched_skills": matched_skills,
            "best_title":     best_title,
            "is_honeypot":    flag,
            "reasoning":      "",         # Populated in score_all for top-K
            "profile":        candidate,  # Reference; not written to CSV
        }

    def score_all(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Score all candidates and attach reasoning for the top-100.

        Returns the full scored list (unsorted). Caller is responsible
        for sorting and slicing to top-K.
        """
        total    = len(candidates)
        results  = []

        for i, cand in enumerate(candidates):
            result = self.score_one(cand)
            results.append(result)

            if (i + 1) % 10_000 == 0:
                logger.info("  Scored %d / %d candidates...", i + 1, total)

        # ── Attach reasoning only for top-100 (saves compute) ───────────
        sorted_results = sorted(results, key=lambda r: (-r["score"], r["candidate_id"]))
        for rank_idx, result in enumerate(sorted_results[:100], start=1):
            result["reasoning"] = reasoning_builder.build(
                candidate     = result["profile"],
                rank          = rank_idx,
                matched_skills= result["matched_skills"],
                best_title    = result["best_title"],
                components    = result["components"],
                is_honeypot_flag = result["is_honeypot"],
            )

        if not sorted_results:
            logger.warning("No candidates were scored — check that the input file loaded correctly.")
            return results
        logger.info("Scoring complete. Top candidate score: %.4f", sorted_results[0]["score"])
        return results
