"""Analysis tools for legal and legislative data.

This module provides:
- categories: Comprehensive law categories for classification
- actions: Specific resistance actions for each category
- analyzer: AI-powered legislation analysis using Ollama/Llama
- resistance: Detailed resistance strategy generation
"""

from .actions import (
    CATEGORY_ACTIONS,
    DEFAULT_ACTIONS,
    ActionType,
    ActionUrgency,
    ResistanceAction,
    get_actions_by_type,
    get_actions_for_category,
    get_actions_for_jurisdiction,
    get_urgent_actions,
)
from .analyzer import (
    AnalysisResult,
    LegislationAnalyzer,
    check_ollama_connection,
    list_ollama_models,
)
from .categories import (
    CATEGORIES,
    LawCategory,
    get_all_keywords,
    get_category_by_slug,
    get_p2025_categories,
)
from .resistance import (
    LegalStrategy,
    OrganizingGuide,
    ResistanceContent,
    ResistanceGenerator,
    StrategyType,
)

__all__ = [
    # Categories
    "CATEGORIES",
    "LawCategory",
    "get_category_by_slug",
    "get_p2025_categories",
    "get_all_keywords",
    # Actions
    "CATEGORY_ACTIONS",
    "DEFAULT_ACTIONS",
    "ActionType",
    "ActionUrgency",
    "ResistanceAction",
    "get_actions_for_category",
    "get_actions_by_type",
    "get_urgent_actions",
    "get_actions_for_jurisdiction",
    # Analyzer
    "LegislationAnalyzer",
    "AnalysisResult",
    "check_ollama_connection",
    "list_ollama_models",
    # Resistance
    "ResistanceGenerator",
    "ResistanceContent",
    "LegalStrategy",
    "OrganizingGuide",
    "StrategyType",
]
