"""Temporal workflows for Civitas data pipelines.

This module provides durable, fault-tolerant workflows for:
- Data ingestion from Congress.gov, SCOTUS, state legislatures, etc.
- AI content generation (resistance analyses, justice profiles, insights)

Workflows are designed to be:
- Resumable after failures
- Observable via Temporal UI
- Schedulable for recurring execution
"""

from civitas.workflows.activities import (
    ingest_california,
    ingest_executive_orders,
    ingest_federal_congress,
    ingest_scotus_opinions,
    ingest_state_bills,
    generate_justice_profiles,
    generate_resistance_analyses,
    generate_resistance_recommendations,
    generate_insights,
)
from civitas.workflows.ingestion import (
    FullIngestionWorkflow,
    FederalIngestionWorkflow,
    SCOTUSIngestionWorkflow,
    StateIngestionWorkflow,
)
from civitas.workflows.content import (
    ContentGenerationWorkflow,
    JusticeProfileWorkflow,
    ResistanceAnalysisWorkflow,
)
from civitas.workflows.worker import create_worker, run_worker

__all__ = [
    # Activities
    "ingest_california",
    "ingest_executive_orders",
    "ingest_federal_congress",
    "ingest_scotus_opinions",
    "ingest_state_bills",
    "generate_justice_profiles",
    "generate_resistance_analyses",
    "generate_resistance_recommendations",
    "generate_insights",
    # Ingestion Workflows
    "FullIngestionWorkflow",
    "FederalIngestionWorkflow",
    "SCOTUSIngestionWorkflow",
    "StateIngestionWorkflow",
    # Content Workflows
    "ContentGenerationWorkflow",
    "JusticeProfileWorkflow",
    "ResistanceAnalysisWorkflow",
    # Worker
    "create_worker",
    "run_worker",
]
