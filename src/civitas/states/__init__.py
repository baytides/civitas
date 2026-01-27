"""State legislative data integration.

Uses Open States API and scrapers for comprehensive state-level data.

Credits:
- Open States Project (GPL-3.0 / CC0-1.0)
- Open Civic Data (BSD-3-Clause)
"""

from .openstates import OpenStatesClient, StateBill, StateLegislator

__all__ = ["OpenStatesClient", "StateBill", "StateLegislator"]
