"""California Legislature data client.

Downloads and parses data from https://downloads.leginfo.legislature.ca.gov/
"""

from __future__ import annotations

import csv
import zipfile
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from civitas.california.models import (
    Bill,
    BillAnalysis,
    BillDetailVote,
    BillHistory,
    BillMotion,
    BillSummaryVote,
    BillVersion,
    BillVersionAuthor,
    CommitteeHearing,
    LawCode,
    LawSection,
    Legislator,
    LocationCode,
    VetoMessage,
)

BASE_URL = "https://downloads.leginfo.legislature.ca.gov"

T = TypeVar("T", bound=BaseModel)


# Mapping of .dat files to their model classes and field names
TABLE_CONFIGS: dict[str, dict[str, Any]] = {
    "BILL_TBL.dat": {
        "model": Bill,
        "fields": [
            "bill_id", "session_year", "session_num", "measure_type", "measure_num",
            "measure_state", "chapter_year", "chapter_type", "chapter_session_num",
            "chapter_num", "latest_bill_version_id", "active_flg", "trans_uid",
            "trans_update", "current_location", "current_secondary_loc",
            "current_house", "current_status", "days_31st_in_print"
        ],
    },
    "BILL_VERSION_TBL.dat": {
        "model": BillVersion,
        "fields": [
            "bill_version_id", "bill_id", "version_num", "bill_version_action_date",
            "bill_version_action", "request_num", "subject", "vote_required",
            "appropriation", "fiscal_committee", "local_program", "substantive_changes",
            "urgency", "taxlevy", "bill_xml", "active_flg", "trans_uid", "trans_update"
        ],
    },
    "BILL_VERSION_AUTHORS_TBL.dat": {
        "model": BillVersionAuthor,
        "fields": [
            "bill_version_id", "type", "house", "name", "contribution",
            "committee_members", "active_flg", "trans_uid", "trans_update",
            "primary_author_flg"
        ],
    },
    "BILL_HISTORY_TBL.dat": {
        "model": BillHistory,
        "fields": [
            "bill_id", "bill_history_id", "action_date", "action", "trans_uid",
            "trans_update_dt", "action_sequence", "action_code", "action_status",
            "primary_location", "secondary_location", "ternary_location", "end_status"
        ],
    },
    "BILL_ANALYSIS_TBL.dat": {
        "model": BillAnalysis,
        "fields": [
            "analysis_id", "bill_id", "house", "analysis_type", "committee_code",
            "committee_name", "amendment_author", "analysis_date", "amendment_date",
            "page_num", "source_doc", "released_floor", "active_flg", "trans_uid",
            "trans_update"
        ],
    },
    "BILL_SUMMARY_VOTE_TBL.dat": {
        "model": BillSummaryVote,
        "fields": [
            "bill_id", "location_code", "vote_date_time", "vote_date_seq",
            "motion_id", "ayes", "noes", "abstain", "vote_result", "trans_uid",
            "trans_update", "file_item_num", "file_location", "display_lines",
            "session_date"
        ],
    },
    "BILL_DETAIL_VOTE_TBL.dat": {
        "model": BillDetailVote,
        "fields": [
            "bill_id", "location_code", "legislator_name", "vote_date_time",
            "vote_date_seq", "vote_code", "motion_id", "trans_uid", "trans_update",
            "member_order", "session_date", "speaker"
        ],
    },
    "BILL_MOTION_TBL.dat": {
        "model": BillMotion,
        "fields": ["motion_id", "motion_text", "trans_uid", "trans_update"],
    },
    "LEGISLATOR_TBL.dat": {
        "model": Legislator,
        "fields": [
            "district", "session_year", "legislator_name", "house_type", "author_name",
            "first_name", "last_name", "middle_initial", "name_suffix", "name_title",
            "web_name_title", "party", "active_flg", "trans_uid", "trans_update",
            "active_legislator"
        ],
    },
    "LAW_SECTION_TBL.dat": {
        "model": LawSection,
        "fields": [
            "id", "law_code", "section_num", "op_statues", "op_chapter", "op_section",
            "effective_date", "law_section_version_id", "division", "title", "part",
            "chapter", "article", "history", "content_xml", "active_flg", "trans_uid",
            "trans_update"
        ],
    },
    "CODES_TBL.dat": {
        "model": LawCode,
        "fields": ["code", "title"],
    },
    "VETO_MESSAGE_TBL.dat": {
        "model": VetoMessage,
        "fields": ["bill_id", "veto_date", "message", "trans_uid", "trans_update"],
    },
    "COMMITTEE_HEARING_TBL.dat": {
        "model": CommitteeHearing,
        "fields": [
            "bill_id", "committee_type", "committee_nr", "hearing_date",
            "location_code", "trans_uid", "trans_update_date"
        ],
    },
    "LOCATION_CODE_TBL.dat": {
        "model": LocationCode,
        "fields": [
            "session_year", "location_code", "location_type", "consent_calendar_code",
            "description", "long_description", "active_flg", "trans_uid", "trans_update",
            "inactive_file_flg"
        ],
    },
}


def _parse_value(value: str, field_name: str) -> Any:
    """Parse a string value into appropriate Python type."""
    if value == "" or value == "\\N":
        return None

    # Handle datetime fields
    if "date" in field_name.lower() or field_name in ("trans_update", "trans_update_dt"):
        try:
            # Try common datetime formats
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            return value  # Return as string if no format matches
        except Exception:
            return value

    # Handle numeric fields
    if field_name in ("measure_num", "version_num", "analysis_id", "bill_history_id",
                      "motion_id", "vote_date_seq", "ayes", "noes", "abstain",
                      "committee_nr", "member_order", "action_sequence", "page_num"):
        try:
            return int(float(value))  # Handle "123.0" format
        except (ValueError, TypeError):
            return None

    return value


def _parse_row(row: list[str], fields: list[str]) -> dict[str, Any]:
    """Parse a tab-delimited row into a dictionary."""
    result = {}
    for i, field in enumerate(fields):
        if i < len(row):
            result[field] = _parse_value(row[i], field)
        else:
            result[field] = None
    return result


class CaliforniaLegislatureClient:
    """Client for downloading and parsing California Legislature data."""

    def __init__(self, data_dir: Path | None = None):
        """Initialize the client.

        Args:
            data_dir: Directory for storing downloaded data. Defaults to ./data/california
        """
        self.data_dir = data_dir or Path("data/california")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._client = httpx.Client(timeout=120.0)  # Large files need longer timeout

    def download_session(self, year: int, extract: bool = True) -> Path:
        """Download data for a legislative session.

        Args:
            year: Session year (e.g., 2023 for 2023-2024 session)
            extract: Whether to extract the zip file

        Returns:
            Path to downloaded/extracted data
        """
        url = f"{BASE_URL}/pubinfo_{year}.zip"
        zip_path = self.data_dir / f"pubinfo_{year}.zip"

        print(f"Downloading {url}...")
        response = self._client.get(url, follow_redirects=True)
        response.raise_for_status()

        zip_path.write_bytes(response.content)
        print(f"Downloaded {len(response.content) / 1024 / 1024:.1f} MB")

        if extract:
            extract_dir = self.data_dir / str(year)
            extract_dir.mkdir(exist_ok=True)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)
            print(f"Extracted to {extract_dir}")
            return extract_dir

        return zip_path

    def download_daily_update(self, day: str = "Mon") -> Path:
        """Download daily incremental update.

        Args:
            day: Day of week (Mon, Tue, Wed, Thu, Fri, Sat)

        Returns:
            Path to downloaded data
        """
        url = f"{BASE_URL}/pubinfo_{day}.zip"
        zip_path = self.data_dir / f"pubinfo_{day}.zip"

        print(f"Downloading {url}...")
        response = self._client.get(url, follow_redirects=True)
        response.raise_for_status()

        zip_path.write_bytes(response.content)

        extract_dir = self.data_dir / f"daily_{day}"
        extract_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        return extract_dir

    def list_available_sessions(self) -> list[int]:
        """List available session years (1989-present)."""
        return list(range(1989, datetime.now().year + 1, 2))

    def parse_table(
        self,
        table_name: str,
        data_path: Path,
        limit: int | None = None,
    ) -> Generator[BaseModel, None, None]:
        """Parse a .dat file and yield model instances.

        Args:
            table_name: Name of the table file (e.g., "BILL_TBL.dat")
            data_path: Path to directory containing the .dat file
            limit: Maximum number of records to parse

        Yields:
            Pydantic model instances
        """
        if table_name not in TABLE_CONFIGS:
            raise ValueError(f"Unknown table: {table_name}")

        config = TABLE_CONFIGS[table_name]
        model_class = config["model"]
        fields = config["fields"]

        dat_file = data_path / table_name
        if not dat_file.exists():
            return

        count = 0
        with open(dat_file, encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                if limit and count >= limit:
                    break

                data = _parse_row(row, fields)

                # Filter to only fields the model accepts
                model_fields = set(model_class.model_fields.keys())
                filtered_data = {k: v for k, v in data.items() if k in model_fields}

                try:
                    yield model_class(**filtered_data)
                    count += 1
                except Exception as e:
                    # Skip malformed rows
                    print(f"Warning: Could not parse row: {e}")
                    continue

    def parse_bills(self, data_path: Path, limit: int | None = None) -> Generator[Bill, None, None]:
        """Parse bill records from extracted data."""
        yield from self.parse_table("BILL_TBL.dat", data_path, limit)

    def parse_bill_versions(self, data_path: Path, limit: int | None = None) -> Generator[BillVersion, None, None]:
        """Parse bill version records."""
        yield from self.parse_table("BILL_VERSION_TBL.dat", data_path, limit)

    def parse_bill_history(self, data_path: Path, limit: int | None = None) -> Generator[BillHistory, None, None]:
        """Parse bill history/action records."""
        yield from self.parse_table("BILL_HISTORY_TBL.dat", data_path, limit)

    def parse_legislators(self, data_path: Path, limit: int | None = None) -> Generator[Legislator, None, None]:
        """Parse legislator records."""
        yield from self.parse_table("LEGISLATOR_TBL.dat", data_path, limit)

    def parse_votes(self, data_path: Path, limit: int | None = None) -> Generator[BillSummaryVote, None, None]:
        """Parse summary vote records."""
        yield from self.parse_table("BILL_SUMMARY_VOTE_TBL.dat", data_path, limit)

    def parse_detail_votes(self, data_path: Path, limit: int | None = None) -> Generator[BillDetailVote, None, None]:
        """Parse individual legislator vote records."""
        yield from self.parse_table("BILL_DETAIL_VOTE_TBL.dat", data_path, limit)

    def parse_law_codes(self, data_path: Path) -> Generator[LawCode, None, None]:
        """Parse law code records."""
        yield from self.parse_table("CODES_TBL.dat", data_path)

    def parse_law_sections(self, data_path: Path, limit: int | None = None) -> Generator[LawSection, None, None]:
        """Parse law section records."""
        yield from self.parse_table("LAW_SECTION_TBL.dat", data_path, limit)

    def parse_veto_messages(self, data_path: Path) -> Generator[VetoMessage, None, None]:
        """Parse veto message records."""
        yield from self.parse_table("VETO_MESSAGE_TBL.dat", data_path)

    def get_bills_by_session(
        self,
        session_year: int,
        measure_type: str | None = None,
        chaptered_only: bool = False,
    ) -> list[Bill]:
        """Get bills for a session, optionally filtered.

        Args:
            session_year: Session year (e.g., 2023)
            measure_type: Filter by type (AB, SB, etc.)
            chaptered_only: Only return enacted bills

        Returns:
            List of Bill objects
        """
        data_path = self.data_dir / str(session_year)
        if not data_path.exists():
            self.download_session(session_year)

        bills = []
        for bill in self.parse_bills(data_path):
            if measure_type and bill.measure_type != measure_type:
                continue
            if chaptered_only and not bill.is_chaptered:
                continue
            bills.append(bill)

        return bills

    def search_bills(
        self,
        session_year: int,
        keyword: str,
        search_subjects: bool = True,
    ) -> list[tuple[Bill, BillVersion | None]]:
        """Search bills by keyword in subject/title.

        Args:
            session_year: Session year
            keyword: Search term
            search_subjects: Whether to search bill subjects

        Returns:
            List of (Bill, BillVersion) tuples
        """
        data_path = self.data_dir / str(session_year)
        if not data_path.exists():
            self.download_session(session_year)

        keyword_lower = keyword.lower()
        results = []

        # Build version lookup
        versions_by_bill: dict[str, BillVersion] = {}
        if search_subjects:
            for version in self.parse_bill_versions(data_path):
                if version.bill_id not in versions_by_bill:
                    versions_by_bill[version.bill_id] = version
                elif version.version_num > versions_by_bill[version.bill_id].version_num:
                    versions_by_bill[version.bill_id] = version

        for bill in self.parse_bills(data_path):
            version = versions_by_bill.get(bill.bill_id)
            match = False

            # Search bill citation
            if keyword_lower in bill.citation.lower():
                match = True
            # Search subject
            elif version and version.subject and keyword_lower in version.subject.lower():
                match = True

            if match:
                results.append((bill, version))

        return results

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
