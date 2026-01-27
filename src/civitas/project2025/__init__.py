"""Project 2025 document parsing and tracking.

Parses the "Mandate for Leadership" document to extract policy proposals
and tracks their implementation through legislation and executive actions.

This module is central to Civitas's counter-initiative mission.

Components:
- Project2025Parser: Basic proposal extraction
- EnhancedProject2025Parser: AI-assisted extraction with categorization
- Project2025Tracker: Matches proposals against legislation/EOs
"""

from .parser import Project2025Parser, EnhancedProject2025Parser, PolicyProposal
from .tracker import Project2025Tracker

__all__ = [
    "Project2025Parser",
    "EnhancedProject2025Parser",
    "PolicyProposal",
    "Project2025Tracker",
]
