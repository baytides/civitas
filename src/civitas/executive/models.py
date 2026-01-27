"""Models for Federal Register data.

API: https://www.federalregister.gov/developers/documentation/api/v1
Source: US National Archives (Public Domain)
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class ExecutiveOrderModel(BaseModel):
    """Executive Order from Federal Register."""

    document_number: str
    executive_order_number: Optional[int] = None
    title: str
    signing_date: Optional[date] = None
    publication_date: date
    president: Optional[str] = None
    abstract: Optional[str] = None
    full_text_xml_url: Optional[str] = None
    pdf_url: Optional[str] = None
    html_url: Optional[str] = None


class FederalRegisterDocument(BaseModel):
    """Any Federal Register document.

    Document types:
    - PRESDOCU: Presidential documents (EOs, proclamations, memos)
    - RULE: Final rules
    - PRORULE: Proposed rules
    - NOTICE: Agency notices
    """

    document_number: str
    document_type: str  # "PRESDOCU", "RULE", "PRORULE", "NOTICE"
    title: str
    publication_date: date
    agencies: list[str] = []
    abstract: Optional[str] = None
    html_url: Optional[str] = None
    pdf_url: Optional[str] = None
    cfr_references: list[str] = []  # Affected CFR sections
