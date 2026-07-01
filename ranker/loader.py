"""
loader.py — Efficient JSONL / gzipped-JSONL / JSON-array candidate loader.

Auto-detects the file format:
  - .jsonl      → one JSON object per line (main dataset)
  - .jsonl.gz   → gzip-compressed JSONL
  - .json       → JSON array (sample_candidates.json, testing)

Streams JSONL line-by-line to avoid loading the full 487 MB into memory.
"""

from __future__ import annotations

import gzip
import json
import logging
from pathlib import Path
from typing import Any, Dict, Generator, List

logger = logging.getLogger(__name__)

Candidate = Dict[str, Any]


def _open_file(path: Path):
    """Return an appropriate file handle for .jsonl, .jsonl.gz, or .json."""
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, "r", encoding="utf-8")


def _is_json_array(path: Path) -> bool:
    """Peek at the first non-whitespace byte to detect a JSON array."""
    with _open_file(path) as fh:
        for char in fh.read(64):
            if char.strip():
                return char == "["
    return False


def stream_candidates(path: Path) -> Generator[Candidate, None, None]:
    """
    Yield one candidate dict at a time, regardless of file format.

    For JSONL files: streams line-by-line (memory-efficient for 100K records).
    For JSON arrays: loads the full array then iterates (used only for small
    sample files — the full dataset is always JSONL).
    """
    if path.suffix == ".json" or _is_json_array(path):
        # JSON array format (e.g. sample_candidates.json)
        with _open_file(path) as fh:
            data = json.load(fh)
        if isinstance(data, list):
            yield from data
        elif isinstance(data, dict):
            yield data
        return

    # JSONL / gzipped JSONL — stream line by line
    with _open_file(path) as fh:
        for line_no, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                yield json.loads(raw)
            except json.JSONDecodeError as exc:
                logger.warning("Skipping malformed JSON at line %d: %s", line_no, exc)


def load_candidates(path: Path) -> List[Candidate]:
    """
    Load all candidates into a list.

    For 100K JSONL records the list fits comfortably within the 16 GB compute
    constraint. Streaming is used so the GC can recover early lines while
    late lines are still being parsed.
    """
    if not path.exists():
        raise FileNotFoundError(f"Candidate file not found: {path}")

    candidates: List[Candidate] = list(stream_candidates(path))
    logger.info("Loaded %d candidate records from %s", len(candidates), path.name)
    return candidates
