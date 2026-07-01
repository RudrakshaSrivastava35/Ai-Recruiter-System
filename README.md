# Redrob Hackathon — Intelligent Candidate Ranker

> **Redrob Intelligent Candidate Discovery & Ranking Challenge**  
> Ranks a 100K candidate pool against a Senior AI Engineer job description using a
> multi-component, rule-based scoring engine. Runs in **< 60 seconds on CPU** with
> zero third-party dependencies.

---

## Problem Statement

Given a pool of 100,000 candidate profiles (skills, career history, education,
and 23 Redrob behavioral platform signals), identify and rank the **top 100 best-fit
candidates** for a Senior AI Engineer role at Redrob AI (Series A, Pune/Noida, 5–9 yrs).

**Constraints**: CPU-only, ≤ 5 min runtime, ≤ 16 GB RAM, zero network calls during ranking.

---

## Architecture

```
candidates.jsonl (100K records, 487 MB)
        │
        ▼
   ranker/loader.py          ← Streaming JSONL / .gz loader
        │
        ▼
   ranker/scorer.py          ← Orchestrates pipeline
   ┌────┴──────────────────────────────────────────────────────┐
   │                                                            │
   │  components/skill_scorer.py     (weight: 40%)             │
   │  ├─ Taxonomy match (50 AI/ML skills)                      │
   │  ├─ Proficiency multiplier (beginner → expert)            │
   │  ├─ Endorsement + duration bonus                          │
   │  └─ Redrob platform assessment bonus                      │
   │                                                            │
   │  components/career_scorer.py    (weight: 25%)             │
   │  ├─ Title relevance map (AI Eng → 1.0, HR Mgr → 0.08)    │
   │  ├─ Career trajectory with recency decay                  │
   │  └─ Industry + company-size bonus                         │
   │                                                            │
   │  components/experience_scorer.py (weight: 15%)            │
   │  └─ Gaussian bell curve (peak: 7yrs, σ=3.5)              │
   │                                                            │
   │  components/signal_scorer.py    (weight: 15%)             │
   │  ├─ Recruiter response rate (0.25)                        │
   │  ├─ GitHub activity score (0.20)                          │
   │  ├─ Last-active recency (0.15)                            │
   │  ├─ Interview completion rate (0.15)                      │
   │  ├─ Profile completeness (0.10)                           │
   │  ├─ Search visibility (0.10)                              │
   │  └─ Notice period (0.05)                                  │
   │                                                            │
   │  components/education_scorer.py  (weight: 5%)             │
   │  └─ Institution tier + field-of-study bonus               │
   └────────────────────────────────────────────────────────────┘
        │
        ▼  × availability multiplier (0.65 – 1.00)
        │  × honeypot penalty (0.20 if detected)
        │
        ▼
   ranker/reasoning.py        ← Fact-grounded reasoning per top-100
        │
        ▼
   ranker/writer.py           ← Validated submission CSV
        │
        ▼
   submission.csv  ✓
```

---

## Scoring Methodology

### Component Weights

| Component    | Weight | Key Signal |
|:-------------|:------:|:-----------|
| Skills       |  40%   | Taxonomy match against 50 curated AI/ML skills |
| Career       |  25%   | Title relevance + career trajectory |
| Experience   |  15%   | Gaussian bell-curve, peak at 7 years |
| Signals      |  15%   | 7 behavioral signals from Redrob platform |
| Education    |   5%   | Institution tier + relevant field of study |

### Post-Score Multipliers

| Condition | Multiplier |
|:----------|:----------:|
| `open_to_work=True` + active ≤ 60 days | ×1.00 |
| Either flag or recently active | ×0.82 |
| Neither open nor recently active | ×0.65 |
| Honeypot detected | ×0.20 |

### Honeypot Detection (4 independent heuristics)

1. **Timeline impossibility** — YOE > years since graduation + buffer
2. **Date anomaly** — `signup_date` after `last_active_date`
3. **Skill-career mismatch** — overwhelmingly irrelevant skills + senior title
4. **Completeness anomaly** — very low profile completeness for claimed seniority

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO

# No pip install needed — pure Python stdlib
# Place candidates.jsonl in the project root, then:
python rank.py --candidates ./candidates.jsonl --out ./submission.csv

# Validate before submitting
python validate_submission.py submission.csv
```

### Options

```
python rank.py --help

  --candidates PATH   Path to candidates.jsonl or .jsonl.gz  [default: candidates.jsonl]
  --out PATH          Output CSV path                         [default: submission.csv]
  --top-k INT         Number of top candidates to include     [default: 100]
  --log-level LEVEL   DEBUG | INFO | WARNING                  [default: INFO]
```

---

## Project Structure

```
.
├── rank.py                          # CLI entry point
├── ranker/
│   ├── __init__.py
│   ├── config.py                    # All weights, taxonomy, thresholds
│   ├── loader.py                    # Streaming JSONL loader
│   ├── scorer.py                    # Pipeline orchestrator
│   ├── honeypot.py                  # Trap-profile detector
│   ├── reasoning.py                 # Fact-grounded reasoning generator
│   ├── writer.py                    # Submission CSV writer + validator
│   └── components/
│       ├── skill_scorer.py
│       ├── career_scorer.py
│       ├── experience_scorer.py
│       ├── education_scorer.py
│       └── signal_scorer.py
├── validate_submission.py           # Official hackathon format validator
├── candidate_schema.json            # Redrob-provided schema
├── sample_candidates.json           # 50-candidate sample for quick testing
├── submission_metadata.yaml         # Filled submission metadata
├── requirements.txt
└── .gitignore
```

---

## Design Decisions

**Why no embeddings or LLMs?**  
The compute constraint (5 min CPU, no network) rules out any hosted LLM call.
More importantly, the JD explicitly cautions against candidates whose "AI experience"
is purely API calls. The same principle applies to the ranker itself — a well-designed
rule system with explicit, inspectable weights outperforms a black-box LLM call
for a structured tabular ranking task like this.

**Why a Gaussian for experience?**  
Hard cutoffs (e.g., "reject anyone with <4 years") are fragile and miss strong
candidates just outside the bracket. A Gaussian gives a smooth gradient: a
candidate at 4 years scores ~0.85, not 0.0.

**Why an availability multiplier instead of a filter?**  
A great candidate who isn't currently open-to-work may still be the right hire
(they might be persuadable). The multiplier depresses their rank without
eliminating them — the recruiter still sees them, just lower.

---

## Performance

| Metric | Value |
|:-------|:------|
| Dataset | 100,000 candidates, 487 MB |
| Runtime (estimate) | ~30–60 s on modern CPU |
| Memory usage | ~1.5 GB peak |
| Third-party dependencies | **None** (stdlib only) |
| GPU required | No |
| Network calls during ranking | No |

---

## License

MIT
