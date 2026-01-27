"""Federal executive actions from the Federal Register.

API: https://www.federalregister.gov/developers/documentation/api/v1
Source: US National Archives (Public Domain)

Provides:
- FederalRegisterClient: Access to executive orders, rules, notices
- ExecutiveOrderModel: Executive order data model
- FederalRegisterDocument: General document model
"""

from .client import FederalRegisterClient
from .models import ExecutiveOrderModel, FederalRegisterDocument

__all__ = ["FederalRegisterClient", "ExecutiveOrderModel", "FederalRegisterDocument"]
