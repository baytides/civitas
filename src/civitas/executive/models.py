"""Models for Federal Register data.

API: https://www.federalregister.gov/developers/documentation/api/v1
Source: US National Archives (Public Domain)
"""

from datetime import date

from pydantic import BaseModel


class ExecutiveOrderModel(BaseModel):
    """Executive Order from Federal Register."""

    document_number: str
    executive_order_number: int | None = None
    title: str
    signing_date: date | None = None
    publication_date: date
    president: str | None = None
    abstract: str | None = None
    full_text_xml_url: str | None = None
    pdf_url: str | None = None
    html_url: str | None = None


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
    abstract: str | None = None
    html_url: str | None = None
    pdf_url: str | None = None
    cfr_references: list[str] = []  # Affected CFR sections
