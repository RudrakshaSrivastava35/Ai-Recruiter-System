#!/usr/bin/env python3
"""
rank.py — CLI entry point for the Redrob Hackathon candidate ranker.

Usage
-----
    python rank.py --candidates ./candidates.jsonl --out ./submission.csv

Compute constraints (per submission_spec.md Section 3)
------------------------------------------------------
    Runtime  : ≤ 5 minutes CPU
    Memory   : ≤ 16 GB RAM
    Compute  : CPU only (no GPU)
    Network  : Offline (no API calls during ranking)
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from ranker.loader import load_candidates
from ranker.scorer import CandidateScorer
from ranker.writer import write_submission

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

_COMPUTE_LIMIT_SECONDS = 300  # 5 minutes per spec


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rank candidates from candidates.jsonl for the Redrob Senior AI Engineer JD.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--candidates",
        type=Path,
        default=Path("candidates.jsonl"),
        help="Path to candidates file (.jsonl or .jsonl.gz)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("submission.csv"),
        help="Output CSV file path",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=100,
        help="Number of top candidates to include in submission",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    logging.getLogger().setLevel(args.log_level)
    t_start = time.perf_counter()

    # ── Load ──────────────────────────────────────────────────────────────
    logger.info("Loading candidates from: %s", args.candidates)
    t0 = time.perf_counter()
    candidates = load_candidates(args.candidates)
    logger.info("Loaded %d candidates in %.2fs", len(candidates), time.perf_counter() - t0)

    # ── Score ─────────────────────────────────────────────────────────────
    logger.info("Scoring all candidates...")
    t1 = time.perf_counter()
    scorer  = CandidateScorer()
    results = scorer.score_all(candidates)
    logger.info("Scoring complete in %.2fs", time.perf_counter() - t1)

    # ── Write ─────────────────────────────────────────────────────────────
    write_submission(results, args.out, top_k=args.top_k)

    elapsed = time.perf_counter() - t_start
    logger.info("Total elapsed: %.2fs", elapsed)

    if elapsed > _COMPUTE_LIMIT_SECONDS:
        logger.error(
            "Runtime %.1fs exceeds the %ds compute limit! "
            "Submission may be disqualified at Stage 3.",
            elapsed,
            _COMPUTE_LIMIT_SECONDS,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
