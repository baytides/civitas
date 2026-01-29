#!/usr/bin/env python3
"""Background script for comprehensive historical SCOTUS scraping.

This script is designed to run on Carl (Azure VM) overnight to fetch
all Supreme Court cases from 1789 to present using the Court Listener API.

Usage:
    # From the civitas repo root:
    python scripts/scrape_historical_scotus.py

    # Or with options:
    python scripts/scrape_historical_scotus.py --start-year 1900 --db /opt/civitas/civitas.db

    # Run in background with nohup:
    nohup python scripts/scrape_historical_scotus.py > scotus_scrape.log 2>&1 &

Environment Variables:
    COURT_LISTENER_TOKEN: API token for higher rate limits
    DATABASE_URL: Database connection string (or use --db flag)
"""

import argparse
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy.orm import Session

from civitas.db.models import Base, get_engine
from civitas.scotus.case_analyzer import CaseAnalyzer
from civitas.scotus.historical import HistoricalSCOTUSScraper
from civitas.scotus.justices import link_opinions_to_justices, sync_justices
from civitas.scotus.profiles import JusticeProfileGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Scrape comprehensive historical SCOTUS data from Court Listener"
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=1789,
        help="Start year for scraping (default: 1789)",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=None,
        help="End year for scraping (default: current year)",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Database path (default: DATABASE_URL env var or civitas.db)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size per API call (default: 100)",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=0.5,
        help="Seconds between API calls (default: 0.5)",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Run case analysis after scraping",
    )
    parser.add_argument(
        "--analyze-limit",
        type=int,
        default=500,
        help="Max cases to analyze (default: 500)",
    )
    parser.add_argument(
        "--generate-profiles",
        action="store_true",
        help="Regenerate justice profiles after scraping",
    )
    parser.add_argument(
        "--sync-justices",
        action="store_true",
        help="Sync justice metadata before scraping",
    )

    args = parser.parse_args()

    # Determine end year
    end_year = args.end_year or date.today().year

    # Get database connection
    db_url = args.db or os.getenv("DATABASE_URL", "civitas.db")

    logger.info("=" * 60)
    logger.info("HISTORICAL SCOTUS SCRAPER")
    logger.info("=" * 60)
    logger.info(f"Date range: {args.start_year} to {end_year}")
    logger.info(f"Database: {db_url}")
    logger.info(f"Rate limit: {args.rate_limit}s between calls")

    # Check for API token
    api_token = os.getenv("COURT_LISTENER_TOKEN")
    if api_token:
        logger.info("Court Listener API token: SET")
    else:
        logger.warning("No COURT_LISTENER_TOKEN - rate limits will be restricted")
        logger.warning("Get a token at: https://www.courtlistener.com/sign-in/")

    # Initialize database
    engine = get_engine(db_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # Optionally sync justice metadata first
        if args.sync_justices:
            logger.info("\n--- Syncing Justice Metadata ---")
            updated = sync_justices(session)
            session.commit()
            logger.info(f"Updated {updated} justices")

        # Run the scraper
        logger.info("\n--- Starting Historical Scrape ---")
        start_time = datetime.now()

        with HistoricalSCOTUSScraper(
            session=session,
            api_token=api_token,
            rate_limit_delay=args.rate_limit,
            verbose=True,
        ) as scraper:
            # Show initial stats
            initial_stats = scraper.get_stats()
            logger.info(f"Initial DB stats: {initial_stats['total_scotus_cases']} cases")

            # Scrape year by year
            stats = scraper.scrape_year_range(
                start_year=args.start_year,
                end_year=end_year,
                batch_size=args.batch_size,
            )

            # Link any unlinked opinions
            logger.info("\n--- Linking Opinions to Justices ---")
            linked = scraper.link_unlinked_opinions()
            logger.info(f"Linked {linked} additional opinions")

            # Also use the standard linker
            linked2 = link_opinions_to_justices(session)
            session.commit()
            logger.info(f"Standard linker linked {linked2} more opinions")

            # Final stats
            final_stats = scraper.get_stats()

        duration = (datetime.now() - start_time).total_seconds()

        logger.info("\n" + "=" * 60)
        logger.info("SCRAPING COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Cases fetched: {stats.cases_fetched}")
        logger.info(f"Cases inserted: {stats.cases_inserted}")
        logger.info(f"Cases updated: {stats.cases_updated}")
        logger.info(f"Errors: {stats.errors}")
        logger.info(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        logger.info("")
        logger.info("Final database stats:")
        logger.info(f"  Total SCOTUS cases: {final_stats['total_scotus_cases']}")
        logger.info(f"  Cases with author: {final_stats['cases_with_author']}")
        oldest = final_stats['oldest_case_date']
        newest = final_stats['newest_case_date']
        logger.info(f"  Date range: {oldest} to {newest}")

        # Optionally run case analysis
        if args.analyze:
            logger.info("\n--- Running Case Analysis ---")
            analyzer = CaseAnalyzer(session=session)

            case_stats = analyzer.get_case_stats()
            logger.info(f"Cases to analyze: {case_stats['remaining']}")

            if case_stats['remaining'] > 0:
                limit = min(args.analyze_limit, case_stats['remaining'])
                logger.info(f"Analyzing up to {limit} cases...")
                successful, failed = analyzer.analyze_batch(limit=limit, force=False)
                logger.info(f"Analyzed: {successful} successful, {failed} failed")

        # Optionally regenerate justice profiles
        if args.generate_profiles:
            logger.info("\n--- Regenerating Justice Profiles ---")
            generator = JusticeProfileGenerator(session=session)
            created = generator.generate_batch(limit=20, force=True)
            logger.info(f"Generated {created} justice profiles")

    logger.info("\n" + "=" * 60)
    logger.info("ALL TASKS COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
