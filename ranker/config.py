"""
config.py — Single source of truth for all scoring parameters.

All weights, thresholds, skill taxonomies, and JD-specific constants
live here. Logic modules never contain hardcoded magic numbers.
"""

from __future__ import annotations

from typing import Dict, FrozenSet

# ---------------------------------------------------------------------------
# Component weights — must sum to 1.0
# ---------------------------------------------------------------------------
COMPONENT_WEIGHTS: Dict[str, float] = {
    "skills":     0.40,
    "career":     0.25,
    "experience": 0.15,
    "signals":    0.15,
    "education":  0.05,
}

# ---------------------------------------------------------------------------
# Availability multiplier applied after base score
# ---------------------------------------------------------------------------
AVAILABILITY_MULTIPLIERS = {
    "fully_available":     1.00,   # open_to_work=True, active ≤60 days
    "partially_available": 0.82,   # either open_to_work or recently active
    "unavailable":         0.65,   # neither open nor recently active
}

RECENCY_THRESHOLD_DAYS = 60       # "recently active" cutoff
RECENCY_STALE_DAYS    = 180       # "very stale" cutoff → hard penalty

# ---------------------------------------------------------------------------
# Skill taxonomy — normalized_name → relevance weight ∈ [0, 1]
#
# Tier 1  (0.90–1.00) : JD must-haves — embeddings, retrieval, ranking, NLP
# Tier 2  (0.70–0.89) : Strong positives — ML frameworks, MLOps, cloud
# Tier 3  (0.40–0.69) : Adjacent / transferable — data engineering, Python infra
# ---------------------------------------------------------------------------
SKILL_TAXONOMY: Dict[str, float] = {
    # ── Retrieval & Search ───────────────────────────────────────────────
    "embeddings":             1.00,
    "vector search":          1.00,
    "semantic search":        1.00,
    "retrieval":              0.95,
    "rag":                    1.00,
    "hybrid search":          0.95,
    "bm25":                   0.85,
    "reranking":              0.95,
    "sentence-transformers":  1.00,
    "information retrieval":  0.90,

    # ── Vector Databases ─────────────────────────────────────────────────
    "milvus":                 1.00,
    "pinecone":               1.00,
    "weaviate":               1.00,
    "qdrant":                 1.00,
    "faiss":                  1.00,
    "elasticsearch":          0.85,
    "opensearch":             0.85,

    # ── Core ML / NLP ────────────────────────────────────────────────────
    "machine learning":       0.95,
    "deep learning":          0.95,
    "nlp":                    1.00,
    "natural language processing": 1.00,
    "transformers":           0.95,
    "bert":                   0.90,
    "fine-tuning llms":       1.00,
    "fine-tuning":            0.90,
    "lora":                   0.90,
    "rlhf":                   0.90,
    "llm":                    0.90,

    # ── ML Frameworks ────────────────────────────────────────────────────
    "pytorch":                0.90,
    "tensorflow":             0.85,
    "keras":                  0.80,
    "scikit-learn":           0.80,
    "hugging face":           0.95,
    "langchain":              0.55,  # JD cautions against pure API-call experience

    # ── Python ───────────────────────────────────────────────────────────
    "python":                 0.95,

    # ── MLOps / Deployment ───────────────────────────────────────────────
    "mlops":                  0.85,
    "bentoml":                0.85,
    "mlflow":                 0.80,
    "weights & biases":       0.80,
    "docker":                 0.65,
    "kubernetes":             0.60,

    # ── Eval / Data Science ──────────────────────────────────────────────
    "feature engineering":    0.75,
    "statistical modeling":   0.75,
    "data science":           0.75,
    "a/b testing":            0.70,
    "ndcg":                   0.85,
    "ranking systems":        0.95,

    # ── Specific Model Types ─────────────────────────────────────────────
    "image classification":   0.70,
    "object detection":       0.70,
    "speech recognition":     0.70,
    "tts":                    0.60,
    "gans":                   0.70,
    "reinforcement learning": 0.70,

    # ── Cloud ─────────────────────────────────────────────────────────────
    "aws":                    0.55,
    "gcp":                    0.55,
    "azure":                  0.55,

    # ── Data Engineering (adjacent) ───────────────────────────────────────
    "sql":                    0.45,
    "apache spark":           0.50,
    "spark":                  0.50,
    "airflow":                0.45,
    "apache beam":            0.50,
    "kafka":                  0.45,
    "databricks":             0.50,
    "dbt":                    0.40,
    "snowflake":              0.40,
    "apache flink":           0.45,
}

# Skills that indicate a non-technical / irrelevant background
IRRELEVANT_SKILLS: FrozenSet[str] = frozenset({
    "photoshop", "illustrator", "indesign", "figma", "sketch", "canva",
    "marketing", "seo", "content writing", "social media", "copywriting",
    "accounting", "bookkeeping", "excel", "powerpoint",
    "payroll", "recruitment",
    "salesforce", "crm",
    "react", "angular", "vue", "tailwind", "css", "html",
    "javascript", "typescript", "node.js", "redux", "graphql", "webpack",
    "solidworks", "autocad", "ansys", "creo",
    "six sigma", "lean", "sap",
})

# ---------------------------------------------------------------------------
# Proficiency level multipliers
# ---------------------------------------------------------------------------
PROFICIENCY_MULTIPLIERS: Dict[str, float] = {
    "expert":       1.00,
    "advanced":     0.85,
    "intermediate": 0.65,
    "beginner":     0.40,
}

# ---------------------------------------------------------------------------
# Career / title relevance
# ---------------------------------------------------------------------------
TITLE_RELEVANCE: Dict[str, float] = {
    # Direct matches
    "ai engineer":                    1.00,
    "ml engineer":                    1.00,
    "machine learning engineer":      1.00,
    "senior machine learning engineer":1.00,
    "junior ml engineer":             0.75,
    "data scientist":                 0.90,
    "senior data scientist":          0.95,
    "research scientist":             0.80,
    "applied scientist":              0.85,
    "nlp engineer":                   0.95,
    "computer vision engineer":       0.80,
    "cv engineer":                    0.80,

    # Technical adjacent
    "backend engineer":               0.55,
    "software engineer":              0.55,
    "senior software engineer":       0.60,
    "analytics engineer":             0.60,
    "data engineer":                  0.60,

    # Non-technical roles
    "business analyst":               0.20,
    "project manager":                0.15,
    "operations manager":             0.10,
    "marketing manager":              0.08,
    "hr manager":                     0.08,
    "accountant":                     0.05,
    "civil engineer":                 0.08,
    "mechanical engineer":            0.08,
    "graphic designer":               0.05,
    "content writer":                 0.08,
    "sales executive":                0.05,
    "customer support":               0.05,
}

# Career history lookback window for relevant past roles
CAREER_HISTORY_LOOKBACK_ROLES = 3     # Consider up to N past roles
RECENT_ROLE_WEIGHT            = 0.60  # Weight for current/most recent role
PAST_ROLE_WEIGHT              = 0.40  # Weight split across other roles

# ---------------------------------------------------------------------------
# Experience parameters — Gaussian bell curve centred at EXPERIENCE_PEAK
# ---------------------------------------------------------------------------
EXPERIENCE_SWEET_SPOT_MIN: float = 4.0
EXPERIENCE_SWEET_SPOT_MAX: float = 10.0
EXPERIENCE_PEAK:           float = 7.0
EXPERIENCE_SIGMA:          float = 3.5  # Standard deviation for Gaussian

# ---------------------------------------------------------------------------
# Education parameters
# ---------------------------------------------------------------------------
EDUCATION_TIER_WEIGHTS: Dict[str, float] = {
    "tier_1": 1.00,
    "tier_2": 0.85,
    "tier_3": 0.70,
    "tier_4": 0.55,
    "unknown": 0.60,
}

RELEVANT_FIELDS: FrozenSet[str] = frozenset({
    "computer science", "machine learning", "artificial intelligence",
    "data science", "information technology", "software engineering",
    "mathematics", "statistics", "electrical engineering",
    "electronics", "computer engineering",
})

# ---------------------------------------------------------------------------
# Behavioral signal weights (within signal_score component)
# ---------------------------------------------------------------------------
SIGNAL_WEIGHTS: Dict[str, float] = {
    "response_rate":         0.25,
    "github_activity":       0.20,
    "recency":               0.15,
    "interview_completion":  0.15,
    "profile_completeness":  0.10,
    "search_visibility":     0.10,
    "notice_period":         0.05,
}

# GitHub score interpretation: -1 means "no GitHub linked"
GITHUB_NOT_LINKED_SCORE: float = 0.20  # Penalty proxy when -1

# Notice period scoring (days → score)
NOTICE_PERIOD_THRESHOLDS = [
    (0,   0.30, 1.00),  # (min_days, max_days_exclusive, score)
    (30,  60,   0.95),
    (60,  90,   0.85),
    (90,  120,  0.70),
    (120, 181,  0.50),
]

# Salary range (INR LPA) that is compatible with this role
SALARY_COMPATIBLE_RANGE = (15, 80)

# ---------------------------------------------------------------------------
# Honeypot detection thresholds
# ---------------------------------------------------------------------------
HONEYPOT_MAX_FRACTION_IRRELEVANT_SKILLS: float = 0.85
HONEYPOT_MIN_COMPLETENESS_FOR_SENIOR:   float = 25.0
HONEYPOT_MAX_YOE_GRAD_GAP:             float = 5.0   # Max plausible gap: yoe > (year - grad_year)
