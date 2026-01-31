"""Temporal activities and workflows for Bay Navigator.

Bay Navigator is a community resources directory for the Bay Area.
This module provides Temporal orchestration for:
- External data ingestion (211, transit, parks, benefits, etc.)
- Civic data scraping (city councils from multiple platforms)
- Data validation and quality checks
- API generation pipeline
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

# Bay Navigator project root (configurable via env)
BAYNAVIGATOR_ROOT = os.getenv("BAYNAVIGATOR_ROOT", "/opt/baynavigator")


@dataclass
class ScriptResult:
    """Result of running a Node.js script."""

    script: str
    success: bool
    stdout: str
    stderr: str
    duration_seconds: float
    exit_code: int


@dataclass
class BatchScriptResult:
    """Result of running multiple scripts."""

    total_scripts: int
    successful: int
    failed: int
    results: list[ScriptResult]
    errors: list[str]


# Retry policies
SCRAPER_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=30),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=10),
    maximum_attempts=3,
)

API_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=10),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=5),
    maximum_attempts=2,
)


def run_node_script(script_name: str, timeout_seconds: int = 300) -> ScriptResult:
    """Run a Node.js script from the Bay Navigator scripts directory.

    Args:
        script_name: Name of the script (e.g., "generate-api.cjs")
        timeout_seconds: Maximum execution time

    Returns:
        ScriptResult with output and status
    """
    import time

    script_path = Path(BAYNAVIGATOR_ROOT) / "scripts" / script_name
    start = time.time()

    try:
        result = subprocess.run(
            ["node", str(script_path)],
            cwd=BAYNAVIGATOR_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env={**os.environ, "NODE_ENV": "production"},
        )

        duration = time.time() - start
        return ScriptResult(
            script=script_name,
            success=result.returncode == 0,
            stdout=result.stdout[-5000:] if result.stdout else "",  # Limit output
            stderr=result.stderr[-2000:] if result.stderr else "",
            duration_seconds=duration,
            exit_code=result.returncode,
        )

    except subprocess.TimeoutExpired:
        duration = time.time() - start
        return ScriptResult(
            script=script_name,
            success=False,
            stdout="",
            stderr=f"Script timed out after {timeout_seconds}s",
            duration_seconds=duration,
            exit_code=-1,
        )
    except Exception as e:
        duration = time.time() - start
        return ScriptResult(
            script=script_name,
            success=False,
            stdout="",
            stderr=str(e),
            duration_seconds=duration,
            exit_code=-1,
        )


# =============================================================================
# Data Ingestion Activities
# =============================================================================


@activity.defn
async def sync_transit_data() -> ScriptResult:
    """Sync Bay Area transit data from 511.org API."""
    activity.heartbeat("Syncing 511 transit data...")
    return run_node_script("sync-511-transit.cjs", timeout_seconds=600)


@activity.defn
async def sync_open_data_cache() -> ScriptResult:
    """Sync open data from Bay Area city portals (Socrata)."""
    activity.heartbeat("Syncing open data portals...")
    return run_node_script("sync-open-data-cache.cjs", timeout_seconds=900)


@activity.defn
async def sync_nps_parks() -> ScriptResult:
    """Sync National Parks Service data."""
    activity.heartbeat("Syncing NPS parks...")
    return run_node_script("sync-nps-parks.cjs", timeout_seconds=300)


@activity.defn
async def sync_recreation_gov() -> ScriptResult:
    """Sync Recreation.gov campgrounds and sites."""
    activity.heartbeat("Syncing Recreation.gov...")
    return run_node_script("sync-recreation-gov.cjs", timeout_seconds=600)


@activity.defn
async def sync_imls_museums() -> ScriptResult:
    """Sync IMLS museum data."""
    activity.heartbeat("Syncing IMLS museums...")
    return run_node_script("sync-imls-museums.cjs", timeout_seconds=300)


@activity.defn
async def sync_usagov_benefits() -> ScriptResult:
    """Sync federal benefits from USA.gov."""
    activity.heartbeat("Syncing USA.gov benefits...")
    return run_node_script("sync-usagov-benefits.cjs", timeout_seconds=300)


@activity.defn
async def sync_california_codes() -> ScriptResult:
    """Sync California legislative codes (large operation)."""
    activity.heartbeat("Syncing California codes...")
    return run_node_script("sync-california-codes.cjs", timeout_seconds=1800)


@activity.defn
async def sync_throughline_helplines() -> ScriptResult:
    """Sync crisis helplines from Throughline."""
    activity.heartbeat("Syncing helplines...")
    return run_node_script("sync-throughline-helplines.cjs", timeout_seconds=300)


@activity.defn
async def fetch_carbon_stats() -> ScriptResult:
    """Fetch carbon statistics."""
    activity.heartbeat("Fetching carbon stats...")
    return run_node_script("fetch-carbon-stats.cjs", timeout_seconds=300)


# =============================================================================
# Civic Scraping Activities (City Councils)
# =============================================================================


@activity.defn
async def scrape_211_bayarea() -> ScriptResult:
    """Scrape 211 Bay Area resources."""
    activity.heartbeat("Scraping 211 Bay Area...")
    return run_node_script("scrape-211bayarea.cjs", timeout_seconds=1200)


@activity.defn
async def scrape_civicplus_councils() -> ScriptResult:
    """Scrape city councils from CivicPlus platform (~45 cities)."""
    activity.heartbeat("Scraping CivicPlus councils...")
    return run_node_script("scrape-civicplus-councils.cjs", timeout_seconds=1800)


@activity.defn
async def scrape_granicus_councils() -> ScriptResult:
    """Scrape city councils from Granicus/OpenCities (~12 cities)."""
    activity.heartbeat("Scraping Granicus councils...")
    return run_node_script("scrape-granicus-councils.cjs", timeout_seconds=900)


@activity.defn
async def scrape_proudcity_councils() -> ScriptResult:
    """Scrape city councils from ProudCity/WordPress (~9 cities)."""
    activity.heartbeat("Scraping ProudCity councils...")
    return run_node_script("scrape-proudcity-councils.cjs", timeout_seconds=600)


@activity.defn
async def scrape_legistar_councils() -> ScriptResult:
    """Scrape city councils from Legistar."""
    activity.heartbeat("Scraping Legistar councils...")
    return run_node_script("scrape-legistar-councils.cjs", timeout_seconds=600)


@activity.defn
async def scrape_wikipedia_councils() -> ScriptResult:
    """Scrape city councils from Wikipedia (fallback source)."""
    activity.heartbeat("Scraping Wikipedia councils...")
    return run_node_script("scrape-wikipedia-councils.cjs", timeout_seconds=600)


@activity.defn
async def scrape_blocked_councils() -> ScriptResult:
    """Scrape blocked/custom city sites (Playwright, slow)."""
    activity.heartbeat("Scraping blocked councils (Playwright)...")
    return run_node_script("scrape-blocked-councils.cjs", timeout_seconds=2400)


@activity.defn
async def consolidate_scraped_data() -> ScriptResult:
    """Consolidate all scraped civic data."""
    activity.heartbeat("Consolidating scraped data...")
    return run_node_script("consolidate-scraped-data.cjs", timeout_seconds=300)


# =============================================================================
# Validation Activities
# =============================================================================


@activity.defn
async def validate_data() -> ScriptResult:
    """Run schema and referential integrity validation."""
    activity.heartbeat("Validating data...")
    return run_node_script("validate-data.cjs", timeout_seconds=120)


@activity.defn
async def check_duplicates() -> ScriptResult:
    """Check for duplicate programs."""
    activity.heartbeat("Checking duplicates...")
    return run_node_script("check-duplicates.cjs", timeout_seconds=60)


@activity.defn
async def validate_links() -> ScriptResult:
    """Validate all external links (slow, parallel)."""
    activity.heartbeat("Validating links...")
    return run_node_script("validate-links.cjs", timeout_seconds=1800)


@activity.defn
async def check_data_freshness() -> ScriptResult:
    """Check data staleness."""
    activity.heartbeat("Checking data freshness...")
    return run_node_script("check-data-freshness.cjs", timeout_seconds=60)


@activity.defn
async def validate_map_coordinates() -> ScriptResult:
    """Validate geographic coordinates."""
    activity.heartbeat("Validating map coordinates...")
    return run_node_script("validate-map-coordinates.cjs", timeout_seconds=120)


# =============================================================================
# API Generation Activities
# =============================================================================


@activity.defn
async def generate_api() -> ScriptResult:
    """Generate main JSON API from YAML data."""
    activity.heartbeat("Generating API...")
    return run_node_script("generate-api.cjs", timeout_seconds=120)


@activity.defn
async def generate_geojson() -> ScriptResult:
    """Generate GeoJSON for maps."""
    activity.heartbeat("Generating GeoJSON...")
    return run_node_script("generate-geojson.cjs", timeout_seconds=120)


@activity.defn
async def generate_search_index() -> ScriptResult:
    """Generate Fuse.js search index."""
    activity.heartbeat("Generating search index...")
    return run_node_script("generate-search-index.cjs", timeout_seconds=120)


@activity.defn
async def generate_simple_language() -> ScriptResult:
    """Generate simple language descriptions (AI-powered)."""
    activity.heartbeat("Generating simple language...")
    return run_node_script("generate-simple-language-descriptions.cjs", timeout_seconds=900)


@activity.defn
async def generate_city_contacts_api() -> ScriptResult:
    """Generate city contacts API."""
    activity.heartbeat("Generating city contacts API...")
    return run_node_script("generate-city-contacts-api.cjs", timeout_seconds=120)


# =============================================================================
# Workflows
# =============================================================================


@workflow.defn
class BayNavigatorFullSyncWorkflow:
    """Complete Bay Navigator data synchronization.

    Runs all data ingestion, validation, and API generation.
    """

    @workflow.run
    async def run(self, include_civic_scraping: bool = False) -> BatchScriptResult:
        """Run full sync pipeline.

        Args:
            include_civic_scraping: If True, also run civic council scraping
        """
        results: list[ScriptResult] = []
        errors: list[str] = []

        workflow.logger.info("Starting Bay Navigator full sync")

        # Phase 1: Data ingestion (parallel where possible)
        ingestion_activities = [
            (sync_transit_data, "transit"),
            (sync_open_data_cache, "open-data"),
            (sync_nps_parks, "nps"),
            (sync_usagov_benefits, "benefits"),
            (sync_throughline_helplines, "helplines"),
        ]

        ingestion_handles = []
        for activity_fn, name in ingestion_activities:
            workflow.logger.info(f"Starting {name} ingestion")
            handle = workflow.start_activity(
                activity_fn,
                start_to_close_timeout=timedelta(hours=1),
                retry_policy=API_RETRY_POLICY,
                heartbeat_timeout=timedelta(minutes=5),
            )
            ingestion_handles.append((name, handle))

        for name, handle in ingestion_handles:
            try:
                result = await handle
                results.append(result)
                if not result.success:
                    errors.append(f"{name}: {result.stderr}")
            except Exception as e:
                errors.append(f"{name} failed: {e!s}")

        # Phase 2: Civic scraping (if enabled, sequential due to rate limits)
        if include_civic_scraping:
            civic_activities = [
                (scrape_civicplus_councils, "civicplus"),
                (scrape_granicus_councils, "granicus"),
                (scrape_proudcity_councils, "proudcity"),
                (scrape_legistar_councils, "legistar"),
                (scrape_wikipedia_councils, "wikipedia"),
            ]

            for activity_fn, name in civic_activities:
                workflow.logger.info(f"Scraping {name} councils")
                try:
                    result = await workflow.execute_activity(
                        activity_fn,
                        start_to_close_timeout=timedelta(hours=1),
                        retry_policy=SCRAPER_RETRY_POLICY,
                        heartbeat_timeout=timedelta(minutes=10),
                    )
                    results.append(result)
                    if not result.success:
                        errors.append(f"{name}: {result.stderr}")
                except Exception as e:
                    errors.append(f"{name} failed: {e!s}")

            # Consolidate civic data
            try:
                result = await workflow.execute_activity(
                    consolidate_scraped_data,
                    start_to_close_timeout=timedelta(minutes=30),
                    retry_policy=API_RETRY_POLICY,
                )
                results.append(result)
            except Exception as e:
                errors.append(f"Consolidation failed: {e!s}")

        # Phase 3: Validation
        workflow.logger.info("Running validation")
        validation_activities = [
            (validate_data, "schema"),
            (check_duplicates, "duplicates"),
            (check_data_freshness, "freshness"),
        ]

        for activity_fn, name in validation_activities:
            try:
                result = await workflow.execute_activity(
                    activity_fn,
                    start_to_close_timeout=timedelta(minutes=10),
                    retry_policy=API_RETRY_POLICY,
                )
                results.append(result)
                if not result.success:
                    errors.append(f"Validation {name}: {result.stderr}")
            except Exception as e:
                errors.append(f"Validation {name} failed: {e!s}")

        # Phase 4: API generation
        workflow.logger.info("Generating API")
        api_activities = [
            (generate_api, "api"),
            (generate_geojson, "geojson"),
            (generate_search_index, "search"),
            (generate_city_contacts_api, "contacts"),
        ]

        for activity_fn, name in api_activities:
            try:
                result = await workflow.execute_activity(
                    activity_fn,
                    start_to_close_timeout=timedelta(minutes=30),
                    retry_policy=API_RETRY_POLICY,
                )
                results.append(result)
                if not result.success:
                    errors.append(f"API {name}: {result.stderr}")
            except Exception as e:
                errors.append(f"API {name} failed: {e!s}")

        successful = sum(1 for r in results if r.success)
        workflow.logger.info(f"Sync complete: {successful}/{len(results)} successful")

        return BatchScriptResult(
            total_scripts=len(results),
            successful=successful,
            failed=len(results) - successful,
            results=results,
            errors=errors,
        )


@workflow.defn
class CivicDataWorkflow:
    """Monthly civic council data collection.

    Scrapes city council data from multiple platforms with
    fallback logic and retry handling.
    """

    @workflow.run
    async def run(self, include_blocked: bool = False) -> BatchScriptResult:
        """Run civic data collection.

        Args:
            include_blocked: If True, include slow Playwright scraping
        """
        results: list[ScriptResult] = []
        errors: list[str] = []

        workflow.logger.info("Starting civic data collection")

        # Run scrapers in order of reliability
        scrapers = [
            (scrape_civicplus_councils, "CivicPlus", True),
            (scrape_granicus_councils, "Granicus", True),
            (scrape_proudcity_councils, "ProudCity", True),
            (scrape_legistar_councils, "Legistar", True),
            (scrape_wikipedia_councils, "Wikipedia", True),
            (scrape_blocked_councils, "Blocked", include_blocked),
        ]

        for activity_fn, name, enabled in scrapers:
            if not enabled:
                continue

            workflow.logger.info(f"Scraping {name}")
            try:
                result = await workflow.execute_activity(
                    activity_fn,
                    start_to_close_timeout=timedelta(hours=1),
                    retry_policy=SCRAPER_RETRY_POLICY,
                    heartbeat_timeout=timedelta(minutes=10),
                )
                results.append(result)
                workflow.logger.info(f"{name}: {'✓' if result.success else '✗'}")
                if not result.success:
                    errors.append(f"{name}: {result.stderr[:200]}")
            except Exception as e:
                errors.append(f"{name} failed: {e!s}")

        # Consolidate all data
        workflow.logger.info("Consolidating scraped data")
        try:
            result = await workflow.execute_activity(
                consolidate_scraped_data,
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=API_RETRY_POLICY,
            )
            results.append(result)
        except Exception as e:
            errors.append(f"Consolidation failed: {e!s}")

        # Generate city contacts API
        try:
            result = await workflow.execute_activity(
                generate_city_contacts_api,
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=API_RETRY_POLICY,
            )
            results.append(result)
        except Exception as e:
            errors.append(f"City contacts API failed: {e!s}")

        successful = sum(1 for r in results if r.success)

        return BatchScriptResult(
            total_scripts=len(results),
            successful=successful,
            failed=len(results) - successful,
            results=results,
            errors=errors,
        )


@workflow.defn
class OpenDataSyncWorkflow:
    """Daily open data synchronization from Bay Area portals."""

    @workflow.run
    async def run(self) -> BatchScriptResult:
        """Sync open data and regenerate API."""
        results: list[ScriptResult] = []
        errors: list[str] = []

        workflow.logger.info("Starting open data sync")

        # Sync open data
        try:
            result = await workflow.execute_activity(
                sync_open_data_cache,
                start_to_close_timeout=timedelta(hours=1),
                retry_policy=API_RETRY_POLICY,
                heartbeat_timeout=timedelta(minutes=5),
            )
            results.append(result)
            if not result.success:
                errors.append(f"Open data sync: {result.stderr}")
        except Exception as e:
            errors.append(f"Open data sync failed: {e!s}")

        # Validate
        try:
            result = await workflow.execute_activity(
                validate_data,
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=API_RETRY_POLICY,
            )
            results.append(result)
        except Exception as e:
            errors.append(f"Validation failed: {e!s}")

        # Regenerate API
        try:
            result = await workflow.execute_activity(
                generate_api,
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=API_RETRY_POLICY,
            )
            results.append(result)
        except Exception as e:
            errors.append(f"API generation failed: {e!s}")

        successful = sum(1 for r in results if r.success)

        return BatchScriptResult(
            total_scripts=len(results),
            successful=successful,
            failed=len(results) - successful,
            results=results,
            errors=errors,
        )


@workflow.defn
class APIGenerationWorkflow:
    """Generate all API outputs from current data."""

    @workflow.run
    async def run(self, include_simple_language: bool = False) -> BatchScriptResult:
        """Generate API files.

        Args:
            include_simple_language: If True, also generate AI-powered simple language
        """
        results: list[ScriptResult] = []
        errors: list[str] = []

        workflow.logger.info("Starting API generation")

        # Core API generation (sequential - dependencies)
        activities = [
            (generate_api, "Main API"),
            (generate_geojson, "GeoJSON"),
            (generate_search_index, "Search Index"),
            (generate_city_contacts_api, "City Contacts"),
        ]

        for activity_fn, name in activities:
            try:
                result = await workflow.execute_activity(
                    activity_fn,
                    start_to_close_timeout=timedelta(minutes=30),
                    retry_policy=API_RETRY_POLICY,
                )
                results.append(result)
                workflow.logger.info(f"{name}: {'✓' if result.success else '✗'}")
                if not result.success:
                    errors.append(f"{name}: {result.stderr}")
            except Exception as e:
                errors.append(f"{name} failed: {e!s}")

        # Optional: Simple language (AI-powered, slow)
        if include_simple_language:
            workflow.logger.info("Generating simple language descriptions")
            try:
                result = await workflow.execute_activity(
                    generate_simple_language,
                    start_to_close_timeout=timedelta(hours=1),
                    retry_policy=API_RETRY_POLICY,
                    heartbeat_timeout=timedelta(minutes=10),
                )
                results.append(result)
            except Exception as e:
                errors.append(f"Simple language failed: {e!s}")

        successful = sum(1 for r in results if r.success)

        return BatchScriptResult(
            total_scripts=len(results),
            successful=successful,
            failed=len(results) - successful,
            results=results,
            errors=errors,
        )


@workflow.defn
class ValidationWorkflow:
    """Run all data validation checks."""

    @workflow.run
    async def run(self, include_link_validation: bool = False) -> BatchScriptResult:
        """Run validation suite.

        Args:
            include_link_validation: If True, validate all external links (slow)
        """
        results: list[ScriptResult] = []
        errors: list[str] = []

        workflow.logger.info("Starting validation")

        activities = [
            (validate_data, "Schema", True),
            (check_duplicates, "Duplicates", True),
            (check_data_freshness, "Freshness", True),
            (validate_map_coordinates, "Coordinates", True),
            (validate_links, "Links", include_link_validation),
        ]

        for activity_fn, name, enabled in activities:
            if not enabled:
                continue

            try:
                result = await workflow.execute_activity(
                    activity_fn,
                    start_to_close_timeout=timedelta(hours=1),
                    retry_policy=API_RETRY_POLICY,
                    heartbeat_timeout=timedelta(minutes=10),
                )
                results.append(result)
                workflow.logger.info(f"{name}: {'✓' if result.success else '✗'}")
                if not result.success:
                    errors.append(f"{name}: {result.stderr}")
            except Exception as e:
                errors.append(f"{name} failed: {e!s}")

        successful = sum(1 for r in results if r.success)

        return BatchScriptResult(
            total_scripts=len(results),
            successful=successful,
            failed=len(results) - successful,
            results=results,
            errors=errors,
        )
