"""
writer.py — Writes and validates the submission CSV.

Enforces the spec from submission_spec.md:
  - Exactly 100 data rows (+ 1 header row)
  - Columns: candidate_id, rank, score, reasoning (in this order)
  - score is monotonically non-increasing with rank
  - Tie-break: candidate_id ascending
  - UTF-8 encoding
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_HEADER    = ["candidate_id", "rank", "score", "reasoning"]
_SCORE_FMT = "{:.4f}"


def _sort_and_rank(results: List[Dict[str, Any]], top_k: int = 100) -> List[Dict[str, Any]]:
    """
    Sort results by score descending; break ties by candidate_id ascending.
    Assign contiguous ranks 1–top_k.

    The validator enforces: for equal scores, candidate_id must be ascending.
    We sort by (-score, candidate_id) which satisfies this exactly.
    """
    ranked = sorted(
        results,
        key=lambda r: (-round(r["score"], 4), r["candidate_id"]),
    )[:top_k]
    for i, r in enumerate(ranked, start=1):
        r["rank"] = i
    return ranked


def write_submission(
    results:  List[Dict[str, Any]],
    out_path: Path,
    top_k:    int = 100,
) -> None:
    """
    Write the ranked results to a submission CSV.

    Parameters
    ----------
    results  : All scored candidates (will be sorted and sliced here).
    out_path : Destination CSV file path.
    top_k    : Number of candidates to write (default: 100).
    """
    ranked = _sort_and_rank(results, top_k)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(_HEADER)
        for r in ranked:
            writer.writerow([
                r["candidate_id"],
                r["rank"],
                _SCORE_FMT.format(r["score"]),
                r.get("reasoning", ""),
            ])

    logger.info(
        "Wrote %d ranked candidates to %s",
        len(ranked),
        out_path,
    )

    _validate_output(ranked)


def _validate_output(ranked: List[Dict[str, Any]]) -> None:
    """
    Run quick sanity checks on the ranked output and log any issues.

    These mirror the checks in validate_submission.py so you catch
    problems before uploading.
    """
    issues: List[str] = []

    if len(ranked) != 100:
        issues.append(f"Expected 100 rows, got {len(ranked)}")

    ranks    = [r["rank"] for r in ranked]
    expected = list(range(1, 101))
    if ranks != expected:
        issues.append(f"Ranks are not 1–100 in order: {ranks[:5]}...")

    # Compare at CSV precision (4 decimal places) to match what the official
    # validator reads. Raw float comparison causes false positives when two
    # candidates have equal 4-decimal scores but differ by < 1e-4 internally.
    scores = [round(r["score"], 4) for r in ranked]
    for i in range(len(scores) - 1):
        if scores[i] < scores[i + 1]:
            issues.append(
                f"Score not non-increasing at rank {i + 1}: "
                f"{scores[i]:.4f} < {scores[i + 1]:.4f}"
            )

    ids = [r["candidate_id"] for r in ranked]
    if len(set(ids)) != len(ids):
        issues.append("Duplicate candidate_ids detected")

    if issues:
        for issue in issues:
            logger.error("Submission validation FAILED: %s", issue)
    else:
        logger.info("Submission validation PASSED — all checks OK")
