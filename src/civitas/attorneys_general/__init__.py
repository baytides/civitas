"""State Attorneys General litigation tracking.

Data Sources:
- https://attorneysgeneral.org/ - Multi-state lawsuits database
- Individual state AG websites

Credits: Dr. Paul Nolette, Marquette University
"""

from .scraper import AGAmicusBrief, AGLawsuit, AGLitigationScraper

__all__ = ["AGLitigationScraper", "AGLawsuit", "AGAmicusBrief"]
