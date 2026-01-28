#!/usr/bin/env python3
"""Setup PostgreSQL database for Civitas.

This script:
1. Creates the PostgreSQL database and tables
2. Optionally migrates data from SQLite
3. Sets up FTS (if using PostgreSQL full-text search) or maintains SQLite FTS

Usage:
    # Just create tables (empty database)
    python scripts/setup_postgres.py --create

    # Create tables and migrate from SQLite
    python scripts/setup_postgres.py --create --migrate-from civitas.db

    # Just migrate data (tables already exist)
    python scripts/setup_postgres.py --migrate-from civitas.db

Environment Variables:
    DATABASE_URL: PostgreSQL connection string
                  e.g., postgresql://user:pass@localhost:5432/civitas
"""

import argparse
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, text

from civitas.db.models import Base


def create_postgres_database(db_url: str) -> None:
    """Create all tables in PostgreSQL."""
    print("Creating database tables...")

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    print("✓ Database tables created successfully")
    return engine


def setup_postgres_fts(engine) -> None:
    """Set up PostgreSQL full-text search.

    PostgreSQL uses tsvector/tsquery for FTS, which is different from SQLite's FTS5.
    We create GIN indexes on text columns for fast searching.
    """
    print("Setting up PostgreSQL full-text search indexes...")

    with engine.connect() as conn:
        # Create GIN indexes for full-text search on legislation
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_legislation_fts
            ON legislation
            USING GIN (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(summary, '')))
        """))

        # Create GIN indexes for court cases
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_court_cases_fts
            ON court_cases
            USING GIN (to_tsvector('english',
                coalesce(case_name, '') || ' ' || coalesce(holding, '')))
        """))

        # Create GIN indexes for law sections
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_law_sections_fts
            ON law_sections
            USING GIN (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, '')))
        """))

        # Create GIN indexes for P2025 policies
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_p2025_policies_fts
            ON project2025_policies
            USING GIN (to_tsvector('english',
                coalesce(proposal_text, '') || ' '
                || coalesce(proposal_summary, '')))
        """))

        conn.commit()

    print("✓ Full-text search indexes created")


def migrate_from_sqlite(sqlite_path: str, postgres_url: str) -> None:
    """Migrate data from SQLite to PostgreSQL."""

    print(f"Migrating data from {sqlite_path} to PostgreSQL...")

    # Connect to both databases
    sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
    postgres_engine = create_engine(postgres_url)

    # Tables to migrate in order (respecting foreign keys)
    tables = [
        "law_codes",
        "law_sections",
        "legislators",
        "legislation",
        "legislation_versions",
        "legislation_actions",
        "sponsorships",
        "votes",
        "vote_records",
        "court_cases",
        "executive_orders",
        "project2025_policies",
        "p2025_implementations",
        "legal_challenges",
        "state_resistance_actions",
        "resistance_recommendations",
    ]

    with sqlite_engine.connect() as sqlite_conn:
        with postgres_engine.connect() as pg_conn:
            for table in tables:
                try:
                    # Check if table exists in SQLite
                    result = sqlite_conn.execute(text(
                        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
                    ))
                    if not result.fetchone():
                        print(f"  - Skipping {table} (not in SQLite)")
                        continue

                    # Get row count
                    count_result = sqlite_conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = count_result.scalar()

                    if count == 0:
                        print(f"  - Skipping {table} (empty)")
                        continue

                    print(f"  - Migrating {table} ({count} rows)...")

                    # Get all data from SQLite
                    result = sqlite_conn.execute(text(f"SELECT * FROM {table}"))
                    columns = result.keys()
                    rows = result.fetchall()

                    # Clear existing data in PostgreSQL (if any)
                    pg_conn.execute(text(f"DELETE FROM {table}"))

                    # Insert into PostgreSQL
                    for row in rows:
                        row_dict = dict(zip(columns, row))

                        # Handle NULL values and datetime conversion
                        for key, value in row_dict.items():
                            if value == "":
                                row_dict[key] = None

                        # Build INSERT statement
                        cols = ", ".join(row_dict.keys())
                        placeholders = ", ".join([f":{k}" for k in row_dict.keys()])
                        insert_sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"

                        try:
                            pg_conn.execute(text(insert_sql), row_dict)
                        except Exception as e:
                            print(f"    Warning: Error inserting row into {table}: {e}")

                    pg_conn.commit()
                    print(f"    ✓ Migrated {count} rows")

                except Exception as e:
                    print(f"  - Error migrating {table}: {e}")

    print("✓ Migration complete")


def verify_migration(postgres_url: str) -> None:
    """Verify the migration by checking row counts."""
    print("\nVerifying migration...")

    engine = create_engine(postgres_url)

    tables_to_check = [
        "legislation",
        "legislators",
        "court_cases",
        "executive_orders",
        "project2025_policies",
    ]

    with engine.connect() as conn:
        for table in tables_to_check:
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"  - {table}: {count} rows")
            except Exception as e:
                print(f"  - {table}: Error - {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Setup PostgreSQL database for Civitas"
    )
    parser.add_argument(
        "--create",
        action="store_true",
        help="Create database tables"
    )
    parser.add_argument(
        "--migrate-from",
        type=str,
        metavar="SQLITE_PATH",
        help="Path to SQLite database to migrate from"
    )
    parser.add_argument(
        "--database-url",
        type=str,
        help="PostgreSQL connection URL (or set DATABASE_URL env var)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify migration by checking row counts"
    )

    args = parser.parse_args()

    # Get database URL
    db_url = args.database_url or os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: No database URL provided.")
        print("Set DATABASE_URL environment variable or use --database-url")
        print("\nExample:")
        print("  export DATABASE_URL=postgresql://user:pass@localhost:5432/civitas")
        sys.exit(1)

    # Normalize postgres:// to postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    if not db_url.startswith("postgresql://"):
        print("Error: DATABASE_URL must be a PostgreSQL connection string")
        print(f"Got: {db_url[:50]}...")
        sys.exit(1)

    print(f"Database: {db_url.split('@')[1] if '@' in db_url else db_url}")
    print()

    if args.create:
        engine = create_postgres_database(db_url)
        setup_postgres_fts(engine)

    if args.migrate_from:
        if not Path(args.migrate_from).exists():
            print(f"Error: SQLite file not found: {args.migrate_from}")
            sys.exit(1)
        migrate_from_sqlite(args.migrate_from, db_url)

    if args.verify or args.migrate_from:
        verify_migration(db_url)

    if not args.create and not args.migrate_from and not args.verify:
        parser.print_help()


if __name__ == "__main__":
    main()
