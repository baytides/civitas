"""Temporal client utilities for triggering workflows.

This module provides functions to start and monitor Civitas workflows.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from temporalio.client import WorkflowHandle

from civitas.workflows.content import (
    ContentGenerationParams,
    ContentGenerationWorkflow,
    JusticeProfileWorkflow,
    ResistanceAnalysisWorkflow,
)
from civitas.workflows.ingestion import (
    FederalIngestionWorkflow,
    FullIngestionParams,
    FullIngestionWorkflow,
    SCOTUSIngestionWorkflow,
    StateIngestionWorkflow,
)
from civitas.workflows.worker import (
    create_client,
    get_task_queue,
)


def generate_workflow_id(prefix: str) -> str:
    """Generate a unique workflow ID."""
    return f"{prefix}-{uuid4().hex[:8]}"


async def start_full_ingestion(
    congress_numbers: list[int] | None = None,
    california_years: list[int] | None = None,
    eo_years: list[int] | None = None,
    states: list[str] | None = None,
    laws_only: bool = True,
    wait: bool = False,
) -> WorkflowHandle | Any:
    """Start a full ingestion workflow.

    Args:
        congress_numbers: Congress sessions to ingest (e.g., [118, 119])
        california_years: California session years (e.g., [2023, 2024])
        eo_years: Executive order years (e.g., [2024, 2025])
        states: State abbreviations for OpenStates (e.g., ["CA", "TX"])
        laws_only: Only ingest enacted laws (not all bills)
        wait: If True, wait for workflow completion and return result

    Returns:
        WorkflowHandle if wait=False, otherwise the workflow result
    """
    client = await create_client()
    task_queue = get_task_queue()
    workflow_id = generate_workflow_id("full-ingestion")

    params = FullIngestionParams(
        congress_numbers=congress_numbers,
        california_years=california_years,
        eo_years=eo_years,
        states=states,
        laws_only=laws_only,
    )

    handle = await client.start_workflow(
        FullIngestionWorkflow.run,
        params,
        id=workflow_id,
        task_queue=task_queue,
    )

    print(f"Started workflow: {workflow_id}")

    if wait:
        return await handle.result()
    return handle


async def start_federal_ingestion(
    congress_numbers: list[int],
    laws_only: bool = True,
    wait: bool = False,
) -> WorkflowHandle | Any:
    """Start federal legislation ingestion."""
    client = await create_client()
    task_queue = get_task_queue()
    workflow_id = generate_workflow_id("federal-ingestion")

    handle = await client.start_workflow(
        FederalIngestionWorkflow.run,
        args=[congress_numbers, laws_only],
        id=workflow_id,
        task_queue=task_queue,
    )

    print(f"Started workflow: {workflow_id}")

    if wait:
        return await handle.result()
    return handle


async def start_scotus_ingestion(
    terms: list[str] | None = None,
    all_terms: bool = False,
    wait: bool = False,
) -> WorkflowHandle | Any:
    """Start SCOTUS opinions ingestion."""
    client = await create_client()
    task_queue = get_task_queue()
    workflow_id = generate_workflow_id("scotus-ingestion")

    handle = await client.start_workflow(
        SCOTUSIngestionWorkflow.run,
        args=[terms, all_terms],
        id=workflow_id,
        task_queue=task_queue,
    )

    print(f"Started workflow: {workflow_id}")

    if wait:
        return await handle.result()
    return handle


async def start_state_ingestion(
    states: list[str],
    session: str | None = None,
    wait: bool = False,
) -> WorkflowHandle | Any:
    """Start state legislature ingestion."""
    client = await create_client()
    task_queue = get_task_queue()
    workflow_id = generate_workflow_id("state-ingestion")

    handle = await client.start_workflow(
        StateIngestionWorkflow.run,
        args=[states, session],
        id=workflow_id,
        task_queue=task_queue,
    )

    print(f"Started workflow: {workflow_id}")

    if wait:
        return await handle.result()
    return handle


async def start_content_generation(
    generate_profiles: bool = True,
    generate_analyses: bool = True,
    generate_recommendations: bool = True,
    generate_insights: bool = False,
    analysis_batch_size: int = 25,
    max_batches: int | None = None,
    wait: bool = False,
) -> WorkflowHandle | Any:
    """Start full content generation workflow.

    Args:
        generate_profiles: Generate justice profiles
        generate_analyses: Generate resistance analyses
        generate_recommendations: Generate recommendations
        generate_insights: Generate plain-language insights
        analysis_batch_size: Items per batch
        max_batches: Maximum number of batches (None = until done)
        wait: If True, wait for completion

    Returns:
        WorkflowHandle or result
    """
    client = await create_client()
    task_queue = get_task_queue()
    workflow_id = generate_workflow_id("content-generation")

    params = ContentGenerationParams(
        generate_profiles=generate_profiles,
        generate_analyses=generate_analyses,
        generate_recommendations=generate_recommendations,
        generate_insights=generate_insights,
        analysis_batch_size=analysis_batch_size,
        max_analysis_batches=max_batches,
        max_recommendation_batches=max_batches,
    )

    handle = await client.start_workflow(
        ContentGenerationWorkflow.run,
        params,
        id=workflow_id,
        task_queue=task_queue,
    )

    print(f"Started workflow: {workflow_id}")

    if wait:
        return await handle.result()
    return handle


async def start_justice_profiles(
    limit: int | None = None,
    force: bool = False,
    wait: bool = False,
) -> WorkflowHandle | Any:
    """Start justice profile generation."""
    client = await create_client()
    task_queue = get_task_queue()
    workflow_id = generate_workflow_id("justice-profiles")

    handle = await client.start_workflow(
        JusticeProfileWorkflow.run,
        args=[limit, force],
        id=workflow_id,
        task_queue=task_queue,
    )

    print(f"Started workflow: {workflow_id}")

    if wait:
        return await handle.result()
    return handle


async def start_resistance_analysis(
    batch_size: int = 25,
    refresh_days: int = 30,
    max_batches: int | None = None,
    include_recommendations: bool = True,
    wait: bool = False,
) -> WorkflowHandle | Any:
    """Start resistance analysis workflow.

    This is the main workflow for expert content generation.
    """
    client = await create_client()
    task_queue = get_task_queue()
    workflow_id = generate_workflow_id("resistance-analysis")

    handle = await client.start_workflow(
        ResistanceAnalysisWorkflow.run,
        args=[batch_size, refresh_days, max_batches, include_recommendations],
        id=workflow_id,
        task_queue=task_queue,
    )

    print(f"Started workflow: {workflow_id}")

    if wait:
        return await handle.result()
    return handle


async def get_workflow_status(workflow_id: str) -> dict[str, Any]:
    """Get the status of a running workflow."""
    client = await create_client()
    handle = client.get_workflow_handle(workflow_id)

    desc = await handle.describe()

    return {
        "workflow_id": workflow_id,
        "status": desc.status.name,
        "start_time": desc.start_time.isoformat() if desc.start_time else None,
        "close_time": desc.close_time.isoformat() if desc.close_time else None,
        "workflow_type": desc.workflow_type,
    }


async def cancel_workflow(workflow_id: str) -> None:
    """Cancel a running workflow."""
    client = await create_client()
    handle = client.get_workflow_handle(workflow_id)
    await handle.cancel()
    print(f"Cancelled workflow: {workflow_id}")


async def list_workflows(
    workflow_type: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List recent workflows."""
    client = await create_client()

    query_parts = []
    if workflow_type:
        query_parts.append(f'WorkflowType = "{workflow_type}"')
    if status:
        query_parts.append(f'ExecutionStatus = "{status}"')

    query = " AND ".join(query_parts) if query_parts else None

    workflows = []
    async for workflow in client.list_workflows(query=query):
        workflows.append({
            "workflow_id": workflow.id,
            "run_id": workflow.run_id,
            "type": workflow.workflow_type,
            "status": workflow.status.name,
            "start_time": workflow.start_time.isoformat() if workflow.start_time else None,
        })
        if len(workflows) >= limit:
            break

    return workflows
