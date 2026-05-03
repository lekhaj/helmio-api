"""One-shot migration: adds new columns + tables for clarifier/rich-plan features.

Idempotent — safe to re-run. Uses raw SQL because we don't have alembic wired yet.
Run on EC2:  /home/ubuntu/helmio-api/.venv/bin/python -m scripts.migrate_v3
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine, Base
from app import models  # noqa: F401  — register all tables

DDL = [
    # projects: rich context fields
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS vision TEXT DEFAULT ''",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS target_user TEXT DEFAULT ''",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS constraints JSONB DEFAULT '[]'::jsonb",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS what_exists JSONB DEFAULT '[]'::jsonb",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS problems JSONB DEFAULT '[]'::jsonb",
    # projects: stage enum
    """DO $$ BEGIN
        CREATE TYPE projectstage AS ENUM ('idea', 'mvp', 'early_users', 'growth', 'scaling');
    EXCEPTION WHEN duplicate_object THEN null; END $$""",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS stage projectstage DEFAULT 'mvp' NOT NULL",

    # weekly_plans: rich inputs/outputs
    "ALTER TABLE weekly_plans ADD COLUMN IF NOT EXISTS time_available_hours INTEGER DEFAULT 35 NOT NULL",
    "ALTER TABLE weekly_plans ADD COLUMN IF NOT EXISTS blockers JSONB DEFAULT '[]'::jsonb",
    "ALTER TABLE weekly_plans ADD COLUMN IF NOT EXISTS focus_areas JSONB DEFAULT '[]'::jsonb",
    "ALTER TABLE weekly_plans ADD COLUMN IF NOT EXISTS analysis_summary TEXT DEFAULT ''",
    "ALTER TABLE weekly_plans ADD COLUMN IF NOT EXISTS key_gaps JSONB DEFAULT '[]'::jsonb",

    # plan_tasks: daily breakdown + dependencies + outcomes
    "ALTER TABLE plan_tasks ADD COLUMN IF NOT EXISTS day_index INTEGER",
    "ALTER TABLE plan_tasks ADD COLUMN IF NOT EXISTS expected_outcome TEXT DEFAULT ''",
    "ALTER TABLE plan_tasks ADD COLUMN IF NOT EXISTS depends_on JSONB DEFAULT '[]'::jsonb",
    "ALTER TABLE plan_tasks ADD COLUMN IF NOT EXISTS is_handoff BOOLEAN DEFAULT false",
]


def run():
    with engine.begin() as conn:
        for stmt in DDL:
            print(f"→ {stmt[:80]}...")
            conn.execute(text(stmt))
    # let SQLAlchemy create new tables (weekly_metrics, weekly_risks)
    print("→ creating new tables (weekly_metrics, weekly_risks)")
    Base.metadata.create_all(bind=engine)
    print("✓ migration complete")


if __name__ == "__main__":
    run()
