"""Analysis tools for legal and legislative data.

This module provides:
- categories: Comprehensive law categories for classification
- actions: Specific resistance actions for each category
- analyzer: AI-powered legislation analysis using Ollama/Llama
- resistance: Detailed resistance strategy generation
"""

from .categories import (
    CATEGORIES,
    LawCategory,
    get_category_by_slug,
    get_p2025_categories,
    get_all_keywords,
)

from .actions import (
    CATEGORY_ACTIONS,
    DEFAULT_ACTIONS,
    ActionType,
    ActionUrgency,
    ResistanceAction,
    get_actions_for_category,
    get_actions_by_type,
    get_urgent_actions,
    get_actions_for_jurisdiction,
)

from .analyzer import (
    LegislationAnalyzer,
    AnalysisResult,
    check_ollama_connection,
    list_ollama_models,
)

from .resistance import (
    ResistanceGenerator,
    ResistanceContent,
    LegalStrategy,
    OrganizingGuide,
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
