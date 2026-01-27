"""Client for Federal Register API.

API Docs: https://www.federalregister.gov/developers/documentation/api/v1
Data Source: US National Archives (Public Domain)

The Federal Register is the official daily publication for:
- Executive Orders
- Presidential Proclamations and Memos
- Federal Agency Rules and Regulations
- Notices of Federal Agencies
"""

from collections.abc import Generator
from datetime import date, timedelta

import httpx

from .models import ExecutiveOrderModel, FederalRegisterDocument


class FederalRegisterClient:
    """Client for the Federal Register API (federalregister.gov).

    Example:
        >>> client = FederalRegisterClient()
        >>> for eo in client.get_executive_orders(president="Biden", year=2024):
        ...     print(f"EO {eo.executive_order_number}: {eo.title}")
    """

    BASE_URL = "https://www.federalregister.gov/api/v1"

    # Known presidents for filtering
    PRESIDENTS = {
        "biden": "Joe Biden",
        "trump": "Donald Trump",
        "obama": "Barack Obama",
        "bush": "George W. Bush",
    }

    def __init__(self, azure_client=None):
        """Initialize Federal Register client.

        Args:
            azure_client: Optional AzureStorageClient for document storage
        """
        self._client = httpx.Client(
            base_url=self.BASE_URL,
            timeout=30.0,
            headers={"User-Agent": "Civitas/1.0 (civic data project)"},
        )
        self.azure = azure_client

    def get_executive_orders(
        self,
        president: str | None = None,
        year: int | None = None,
        limit: int = 100,
    ) -> Generator[ExecutiveOrderModel, None, None]:
        """Fetch executive orders.

        Args:
            president: Filter by president name (e.g., "Biden", "Trump")
            year: Filter by publication year
            limit: Maximum results to return

        Yields:
            ExecutiveOrderModel objects
        """
        params = {
            "conditions[type][]": "PRESDOCU",
            "conditions[presidential_document_type][]": "executive_order",
            "per_page": min(limit, 1000),
            "order": "newest",
        }

        if president:
            # Normalize president name
            normalized = self.PRESIDENTS.get(president.lower(), president)
            params["conditions[president][]"] = normalized

        if year:
            params["conditions[publication_date][year]"] = year

        response = self._client.get("/documents.json", params=params)
        response.raise_for_status()

        for doc in response.json().get("results", []):
            eo = ExecutiveOrderModel(
                document_number=doc["document_number"],
                executive_order_number=doc.get("executive_order_number"),
                title=doc["title"],
                signing_date=doc.get("signing_date"),
                publication_date=doc["publication_date"],
                president=doc.get("president", {}).get("name") if doc.get("president") else None,
                abstract=doc.get("abstract"),
                full_text_xml_url=doc.get("full_text_xml_url"),
                pdf_url=doc.get("pdf_url"),
                html_url=doc.get("html_url"),
            )

            # Store in Azure if configured
            if self.azure and eo.pdf_url:
                try:
                    pdf_response = self._client.get(eo.pdf_url)
                    if pdf_response.status_code == 200:
                        self.azure.upload_document(
                            pdf_response.content,
                            "executive_order",
                            "federal_register",
                            eo.document_number,
                            "pdf",
                        )
                except Exception:
                    pass  # Continue even if upload fails

            yield eo

    def get_recent_documents(
        self,
        document_type: str | None = None,
        agency: str | None = None,
        days: int = 30,
        limit: int = 100,
    ) -> Generator[FederalRegisterDocument, None, None]:
        """Get recent Federal Register documents.

        Args:
            document_type: Filter by type (PRESDOCU, RULE, PRORULE, NOTICE)
            agency: Filter by agency name
            days: Number of days to look back
            limit: Maximum results to return

        Yields:
            FederalRegisterDocument objects
        """
        since = date.today() - timedelta(days=days)

        params = {
            "conditions[publication_date][gte]": since.isoformat(),
            "per_page": min(limit, 1000),
            "order": "newest",
        }

        if document_type:
            params["conditions[type][]"] = document_type

        if agency:
            params["conditions[agencies][]"] = agency

        response = self._client.get("/documents.json", params=params)
        response.raise_for_status()

        for doc in response.json().get("results", []):
            yield FederalRegisterDocument(
                document_number=doc["document_number"],
                document_type=doc["type"],
                title=doc["title"],
                publication_date=doc["publication_date"],
                agencies=[a["name"] for a in doc.get("agencies", [])],
                abstract=doc.get("abstract"),
                html_url=doc.get("html_url"),
                pdf_url=doc.get("pdf_url"),
                cfr_references=[
                    f"{ref['title']} CFR {ref.get('part', '')}"
                    for ref in doc.get("cfr_references", [])
                ],
            )

    def get_agency_rules(
        self,
        agency: str,
        days: int = 90,
        include_proposed: bool = True,
    ) -> Generator[FederalRegisterDocument, None, None]:
        """Get rules from a specific agency.

        Useful for tracking regulatory changes that might align
        with Project 2025 proposals.

        Args:
            agency: Agency name (e.g., "Environmental Protection Agency")
            days: Number of days to look back
            include_proposed: Include proposed rules (not just final)

        Yields:
            FederalRegisterDocument objects
        """
        types = ["RULE"]
        if include_proposed:
            types.append("PRORULE")

        for doc_type in types:
            yield from self.get_recent_documents(
                document_type=doc_type,
                agency=agency,
                days=days,
            )

    def get_document(self, document_number: str) -> FederalRegisterDocument | None:
        """Get a specific document by number.

        Args:
            document_number: Federal Register document number

        Returns:
            FederalRegisterDocument or None if not found
        """
        try:
            response = self._client.get(f"/documents/{document_number}.json")
            response.raise_for_status()
            doc = response.json()

            return FederalRegisterDocument(
                document_number=doc["document_number"],
                document_type=doc["type"],
                title=doc["title"],
                publication_date=doc["publication_date"],
                agencies=[a["name"] for a in doc.get("agencies", [])],
                abstract=doc.get("abstract"),
                html_url=doc.get("html_url"),
                pdf_url=doc.get("pdf_url"),
            )
        except httpx.HTTPStatusError:
            return None

    def search(
        self,
        query: str,
        document_type: str | None = None,
        limit: int = 50,
    ) -> list[FederalRegisterDocument]:
        """Search Federal Register documents.

        Args:
            query: Search query string
            document_type: Filter by document type
            limit: Maximum results

        Returns:
            List of matching documents
        """
        params = {
            "conditions[term]": query,
            "per_page": min(limit, 1000),
            "order": "relevance",
        }

        if document_type:
            params["conditions[type][]"] = document_type

        response = self._client.get("/documents.json", params=params)
        response.raise_for_status()

        return [
            FederalRegisterDocument(
                document_number=doc["document_number"],
                document_type=doc["type"],
                title=doc["title"],
                publication_date=doc["publication_date"],
                agencies=[a["name"] for a in doc.get("agencies", [])],
                abstract=doc.get("abstract"),
                html_url=doc.get("html_url"),
                pdf_url=doc.get("pdf_url"),
            )
            for doc in response.json().get("results", [])
        ]

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
