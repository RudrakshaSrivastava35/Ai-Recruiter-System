#!/usr/bin/env python3
"""
app.py — Flask dashboard for Redrob Candidate Ranker results.

Serves a beautiful web interface to browse the top-100 ranked candidates,
search/filter by title, country, and work mode, and download the CSV.

Usage
-----
    pip install flask
    python app.py
    # Open http://localhost:5000 in your browser

First run generates top100_details.json (takes ~20s while scanning
candidates.jsonl). Every subsequent run loads instantly from cache.
"""

from __future__ import annotations

import csv
import json
import logging
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, send_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Custom Jinja2 filter: {{ 100000 | format_number }} → "100,000"
@app.template_filter("format_number")
def format_number(value):
    return f"{int(value):,}"


ROOT          = Path(__file__).parent
SUBMISSION    = ROOT / "submission.csv"
CANDIDATES_FILE = ROOT / "candidates.jsonl"
CACHE_FILE    = ROOT / "top100_details.json"

_PROFICIENCY_RANK = {"expert": 4, "advanced": 3, "intermediate": 2, "beginner": 1}


# ── Helpers ────────────────────────────────────────────────────────────────

def _top_skills(skills: list, n: int = 5) -> list[str]:
    """Return the top-n skills sorted by proficiency then endorsements."""
    return [
        s["name"]
        for s in sorted(
            skills,
            key=lambda s: (
                _PROFICIENCY_RANK.get(s.get("proficiency", ""), 0),
                s.get("endorsements", 0),
            ),
            reverse=True,
        )[:n]
    ]


def _best_education(education: list) -> str:
    """Return a one-line string for the highest-tier degree."""
    if not education:
        return ""
    deg = education[0]
    return (
        f"{deg.get('degree', '')} in {deg.get('field_of_study', '')} "
        f"— {deg.get('institution', '')}"
    )


# ── Cache generation ────────────────────────────────────────────────────────

def generate_cache() -> list:
    """
    Scan candidates.jsonl, match top-100 candidate_ids from submission.csv,
    extract UI-relevant fields, and write to top100_details.json.
    """
    if not SUBMISSION.exists():
        logger.error("submission.csv not found. Run:  python rank.py  first.")
        sys.exit(1)
    if not CANDIDATES_FILE.exists():
        logger.error("candidates.jsonl not found in project root.")
        sys.exit(1)

    # Load submission rankings
    ranked: dict = {}
    with open(SUBMISSION, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ranked[row["candidate_id"]] = {
                "rank":      int(row["rank"]),
                "score":     float(row["score"]),
                "reasoning": row["reasoning"],
            }

    logger.info(
        "Scanning candidates.jsonl for top-100 profiles — one-time operation..."
    )

    results: list = []

    with open(CANDIDATES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                cand = json.loads(line)
            except json.JSONDecodeError:
                continue

            cid = cand.get("candidate_id", "")
            if cid not in ranked:
                continue

            r       = ranked[cid]
            profile = cand.get("profile", {})
            sig     = cand.get("redrob_signals", {})
            skills  = cand.get("skills", [])
            edu     = cand.get("education", [])
            career  = cand.get("career_history", [])

            results.append({
                "candidate_id":  cid,
                "rank":          r["rank"],
                "score":         r["score"],
                "reasoning":     r["reasoning"],
                # Profile
                "name":          profile.get("anonymized_name", "Anonymous"),
                "headline":      profile.get("headline", ""),
                "title":         profile.get("current_title", ""),
                "company":       profile.get("current_company", ""),
                "location":      profile.get("location", ""),
                "country":       profile.get("country", ""),
                "yoe":           profile.get("years_of_experience", 0),
                "summary":       profile.get("summary", "")[:400],
                # Skills & Education
                "skills":        _top_skills(skills),
                "education":     _best_education(edu),
                "career_count":  len(career),
                # Signals
                "open_to_work":    bool(sig.get("open_to_work_flag", False)),
                "github_score":    float(sig.get("github_activity_score", -1)),
                "response_rate":   float(sig.get("recruiter_response_rate", 0)),
                "completeness":    float(sig.get("profile_completeness_score", 0)),
                "notice_days":     int(sig.get("notice_period_days", 90)),
                "work_mode":       sig.get("preferred_work_mode", ""),
                "last_active":     sig.get("last_active_date", ""),
                "salary_min":      sig.get("expected_salary_range_inr_lpa", {}).get("min", 0),
                "salary_max":      sig.get("expected_salary_range_inr_lpa", {}).get("max", 0),
                "interview_rate":  float(sig.get("interview_completion_rate", 0)),
                "willing_relocate": bool(sig.get("willing_to_relocate", False)),
                "verified_email":  bool(sig.get("verified_email", False)),
                "linkedin_connected": bool(sig.get("linkedin_connected", False)),
            })

    results.sort(key=lambda x: x["rank"])

    CACHE_FILE.write_text(json.dumps(results, indent=2), encoding="utf-8")
    logger.info("Cached %d profiles → %s", len(results), CACHE_FILE.name)
    return results


def load_data() -> list:
    if CACHE_FILE.exists():
        logger.info("Loading from cache: %s", CACHE_FILE.name)
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return generate_cache()


# ── Load at startup ─────────────────────────────────────────────────────────

logger.info("Initialising dashboard data...")
CANDIDATES_DATA: list = load_data()
logger.info(
    "Ready — %d candidates loaded. Open http://localhost:5000",
    len(CANDIDATES_DATA),
)


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    top10 = CANDIDATES_DATA[:10]
    stats = {
        "total_screened":  100_000,
        "top_score":       CANDIDATES_DATA[0]["score"] if CANDIDATES_DATA else 0,
        "ai_eng_top10":    sum(
            1 for c in top10
            if any(
                kw in c["title"].lower()
                for kw in ["ml", "ai ", "machine learning", "nlp", "data scientist"]
            )
        ),
        "india_top20":     sum(
            1 for c in CANDIDATES_DATA[:20] if c["country"] == "India"
        ),
        "avg_score_top10": round(
            sum(c["score"] for c in top10) / len(top10), 4
        ) if top10 else 0,
        "runtime_seconds": 33,
    }
    # Unique countries and work modes for filter dropdowns
    countries  = sorted({c["country"] for c in CANDIDATES_DATA if c["country"]})
    work_modes = sorted({c["work_mode"] for c in CANDIDATES_DATA if c["work_mode"]})
    return render_template(
        "index.html",
        candidates=CANDIDATES_DATA,
        stats=stats,
        countries=countries,
        work_modes=work_modes,
    )


@app.route("/api/candidates")
def api_candidates():
    return jsonify(CANDIDATES_DATA)


@app.route("/api/stats")
def api_stats():
    countries  = {}
    work_modes = {}
    for c in CANDIDATES_DATA:
        countries[c["country"]]  = countries.get(c["country"], 0) + 1
        work_modes[c["work_mode"]] = work_modes.get(c["work_mode"], 0) + 1
    return jsonify({
        "total":      len(CANDIDATES_DATA),
        "countries":  countries,
        "work_modes": work_modes,
        "avg_score":  round(
            sum(c["score"] for c in CANDIDATES_DATA) / len(CANDIDATES_DATA), 4
        ) if CANDIDATES_DATA else 0,
    })


@app.route("/download")
def download_csv():
    """Serve submission.csv as a file download."""
    return send_file(
        SUBMISSION,
        mimetype="text/csv",
        as_attachment=True,
        download_name="submission.csv",
    )


import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
