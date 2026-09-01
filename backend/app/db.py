"""SQLite connection helper. No ORM — plain sqlite3 for the prototype."""

import json
import sqlite3
from pathlib import Path

from app.config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    source_id   TEXT PRIMARY KEY,
    filename    TEXT,
    grain       TEXT,
    cadence     TEXT,
    uploaded_at TEXT
);

CREATE TABLE IF NOT EXISTS profiles (
    source_id   TEXT,
    profile_json TEXT,
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS semantic_contracts (
    source_id     TEXT PRIMARY KEY,
    contract_json TEXT,
    updated_at    TEXT
);

CREATE TABLE IF NOT EXISTS quality_reports (
    source_id    TEXT PRIMARY KEY,
    report_json  TEXT,
    created_at   TEXT
);

CREATE TABLE IF NOT EXISTS canonical_datasets (
    dataset_id       TEXT PRIMARY KEY,
    source_ids       TEXT,
    join_config_json TEXT,
    created_at       TEXT
);

CREATE TABLE IF NOT EXISTS kpis (
    kpi_id   TEXT PRIMARY KEY,
    dataset_id TEXT,
    definition_json TEXT,
    status   TEXT
);

CREATE TABLE IF NOT EXISTS kpi_computations (
    kpi_id          TEXT PRIMARY KEY,
    computation_json TEXT,
    computed_at     TEXT
);

CREATE TABLE IF NOT EXISTS anomalies (
    kpi_id       TEXT,
    anomaly_json TEXT,
    detected_at  TEXT
);

CREATE TABLE IF NOT EXISTS findings (
    finding_id    TEXT PRIMARY KEY,
    kpi_id        TEXT,
    finding_type  TEXT,
    finding_json  TEXT,
    evidence_json TEXT,
    created_at    TEXT
);

CREATE TABLE IF NOT EXISTS personas (
    persona_id TEXT PRIMARY KEY,
    name       TEXT,
    access_json TEXT
);

CREATE TABLE IF NOT EXISTS insights (
    insight_id    TEXT PRIMARY KEY,
    kpi_id        TEXT,
    persona_id    TEXT,
    text          TEXT,
    generated_at  TEXT
);

CREATE TABLE IF NOT EXISTS recommendation_packages (
    package_id   TEXT PRIMARY KEY,
    kpi_id        TEXT,
    package_json TEXT,
    created_at    TEXT
);

CREATE TABLE IF NOT EXISTS llm_calls (
    call_id            TEXT PRIMARY KEY,
    kpi_id             TEXT,
    package_hash       TEXT,
    prompt_tokens      INTEGER,
    completion_tokens  INTEGER,
    latency_ms         INTEGER,
    cost_usd           REAL,
    cached             BOOLEAN,
    created_at         TEXT
);

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id TEXT PRIMARY KEY,
    target_type TEXT,
    target_id   TEXT,
    verdict     TEXT,
    note        TEXT,
    created_at  TEXT
);
"""

# Extended tables (Phase 11): per-stage latency timings, the persisted
# driver-type weight multipliers used by the feedback loop, and feedback
# metadata (the driver type each feedback row targets — the deterministic
# adjustment rule reads it from here, keeping the feedback table's schema
# exactly as the plan specifies).
_SCHEMA = _SCHEMA + """
CREATE TABLE IF NOT EXISTS stage_timings (
    stage        TEXT,
    latency_ms   INTEGER,
    recorded_at  TEXT
);

CREATE TABLE IF NOT EXISTS driver_weight_adjustments (
    driver_type TEXT PRIMARY KEY,
    multiplier  REAL,
    updated_at  TEXT
);

CREATE TABLE IF NOT EXISTS feedback_meta (
    feedback_id TEXT PRIMARY KEY,
    driver_type TEXT,
    created_at  TEXT
);
"""

# Seeded personas (Phase 8): role-based access rules applied by
# core/persona/access_control.filter_for_persona before any response leaves
# the API layer. Rules are generic — column ROLE tags, never specific names.
#   allowed_domains  : dimension domains the persona may see (None = all)
#   restricted_roles : contract column roles hidden from this persona
#   restricted_columns: exact column names hidden from this persona
#   max_slices       : per-dimension slice-detail cap (None = unlimited)
_SEED_PERSONAS = [
    {
        "persona_id": "category_manager",
        "name": "Category Manager",
        "access_json": {
            "description": "Tactical, broad access: every domain, full slice detail.",
            "allowed_domains": None,
            "restricted_roles": [],
            "restricted_columns": [],
            "max_slices": None,
        },
    },
    {
        "persona_id": "cfo",
        "name": "CFO",
        "access_json": {
            "description": (
                "Headline financial view: cost-breakdown and operational-detail "
                "measures hidden, identifier roles restricted, slice detail capped."
            ),
            "allowed_domains": None,
            "restricted_roles": ["identifier"],
            "restricted_columns": [
                "delivery_fee",
                "platform_fee",
                "estimated_delivery_minutes",
                "actual_delivery_minutes",
            ],
            "max_slices": 5,
        },
    },
]


def get_connection() -> sqlite3.Connection:
    """Open a connection to the SQLite database, creating the file/folder if missing.

    Enables foreign keys and row access by name for convenience.
    """
    db_path: Path = settings.DATABASE_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create any needed tables and seed personas if empty. Later phases extend the schema above."""
    conn = get_connection()
    try:
        conn.executescript(_SCHEMA)
        count = conn.execute("SELECT COUNT(*) AS n FROM personas").fetchone()["n"]
        if count == 0:
            for persona in _SEED_PERSONAS:
                conn.execute(
                    "INSERT INTO personas (persona_id, name, access_json) VALUES (?, ?, ?)",
                    (
                        persona["persona_id"],
                        persona["name"],
                        json.dumps(persona["access_json"]),
                    ),
                )
        conn.commit()
    finally:
        conn.close()
