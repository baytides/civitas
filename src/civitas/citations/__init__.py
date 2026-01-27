"""Citation extraction and linking.

Uses eyecite from Free Law Project (BSD-2-Clause) for extracting
legal citations from text.

Credits: https://github.com/freelawproject/eyecite
"""

from .extractor import CitationExtractor, ExtractedCitation
from .models import Citation

__all__ = ["CitationExtractor", "ExtractedCitation", "Citation"]
