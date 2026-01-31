"""AI content generation workflows for Civitas.

These workflows orchestrate the generation of AI-powered content including:
- Justice voting profiles
- Resistance analyses
- Resistance recommendations
- Plain-language insights
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from civitas.workflows.activities import (
        GenerationResult,
        generate_insights,
        generate_justice_profiles,
        generate_resistance_analyses,
        generate_resistance_recommendations,
    )


# Retry policy for AI generation - more conservative due to LLM costs
AI_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=30),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=5),
    maximum_attempts=2,  # LLM calls are expensive, limit retries
    non_retryable_error_types=["ValueError", "AuthenticationError"],
)


@dataclass
class ContentGenerationParams:
    """Parameters for full content generation."""

    # Justice profiles
    generate_profiles: bool = True
    profile_limit: int | None = None
    force_profiles: bool = False

    # Resistance analyses
    generate_analyses: bool = True
    analysis_batch_size: int = 25
    analysis_refresh_days: int = 30
    max_analysis_batches: int | None = None

    # Resistance recommendations
    generate_recommendations: bool = True
    recommendation_batch_size: int = 25
    recommendation_tier: str | None = None
    force_recommendations: bool = False
    max_recommendation_batches: int | None = None

    # Insights
    generate_insights: bool = False
    insight_types: list[str] | None = None  # ["objective", "eo", "case", "legislation"]
    insight_limit: int = 50


@dataclass
class ContentGenerationSummary:
    """Summary of content generation run."""

    profiles_generated: int
    analyses_generated: int
    recommendations_generated: int
    insights_generated: int
    total_items: int
    total_failures: int
    results: list[GenerationResult]
    errors: list[str]


@workflow.defn
class ContentGenerationWorkflow:
    """Full content generation workflow.

    Runs generation in the correct order:
    1. Justice profiles (needed for legal context)
    2. Resistance analyses (uses justice data)
    3. Resistance recommendations (uses analyses)
    4. Insights (independent)
    """

    @workflow.run
    async def run(self, params: ContentGenerationParams) -> ContentGenerationSummary:
        """Execute the full content generation pipeline."""
        results: list[GenerationResult] = []
        errors: list[str] = []

        profiles_generated = 0
        analyses_generated = 0
        recommendations_generated = 0
        insights_generated = 0

        workflow.logger.info("Starting content generation workflow")

        # Phase 1: Justice profiles
        if params.generate_profiles:
            workflow.logger.info("Generating justice profiles")
            try:
                result = await workflow.execute_activity(
                    generate_justice_profiles,
                    args=[params.profile_limit, params.force_profiles],
                    start_to_close_timeout=timedelta(hours=1),
                    retry_policy=AI_RETRY_POLICY,
                    heartbeat_timeout=timedelta(minutes=10),
                )
                results.append(result)
                profiles_generated = result.items_generated
                if result.errors:
                    errors.extend(result.errors)
            except Exception as e:
                errors.append(f"Justice profiles failed: {e!s}")

        # Phase 2: Resistance analyses (in batches)
        if params.generate_analyses:
            batch_count = 0
            max_batches = params.max_analysis_batches or 100  # Safety limit

            while batch_count < max_batches:
                workflow.logger.info(f"Generating resistance analyses batch {batch_count + 1}")
                try:
                    result = await workflow.execute_activity(
                        generate_resistance_analyses,
                        args=[params.analysis_batch_size, params.analysis_refresh_days],
                        start_to_close_timeout=timedelta(hours=2),
                        retry_policy=AI_RETRY_POLICY,
                        heartbeat_timeout=timedelta(minutes=10),
                    )
                    results.append(result)
                    analyses_generated += result.items_generated
                    if result.errors:
                        errors.extend(result.errors)

                    # Stop if no more items to process
                    if result.items_processed == 0:
                        workflow.logger.info("No more policies needing analysis")
                        break

                    batch_count += 1

                except Exception as e:
                    errors.append(f"Analysis batch {batch_count + 1} failed: {e!s}")
                    break

        # Phase 3: Resistance recommendations (in batches)
        if params.generate_recommendations:
            batch_count = 0
            max_batches = params.max_recommendation_batches or 100

            while batch_count < max_batches:
                workflow.logger.info(f"Generating recommendations batch {batch_count + 1}")
                try:
                    result = await workflow.execute_activity(
                        generate_resistance_recommendations,
                        args=[
                            params.recommendation_batch_size,
                            params.recommendation_tier,
                            params.force_recommendations,
                        ],
                        start_to_close_timeout=timedelta(hours=2),
                        retry_policy=AI_RETRY_POLICY,
                        heartbeat_timeout=timedelta(minutes=10),
                    )
                    results.append(result)
                    recommendations_generated += result.items_generated
                    if result.errors:
                        errors.extend(result.errors)

                    if result.items_processed == 0:
                        workflow.logger.info("No more policies needing recommendations")
                        break

                    batch_count += 1

                except Exception as e:
                    errors.append(f"Recommendation batch {batch_count + 1} failed: {e!s}")
                    break

        # Phase 4: Insights (parallel by type)
        if params.generate_insights:
            insight_types = params.insight_types or ["objective", "eo", "case"]
            insight_handles = []

            for content_type in insight_types:
                workflow.logger.info(f"Starting insights for {content_type}")
                handle = workflow.start_activity(
                    generate_insights,
                    args=[content_type, params.insight_limit, False, None],
                    start_to_close_timeout=timedelta(hours=1),
                    retry_policy=AI_RETRY_POLICY,
                    heartbeat_timeout=timedelta(minutes=10),
                )
                insight_handles.append((content_type, handle))

            for content_type, handle in insight_handles:
                try:
                    result = await handle
                    results.append(result)
                    insights_generated += result.items_generated
                    if result.errors:
                        errors.extend(result.errors)
                except Exception as e:
                    errors.append(f"Insights for {content_type} failed: {e!s}")

        # Calculate totals
        total_items = (
            profiles_generated
            + analyses_generated
            + recommendations_generated
            + insights_generated
        )
        total_failures = sum(r.items_failed for r in results)

        workflow.logger.info(
            f"Content generation complete: {total_items} items, {total_failures} failures"
        )

        return ContentGenerationSummary(
            profiles_generated=profiles_generated,
            analyses_generated=analyses_generated,
            recommendations_generated=recommendations_generated,
            insights_generated=insights_generated,
            total_items=total_items,
            total_failures=total_failures,
            results=results,
            errors=errors,
        )


@workflow.defn
class JusticeProfileWorkflow:
    """Focused workflow for justice profile generation."""

    @workflow.run
    async def run(
        self,
        limit: int | None = None,
        force: bool = False,
    ) -> GenerationResult:
        """Generate justice profiles.

        This workflow:
        1. Identifies justices needing profiles
        2. Gathers voting history and opinion data
        3. Generates AI-powered profiles
        """
        workflow.logger.info(f"Starting justice profile generation (limit={limit}, force={force})")

        result = await workflow.execute_activity(
            generate_justice_profiles,
            args=[limit, force],
            start_to_close_timeout=timedelta(hours=2),
            retry_policy=AI_RETRY_POLICY,
            heartbeat_timeout=timedelta(minutes=10),
        )

        return result


@workflow.defn
class ResistanceAnalysisWorkflow:
    """Focused workflow for resistance analysis generation.

    This is the main workflow for generating expert-level analysis
    of Project 2025 policies, including:
    - Constitutional vulnerabilities
    - Relevant precedents
    - Challenge strategies
    - State resistance options
    """

    @workflow.run
    async def run(
        self,
        batch_size: int = 25,
        refresh_days: int = 30,
        max_batches: int | None = None,
        include_recommendations: bool = True,
    ) -> ContentGenerationSummary:
        """Run resistance analysis generation.

        Args:
            batch_size: Number of policies to process per batch
            refresh_days: Regenerate analyses older than this
            max_batches: Maximum number of batches (None = until done)
            include_recommendations: Also generate recommendations after analyses
        """
        results: list[GenerationResult] = []
        errors: list[str] = []
        analyses_generated = 0
        recommendations_generated = 0
        batch_count = 0
        max_batches = max_batches or 1000  # Safety limit

        workflow.logger.info(
            f"Starting resistance analysis workflow "
            f"(batch_size={batch_size}, refresh_days={refresh_days})"
        )

        # Phase 1: Generate analyses in batches
        while batch_count < max_batches:
            workflow.logger.info(f"Processing analysis batch {batch_count + 1}")

            try:
                result = await workflow.execute_activity(
                    generate_resistance_analyses,
                    args=[batch_size, refresh_days],
                    start_to_close_timeout=timedelta(hours=2),
                    retry_policy=AI_RETRY_POLICY,
                    heartbeat_timeout=timedelta(minutes=10),
                )
                results.append(result)
                analyses_generated += result.items_generated

                if result.errors:
                    errors.extend(result.errors)

                # Stop if no more items
                if result.items_processed == 0:
                    workflow.logger.info("Analysis phase complete - no more policies")
                    break

                batch_count += 1

                # Brief pause between batches to avoid overwhelming the LLM
                await workflow.sleep(timedelta(seconds=5))

            except Exception as e:
                errors.append(f"Analysis batch {batch_count + 1} failed: {e!s}")
                break

        # Phase 2: Generate recommendations for analyzed policies
        if include_recommendations:
            batch_count = 0
            workflow.logger.info("Starting recommendations phase")

            while batch_count < max_batches:
                workflow.logger.info(f"Processing recommendation batch {batch_count + 1}")

                try:
                    result = await workflow.execute_activity(
                        generate_resistance_recommendations,
                        args=[batch_size, None, False],
                        start_to_close_timeout=timedelta(hours=2),
                        retry_policy=AI_RETRY_POLICY,
                        heartbeat_timeout=timedelta(minutes=10),
                    )
                    results.append(result)
                    recommendations_generated += result.items_generated

                    if result.errors:
                        errors.extend(result.errors)

                    if result.items_processed == 0:
                        workflow.logger.info("Recommendations phase complete")
                        break

                    batch_count += 1
                    await workflow.sleep(timedelta(seconds=5))

                except Exception as e:
                    errors.append(f"Recommendation batch {batch_count + 1} failed: {e!s}")
                    break

        total_items = analyses_generated + recommendations_generated
        total_failures = sum(r.items_failed for r in results)

        workflow.logger.info(
            f"Resistance workflow complete: "
            f"{analyses_generated} analyses, {recommendations_generated} recommendations"
        )

        return ContentGenerationSummary(
            profiles_generated=0,
            analyses_generated=analyses_generated,
            recommendations_generated=recommendations_generated,
            insights_generated=0,
            total_items=total_items,
            total_failures=total_failures,
            results=results,
            errors=errors,
        )
