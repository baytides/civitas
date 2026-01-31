"""Data ingestion workflows for Civitas.

These workflows orchestrate the ingestion of data from various sources
with proper retry logic, progress tracking, and failure handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

# Import activity stubs - these are type hints for the workflow
with workflow.unsafe.imports_passed_through():
    from civitas.workflows.activities import (
        IngestionResult,
        ingest_california,
        ingest_executive_orders,
        ingest_federal_congress,
        ingest_scotus_opinions,
        ingest_state_bills,
    )


# Retry policy for ingestion activities
INGESTION_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=10),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=10),
    maximum_attempts=3,
    non_retryable_error_types=["ValueError", "KeyError"],
)


@dataclass
class FullIngestionParams:
    """Parameters for full data ingestion."""

    congress_numbers: list[int] | None = None  # e.g., [118, 119]
    california_years: list[int] | None = None  # e.g., [2023, 2024]
    eo_years: list[int] | None = None  # e.g., [2024, 2025]
    scotus_terms: list[str] | None = None  # e.g., ["24", "25"]
    states: list[str] | None = None  # e.g., ["CA", "TX", "NY"]
    laws_only: bool = True


@dataclass
class IngestionSummary:
    """Summary of a complete ingestion run."""

    total_sources: int
    successful_sources: int
    failed_sources: int
    total_records: int
    results: list[IngestionResult]
    errors: list[str]


@workflow.defn
class FullIngestionWorkflow:
    """Complete data ingestion from all sources.

    This workflow runs ingestion from:
    1. Federal Congress (legislation)
    2. California Legislature
    3. Executive Orders
    4. Supreme Court opinions
    5. State legislatures (if specified)

    Sources are processed in parallel where possible.
    """

    @workflow.run
    async def run(self, params: FullIngestionParams) -> IngestionSummary:
        """Execute the full ingestion pipeline."""
        results: list[IngestionResult] = []
        errors: list[str] = []

        # Default values if not specified
        congress_numbers = params.congress_numbers or [118, 119]
        california_years = params.california_years or [2023, 2024]
        eo_years = params.eo_years or [2024, 2025]
        scotus_terms = params.scotus_terms or ["24", "25"]

        workflow.logger.info("Starting full ingestion workflow")

        # Phase 1: Federal legislation (sequential by congress)
        for congress in congress_numbers:
            workflow.logger.info(f"Ingesting Congress {congress}")
            try:
                result = await workflow.execute_activity(
                    ingest_federal_congress,
                    args=[congress, params.laws_only],
                    start_to_close_timeout=timedelta(hours=2),
                    retry_policy=INGESTION_RETRY_POLICY,
                    heartbeat_timeout=timedelta(minutes=5),
                )
                results.append(result)
                if result.errors:
                    errors.extend(result.errors)
            except Exception as e:
                errors.append(f"Congress {congress} failed: {e!s}")

        # Phase 2: Executive orders (parallel by year)
        eo_handles = []
        for year in eo_years:
            workflow.logger.info(f"Starting EO ingestion for {year}")
            handle = workflow.start_activity(
                ingest_executive_orders,
                args=[year],
                start_to_close_timeout=timedelta(hours=1),
                retry_policy=INGESTION_RETRY_POLICY,
                heartbeat_timeout=timedelta(minutes=5),
            )
            eo_handles.append((year, handle))

        for year, handle in eo_handles:
            try:
                result = await handle
                results.append(result)
                if result.errors:
                    errors.extend(result.errors)
            except Exception as e:
                errors.append(f"EO {year} failed: {e!s}")

        # Phase 3: SCOTUS opinions
        workflow.logger.info("Ingesting SCOTUS opinions")
        try:
            result = await workflow.execute_activity(
                ingest_scotus_opinions,
                args=[None, False],  # Will use recent terms
                start_to_close_timeout=timedelta(hours=2),
                retry_policy=INGESTION_RETRY_POLICY,
                heartbeat_timeout=timedelta(minutes=5),
            )
            results.append(result)
            if result.errors:
                errors.extend(result.errors)
        except Exception as e:
            errors.append(f"SCOTUS failed: {e!s}")

        # Phase 4: California legislature (parallel by year)
        ca_handles = []
        for year in california_years:
            workflow.logger.info(f"Starting California {year} ingestion")
            handle = workflow.start_activity(
                ingest_california,
                args=[year],
                start_to_close_timeout=timedelta(hours=2),
                retry_policy=INGESTION_RETRY_POLICY,
                heartbeat_timeout=timedelta(minutes=5),
            )
            ca_handles.append((year, handle))

        for year, handle in ca_handles:
            try:
                result = await handle
                results.append(result)
                if result.errors:
                    errors.extend(result.errors)
            except Exception as e:
                errors.append(f"California {year} failed: {e!s}")

        # Phase 5: State legislatures (if specified, parallel)
        if params.states:
            state_handles = []
            for state in params.states:
                workflow.logger.info(f"Starting {state} ingestion")
                handle = workflow.start_activity(
                    ingest_state_bills,
                    args=[state, None],
                    start_to_close_timeout=timedelta(hours=1),
                    retry_policy=INGESTION_RETRY_POLICY,
                    heartbeat_timeout=timedelta(minutes=5),
                )
                state_handles.append((state, handle))

            for state, handle in state_handles:
                try:
                    result = await handle
                    results.append(result)
                    if result.errors:
                        errors.extend(result.errors)
                except Exception as e:
                    errors.append(f"State {state} failed: {e!s}")

        # Calculate summary
        successful = sum(1 for r in results if not r.errors)
        total_records = sum(r.records_processed for r in results)

        workflow.logger.info(
            f"Ingestion complete: {successful}/{len(results)} sources, "
            f"{total_records} total records"
        )

        return IngestionSummary(
            total_sources=len(results),
            successful_sources=successful,
            failed_sources=len(results) - successful,
            total_records=total_records,
            results=results,
            errors=errors,
        )


@workflow.defn
class FederalIngestionWorkflow:
    """Focused workflow for federal legislation ingestion."""

    @workflow.run
    async def run(
        self,
        congress_numbers: list[int],
        laws_only: bool = True,
    ) -> IngestionSummary:
        """Ingest federal legislation for specified Congress sessions."""
        results: list[IngestionResult] = []
        errors: list[str] = []

        for congress in congress_numbers:
            workflow.logger.info(f"Ingesting Congress {congress}")
            try:
                result = await workflow.execute_activity(
                    ingest_federal_congress,
                    args=[congress, laws_only],
                    start_to_close_timeout=timedelta(hours=2),
                    retry_policy=INGESTION_RETRY_POLICY,
                    heartbeat_timeout=timedelta(minutes=5),
                )
                results.append(result)
                if result.errors:
                    errors.extend(result.errors)
            except Exception as e:
                errors.append(f"Congress {congress} failed: {e!s}")

        successful = sum(1 for r in results if not r.errors)
        total_records = sum(r.records_processed for r in results)

        return IngestionSummary(
            total_sources=len(results),
            successful_sources=successful,
            failed_sources=len(results) - successful,
            total_records=total_records,
            results=results,
            errors=errors,
        )


@workflow.defn
class SCOTUSIngestionWorkflow:
    """Focused workflow for Supreme Court data ingestion."""

    @workflow.run
    async def run(
        self,
        terms: list[str] | None = None,
        all_terms: bool = False,
    ) -> IngestionResult:
        """Ingest SCOTUS opinions for specified terms."""
        workflow.logger.info(f"Starting SCOTUS ingestion (terms={terms}, all={all_terms})")

        result = await workflow.execute_activity(
            ingest_scotus_opinions,
            args=[terms[0] if terms and len(terms) == 1 else None, all_terms],
            start_to_close_timeout=timedelta(hours=3),
            retry_policy=INGESTION_RETRY_POLICY,
            heartbeat_timeout=timedelta(minutes=5),
        )

        return result


@workflow.defn
class StateIngestionWorkflow:
    """Focused workflow for state legislature ingestion."""

    @workflow.run
    async def run(
        self,
        states: list[str],
        session: str | None = None,
    ) -> IngestionSummary:
        """Ingest state legislature data for specified states.

        States are processed in parallel for efficiency.
        """
        results: list[IngestionResult] = []
        errors: list[str] = []

        # Start all state ingestions in parallel
        handles = []
        for state in states:
            workflow.logger.info(f"Starting {state} ingestion")
            handle = workflow.start_activity(
                ingest_state_bills,
                args=[state, session],
                start_to_close_timeout=timedelta(hours=1),
                retry_policy=INGESTION_RETRY_POLICY,
                heartbeat_timeout=timedelta(minutes=5),
            )
            handles.append((state, handle))

        # Collect results
        for state, handle in handles:
            try:
                result = await handle
                results.append(result)
                if result.errors:
                    errors.extend(result.errors)
            except Exception as e:
                errors.append(f"State {state} failed: {e!s}")

        successful = sum(1 for r in results if not r.errors)
        total_records = sum(r.records_processed for r in results)

        return IngestionSummary(
            total_sources=len(results),
            successful_sources=successful,
            failed_sources=len(results) - successful,
            total_records=total_records,
            results=results,
            errors=errors,
        )
