"""Resistance analysis and recommendation engine.

Uses Ollama/Llama (via Bay Tides) to analyze legal data and
generate strategies for countering Project 2025 implementations.
"""

from .analyzer import ResistanceAnalyzer
from .recommender import ResistanceRecommender
from .tracker import ImplementationTracker

__all__ = ["ResistanceAnalyzer", "ResistanceRecommender", "ImplementationTracker"]
