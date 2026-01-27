"""Resistance analysis and recommendation engine.

Uses Carl (Ollama/Llama on Azure) to analyze legal data and
generate strategies for countering Project 2025 implementations.
"""

from .analyzer import ResistanceAnalyzer
from .recommender import ResistanceRecommender
from .tracker import ImplementationTracker

__all__ = ["ResistanceAnalyzer", "ResistanceRecommender", "ImplementationTracker"]
