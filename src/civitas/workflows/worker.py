"""Temporal worker for Civitas workflows.

This module provides the worker that executes workflows and activities.
Run with: civitas worker start
"""

from __future__ import annotations

import asyncio
import os

from temporalio.client import Client
from temporalio.worker import Worker

from civitas.workflows.activities import (
    generate_insights,
    generate_justice_profiles,
    generate_resistance_analyses,
    generate_resistance_recommendations,
    ingest_california,
    ingest_executive_orders,
    ingest_federal_congress,
    ingest_scotus_opinions,
    ingest_state_bills,
)
from civitas.workflows.baynavigator import (
    APIGenerationWorkflow,
    # Workflows
    BayNavigatorFullSyncWorkflow,
    CivicDataWorkflow,
    OpenDataSyncWorkflow,
    ValidationWorkflow,
    check_data_freshness,
    check_duplicates,
    consolidate_scraped_data,
    fetch_carbon_stats,
    generate_api,
    generate_city_contacts_api,
    generate_geojson,
    generate_search_index,
    generate_simple_language,
    scrape_211_bayarea,
    scrape_blocked_councils,
    scrape_civicplus_councils,
    scrape_granicus_councils,
    scrape_legistar_councils,
    scrape_proudcity_councils,
    scrape_wikipedia_councils,
    sync_california_codes,
    sync_imls_museums,
    sync_nps_parks,
    sync_open_data_cache,
    sync_recreation_gov,
    sync_throughline_helplines,
    # Activities
    sync_transit_data,
    sync_usagov_benefits,
    validate_data,
    validate_links,
    validate_map_coordinates,
)
from civitas.workflows.content import (
    ContentGenerationWorkflow,
    JusticeProfileWorkflow,
    ResistanceAnalysisWorkflow,
)
from civitas.workflows.ingestion import (
    FederalIngestionWorkflow,
    FullIngestionWorkflow,
    SCOTUSIngestionWorkflow,
    StateIngestionWorkflow,
)

# Default configuration
DEFAULT_TEMPORAL_HOST = "localhost:7233"
DEFAULT_NAMESPACE = "default"
DEFAULT_TASK_QUEUE = "civitas-tasks"


def get_temporal_host() -> str:
    """Get Temporal server address from environment."""
    return os.getenv("TEMPORAL_HOST", DEFAULT_TEMPORAL_HOST)


def get_namespace() -> str:
    """Get Temporal namespace from environment."""
    return os.getenv("TEMPORAL_NAMESPACE", DEFAULT_NAMESPACE)


def get_task_queue() -> str:
    """Get Temporal task queue from environment."""
    return os.getenv("TEMPORAL_TASK_QUEUE", DEFAULT_TASK_QUEUE)


async def create_client() -> Client:
    """Create a Temporal client connection."""
    host = get_temporal_host()
    namespace = get_namespace()

    return await Client.connect(host, namespace=namespace)


async def create_worker(client: Client | None = None) -> Worker:
    """Create a Temporal worker with all workflows and activities.

    Args:
        client: Optional pre-existing client. If None, creates new connection.

    Returns:
        Configured Worker instance (not started)
    """
    if client is None:
        client = await create_client()

    task_queue = get_task_queue()

    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[
            # Civitas: Ingestion workflows
            FullIngestionWorkflow,
            FederalIngestionWorkflow,
            SCOTUSIngestionWorkflow,
            StateIngestionWorkflow,
            # Civitas: Content generation workflows
            ContentGenerationWorkflow,
            JusticeProfileWorkflow,
            ResistanceAnalysisWorkflow,
            # Bay Navigator workflows
            BayNavigatorFullSyncWorkflow,
            CivicDataWorkflow,
            OpenDataSyncWorkflow,
            APIGenerationWorkflow,
            ValidationWorkflow,
        ],
        activities=[
            # Civitas: Ingestion activities
            ingest_federal_congress,
            ingest_california,
            ingest_executive_orders,
            ingest_scotus_opinions,
            ingest_state_bills,
            # Civitas: Content generation activities
            generate_justice_profiles,
            generate_resistance_analyses,
            generate_resistance_recommendations,
            generate_insights,
            # Bay Navigator: Data ingestion
            sync_transit_data,
            sync_open_data_cache,
            sync_nps_parks,
            sync_recreation_gov,
            sync_imls_museums,
            sync_usagov_benefits,
            sync_california_codes,
            sync_throughline_helplines,
            fetch_carbon_stats,
            # Bay Navigator: Civic scraping
            scrape_211_bayarea,
            scrape_civicplus_councils,
            scrape_granicus_councils,
            scrape_proudcity_councils,
            scrape_legistar_councils,
            scrape_wikipedia_councils,
            scrape_blocked_councils,
            consolidate_scraped_data,
            # Bay Navigator: Validation
            validate_data,
            check_duplicates,
            validate_links,
            check_data_freshness,
            validate_map_coordinates,
            # Bay Navigator: API generation
            generate_api,
            generate_geojson,
            generate_search_index,
            generate_simple_language,
            generate_city_contacts_api,
        ],
    )

    return worker


async def run_worker() -> None:
    """Run the Temporal worker until interrupted.

    This is the main entry point for the worker process.
    """
    client = await create_client()
    worker = await create_worker(client)

    print("Starting Civitas Temporal worker...")
    print(f"  Host: {get_temporal_host()}")
    print(f"  Namespace: {get_namespace()}")
    print(f"  Task Queue: {get_task_queue()}")
    print()
    print("Registered workflows:")
    print("  Civitas:")
    print("    - FullIngestionWorkflow")
    print("    - FederalIngestionWorkflow")
    print("    - SCOTUSIngestionWorkflow")
    print("    - StateIngestionWorkflow")
    print("    - ContentGenerationWorkflow")
    print("    - JusticeProfileWorkflow")
    print("    - ResistanceAnalysisWorkflow")
    print("  Bay Navigator:")
    print("    - BayNavigatorFullSyncWorkflow")
    print("    - CivicDataWorkflow")
    print("    - OpenDataSyncWorkflow")
    print("    - APIGenerationWorkflow")
    print("    - ValidationWorkflow")
    print()
    print("Worker is running. Press Ctrl+C to stop.")

    await worker.run()


def main() -> None:
    """Entry point for running the worker as a standalone process."""
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        print("\nWorker stopped.")


if __name__ == "__main__":
    main()
