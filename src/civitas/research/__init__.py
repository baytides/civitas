"""Research and report generation tools for Civitas.

This module provides integrations with external research tools:
- STORM: Generates comprehensive Wikipedia-style reports with citations

Usage:
    from civitas.research import STORMReportGenerator

    generator = STORMReportGenerator(session)
    report = generator.generate_policy_report("EPA regulations under P2025")
"""

from .storm_integration import STORMReport, STORMReportGenerator, generate_storm_report

__all__ = [
    "STORMReport",
    "STORMReportGenerator",
    "generate_storm_report",
]
