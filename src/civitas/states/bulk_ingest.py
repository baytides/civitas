"""Bulk data ingestion from Open States PostgreSQL dumps.

This module provides functionality to import state legislative data from
Open States' monthly PostgreSQL dumps, bypassing the 500 requests/day API limit.

Data Source: https://open.pluralpolicy.com/data/
License: Public Domain (CC0-1.0)

The dump is in PostgreSQL custom format and contains:
- opencivicdata_bill - State legislation
- opencivicdata_person - State legislators
- opencivicdata_organization - Chambers, committees
- opencivicdata_votecount - Roll call votes
- opencivicdata_jurisdiction - State/jurisdiction info
"""

import subprocess
from collections.abc import Generator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@dataclass
class BulkStateBill:
    """A state bill from OpenStates bulk data."""

    id: str
    identifier: str  # e.g., "HB 123"
    title: str
    jurisdiction_id: str  # e.g., "ocd-jurisdiction/country:us/state:ca/government"
    session: str
    from_organization_id: str | None = None
    classification: list[str] = field(default_factory=list)
    subject: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class BulkStateLegislator:
    """A state legislator from OpenStates bulk data."""

    id: str
    name: str
    jurisdiction_id: str
    party: str | None = None
    image: str | None = None
    email: str | None = None
    current_role: dict | None = None
    created_at: datetime | None = None


class OpenStatesBulkIngester:
    """Ingest state legislative data from OpenStates PostgreSQL dumps.

    This class provides two approaches:
    1. Direct PostgreSQL restore and query (requires PostgreSQL installed)
    2. Parse pg_restore SQL output directly (no PostgreSQL required)

    Example:
        >>> ingester = OpenStatesBulkIngester("/path/to/openstates.pgdump")
        >>> for bill in ingester.get_bills(state="ca"):
        ...     print(f"{bill.identifier}: {bill.title}")
    """

    # State code to jurisdiction ID mapping
    STATE_JURISDICTIONS = {
        "al": "ocd-jurisdiction/country:us/state:al/government",
        "ak": "ocd-jurisdiction/country:us/state:ak/government",
        "az": "ocd-jurisdiction/country:us/state:az/government",
        "ar": "ocd-jurisdiction/country:us/state:ar/government",
        "ca": "ocd-jurisdiction/country:us/state:ca/government",
        "co": "ocd-jurisdiction/country:us/state:co/government",
        "ct": "ocd-jurisdiction/country:us/state:ct/government",
        "de": "ocd-jurisdiction/country:us/state:de/government",
        "fl": "ocd-jurisdiction/country:us/state:fl/government",
        "ga": "ocd-jurisdiction/country:us/state:ga/government",
        "hi": "ocd-jurisdiction/country:us/state:hi/government",
        "id": "ocd-jurisdiction/country:us/state:id/government",
        "il": "ocd-jurisdiction/country:us/state:il/government",
        "in": "ocd-jurisdiction/country:us/state:in/government",
        "ia": "ocd-jurisdiction/country:us/state:ia/government",
        "ks": "ocd-jurisdiction/country:us/state:ks/government",
        "ky": "ocd-jurisdiction/country:us/state:ky/government",
        "la": "ocd-jurisdiction/country:us/state:la/government",
        "me": "ocd-jurisdiction/country:us/state:me/government",
        "md": "ocd-jurisdiction/country:us/state:md/government",
        "ma": "ocd-jurisdiction/country:us/state:ma/government",
        "mi": "ocd-jurisdiction/country:us/state:mi/government",
        "mn": "ocd-jurisdiction/country:us/state:mn/government",
        "ms": "ocd-jurisdiction/country:us/state:ms/government",
        "mo": "ocd-jurisdiction/country:us/state:mo/government",
        "mt": "ocd-jurisdiction/country:us/state:mt/government",
        "ne": "ocd-jurisdiction/country:us/state:ne/government",
        "nv": "ocd-jurisdiction/country:us/state:nv/government",
        "nh": "ocd-jurisdiction/country:us/state:nh/government",
        "nj": "ocd-jurisdiction/country:us/state:nj/government",
        "nm": "ocd-jurisdiction/country:us/state:nm/government",
        "ny": "ocd-jurisdiction/country:us/state:ny/government",
        "nc": "ocd-jurisdiction/country:us/state:nc/government",
        "nd": "ocd-jurisdiction/country:us/state:nd/government",
        "oh": "ocd-jurisdiction/country:us/state:oh/government",
        "ok": "ocd-jurisdiction/country:us/state:ok/government",
        "or": "ocd-jurisdiction/country:us/state:or/government",
        "pa": "ocd-jurisdiction/country:us/state:pa/government",
        "ri": "ocd-jurisdiction/country:us/state:ri/government",
        "sc": "ocd-jurisdiction/country:us/state:sc/government",
        "sd": "ocd-jurisdiction/country:us/state:sd/government",
        "tn": "ocd-jurisdiction/country:us/state:tn/government",
        "tx": "ocd-jurisdiction/country:us/state:tx/government",
        "ut": "ocd-jurisdiction/country:us/state:ut/government",
        "vt": "ocd-jurisdiction/country:us/state:vt/government",
        "va": "ocd-jurisdiction/country:us/state:va/government",
        "wa": "ocd-jurisdiction/country:us/state:wa/government",
        "wv": "ocd-jurisdiction/country:us/state:wv/government",
        "wi": "ocd-jurisdiction/country:us/state:wi/government",
        "wy": "ocd-jurisdiction/country:us/state:wy/government",
        "dc": "ocd-jurisdiction/country:us/district:dc/government",
        "pr": "ocd-jurisdiction/country:us/territory:pr/government",
    }

    def __init__(
        self,
        dump_path: str | Path,
        temp_db_name: str = "openstates_temp",
        use_temp_db: bool = True,
    ):
        """Initialize the bulk ingester.

        Args:
            dump_path: Path to the OpenStates PostgreSQL dump file
            temp_db_name: Name for temporary PostgreSQL database
            use_temp_db: If True, restore to temp DB; if False, parse SQL directly
        """
        self.dump_path = Path(dump_path)
        self.temp_db_name = temp_db_name
        self.use_temp_db = use_temp_db
        self._db_restored = False

        if not self.dump_path.exists():
            raise FileNotFoundError(f"Dump file not found: {self.dump_path}")

    def _check_postgresql(self) -> bool:
        """Check if PostgreSQL tools are available."""
        try:
            subprocess.run(
                ["pg_restore", "--version"],
                capture_output=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _dump_has_schema(self) -> bool:
        """Return True if the dump includes schema (table definitions)."""
        try:
            result = subprocess.run(
                ["pg_restore", "-l", str(self.dump_path)],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError:
            return False

        for line in result.stdout.splitlines():
            if " TABLE " in line and "TABLE DATA" not in line:
                return True
        return False

    def _create_minimal_schema(self) -> None:
        """Create minimal tables needed for Civitas ingestion."""
        sql = """
        CREATE TABLE IF NOT EXISTS opencivicdata_bill (
            created_at TEXT,
            updated_at TEXT,
            extras TEXT,
            id TEXT,
            identifier TEXT,
            title TEXT,
            classification TEXT,
            subject TEXT,
            from_organization_id TEXT,
            legislative_session_id TEXT,
            first_action_date TEXT,
            latest_action_date TEXT,
            latest_action_description TEXT,
            latest_passage_date TEXT,
            citations TEXT
        );

        CREATE TABLE IF NOT EXISTS opencivicdata_person (
            created_at TEXT,
            updated_at TEXT,
            extras TEXT,
            id TEXT,
            name TEXT,
            family_name TEXT,
            given_name TEXT,
            image TEXT,
            gender TEXT,
            biography TEXT,
            birth_date TEXT,
            death_date TEXT,
            primary_party TEXT,
            current_jurisdiction_id TEXT,
            "current_role" TEXT,
            email TEXT
        );

        CREATE TABLE IF NOT EXISTS opencivicdata_legislativesession (
            id TEXT,
            identifier TEXT,
            name TEXT,
            classification TEXT,
            start_date TEXT,
            end_date TEXT,
            jurisdiction_id TEXT,
            active TEXT
        );
        """
        subprocess.run(
            ["psql", "-d", self.temp_db_name, "-v", "ON_ERROR_STOP=1", "-c", sql],
            check=True,
            capture_output=True,
            text=True,
        )

    def _restore_to_temp_db(self) -> None:
        """Restore the dump to a temporary PostgreSQL database."""
        if self._db_restored:
            return

        console.print(f"[blue]Restoring dump to temporary database: {self.temp_db_name}[/blue]")

        # Drop existing temp database if exists
        subprocess.run(
            ["dropdb", "--if-exists", self.temp_db_name],
            capture_output=True,
        )

        # Create new database
        subprocess.run(
            ["createdb", self.temp_db_name],
            check=True,
        )

        has_schema = self._dump_has_schema()

        if not has_schema:
            console.print("[yellow]Dump appears data-only; creating minimal schema[/yellow]")
            self._create_minimal_schema()

        # Restore the dump
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Restoring PostgreSQL dump...", total=None)

            if has_schema:
                result = subprocess.run(
                    [
                        "pg_restore",
                        "-d",
                        self.temp_db_name,
                        "--no-owner",
                        "--no-privileges",
                        str(self.dump_path),
                    ],
                    capture_output=True,
                    text=True,
                )
            else:
                result = subprocess.run(
                    [
                        "pg_restore",
                        "-d",
                        self.temp_db_name,
                        "--data-only",
                        "--schema=public",
                        "--no-owner",
                        "--no-privileges",
                        "--table=opencivicdata_bill",
                        "--table=opencivicdata_person",
                        "--table=opencivicdata_legislativesession",
                        str(self.dump_path),
                    ],
                    capture_output=True,
                    text=True,
                )

            # pg_restore may return non-zero for warnings, check stderr
            if result.returncode != 0 and "error" in result.stderr.lower():
                raise RuntimeError(f"pg_restore failed: {result.stderr}")

        self._db_restored = True
        console.print("[green]Database restored successfully[/green]")

    def _query_db(self, sql: str) -> list[dict]:
        """Execute a SQL query against the temp database."""
        if not self._db_restored:
            self._restore_to_temp_db()

        result = subprocess.run(
            [
                "psql",
                "-d",
                self.temp_db_name,
                "-t",  # Tuples only
                "-A",  # Unaligned output
                "-F",
                "\t",  # Tab separator
                "-c",
                sql,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse output into list of dicts
        lines = result.stdout.strip().split("\n")
        if not lines or lines == [""]:
            return []

        return [{"data": line} for line in lines if line]

    def get_bills(
        self,
        state: str | None = None,
        session: str | None = None,
        limit: int | None = None,
    ) -> Generator[BulkStateBill, None, None]:
        """Get bills from the bulk data.

        Args:
            state: Two-letter state code (e.g., "ca")
            session: Legislative session identifier
            limit: Maximum number of bills to return
        """
        if not self._check_postgresql():
            console.print("[yellow]PostgreSQL not available, using CSV export method[/yellow]")
            yield from self._get_bills_from_csv(state, session, limit)
            return

        self._restore_to_temp_db()

        where_clauses = []
        if state:
            jurisdiction = self.STATE_JURISDICTIONS.get(state.lower())
            if jurisdiction:
                where_clauses.append(f"ls.jurisdiction_id = '{jurisdiction}'")

        if session:
            where_clauses.append(f"legislative_session_id LIKE '%{session}%'")

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        limit_sql = f"LIMIT {limit}" if limit else ""

        sql = f"""
            SELECT
                b.id,
                b.identifier,
                b.title,
                ls.jurisdiction_id,
                b.legislative_session_id,
                b.from_organization_id,
                b.classification,
                b.subject,
                b.created_at,
                b.updated_at
            FROM opencivicdata_bill b
            LEFT JOIN opencivicdata_legislativesession ls
                ON ls.id = b.legislative_session_id
            WHERE {where_sql}
            ORDER BY b.updated_at DESC
            {limit_sql}
        """

        result = subprocess.run(
            [
                "psql",
                "-d",
                self.temp_db_name,
                "-t",
                "-A",
                "-F",
                "|||",  # Use unlikely separator
                "-c",
                sql,
            ],
            capture_output=True,
            text=True,
        )

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("|||")
            if len(parts) < 10:
                continue

            try:
                yield BulkStateBill(
                    id=parts[0],
                    identifier=parts[1],
                    title=parts[2],
                    jurisdiction_id=parts[3],
                    session=parts[4],
                    from_organization_id=parts[5] or None,
                    classification=self._parse_pg_array(parts[6]),
                    subject=self._parse_pg_array(parts[7]),
                    created_at=self._parse_datetime(parts[8]),
                    updated_at=self._parse_datetime(parts[9]),
                )
            except (ValueError, IndexError) as e:
                console.print(f"[yellow]Skipping malformed bill record: {e}[/yellow]")
                continue

    def get_legislators(
        self,
        state: str | None = None,
        limit: int | None = None,
    ) -> Generator[BulkStateLegislator, None, None]:
        """Get legislators from the bulk data.

        Args:
            state: Two-letter state code
            limit: Maximum number of legislators to return
        """
        if not self._check_postgresql():
            console.print("[yellow]PostgreSQL not available[/yellow]")
            return

        self._restore_to_temp_db()

        where_clauses = []
        if state:
            jurisdiction = self.STATE_JURISDICTIONS.get(state.lower())
            if jurisdiction:
                where_clauses.append(f"current_jurisdiction_id = '{jurisdiction}'")

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        limit_sql = f"LIMIT {limit}" if limit else ""

        sql = f"""
            SELECT
                id,
                name,
                image,
                email,
                created_at,
                primary_party,
                current_jurisdiction_id
            FROM opencivicdata_person
            WHERE {where_sql}
            ORDER BY name
            {limit_sql}
        """

        result = subprocess.run(
            [
                "psql",
                "-d",
                self.temp_db_name,
                "-t",
                "-A",
                "-F",
                "|||",
                "-c",
                sql,
            ],
            capture_output=True,
            text=True,
        )

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("|||")
            if len(parts) < 7:
                continue

            try:
                yield BulkStateLegislator(
                    id=parts[0],
                    name=parts[1],
                    jurisdiction_id=parts[6],
                    image=parts[2] or None,
                    email=parts[3] or None,
                    party=parts[5] or None,
                    created_at=self._parse_datetime(parts[4]),
                )
            except (ValueError, IndexError) as e:
                console.print(f"[yellow]Skipping malformed legislator record: {e}[/yellow]")
                continue

    def get_statistics(self) -> dict:
        """Get statistics about the bulk data."""
        if not self._check_postgresql():
            return {"error": "PostgreSQL not available"}

        self._restore_to_temp_db()

        stats = {}

        # Count bills by jurisdiction
        sql = """
            SELECT
                ls.jurisdiction_id,
                COUNT(*) as count
            FROM opencivicdata_bill b
            LEFT JOIN opencivicdata_legislativesession ls
                ON ls.id = b.legislative_session_id
            WHERE ls.jurisdiction_id IS NOT NULL
            GROUP BY ls.jurisdiction_id
            ORDER BY count DESC
        """

        result = subprocess.run(
            [
                "psql",
                "-d",
                self.temp_db_name,
                "-t",
                "-A",
                "-F",
                "|",
                "-c",
                sql,
            ],
            capture_output=True,
            text=True,
        )

        bills_by_state = {}
        for line in result.stdout.strip().split("\n"):
            if not line or "|" not in line:
                continue
            parts = line.split("|")
            jurisdiction = parts[0]
            count = int(parts[1])
            # Extract state code from jurisdiction
            if "/state:" in jurisdiction:
                state = jurisdiction.split("/state:")[1].split("/")[0]
                bills_by_state[state.upper()] = count

        stats["bills_by_state"] = bills_by_state
        stats["total_bills"] = sum(bills_by_state.values())

        # Count people
        result = subprocess.run(
            [
                "psql",
                "-d",
                self.temp_db_name,
                "-t",
                "-A",
                "-c",
                "SELECT COUNT(*) FROM opencivicdata_person",
            ],
            capture_output=True,
            text=True,
        )
        stats["total_legislators"] = int(result.stdout.strip()) if result.stdout.strip() else 0

        return stats

    def _get_bills_from_csv(
        self,
        state: str | None,
        session: str | None,
        limit: int | None,
    ) -> Generator[BulkStateBill, None, None]:
        """Extract bills by converting dump to CSV (fallback method)."""
        # This method would export specific tables to CSV first
        # For now, just indicate PostgreSQL is required
        console.print("[red]CSV export method not yet implemented.[/red]")
        console.print("Please install PostgreSQL to use bulk ingestion.")
        return
        yield  # Make this a generator

    def _parse_pg_array(self, value: str) -> list[str]:
        """Parse PostgreSQL array format {a,b,c} to Python list."""
        if not value or value == "{}":
            return []
        # Remove braces and split
        value = value.strip("{}")
        if not value:
            return []
        return [v.strip('"') for v in value.split(",")]

    def _parse_datetime(self, value: str) -> datetime | None:
        """Parse datetime string from PostgreSQL."""
        if not value or value == "":
            return None
        try:
            # Handle various PostgreSQL datetime formats
            if "." in value:
                value = value.split(".")[0]  # Remove microseconds
            if "+" in value:
                value = value.split("+")[0]  # Remove timezone
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def cleanup(self) -> None:
        """Drop the temporary database."""
        if self._db_restored:
            subprocess.run(
                ["dropdb", "--if-exists", self.temp_db_name],
                capture_output=True,
            )
            self._db_restored = False
            console.print(f"[blue]Cleaned up temporary database: {self.temp_db_name}[/blue]")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.cleanup()


def download_bulk_data(
    output_dir: str | Path = "/opt/civitas/data/openstates",
    year_month: str | None = None,
) -> Path:
    """Download the OpenStates bulk PostgreSQL dump.

    Args:
        output_dir: Directory to save the dump
        year_month: Specific month in YYYY-MM format (default: current month)

    Returns:
        Path to the downloaded dump file
    """
    import httpx

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if year_month is None:
        year_month = datetime.now().strftime("%Y-%m")

    url = f"https://data.openstates.org/postgres/monthly/{year_month}-public.pgdump"
    output_file = output_dir / f"openstates-{year_month}.pgdump"

    console.print(f"[blue]Downloading OpenStates bulk data for {year_month}...[/blue]")
    console.print(f"URL: {url}")
    console.print(f"Output: {output_file}")
    console.print("[yellow]This is approximately 9GB and may take a while.[/yellow]")

    with httpx.stream("GET", url, follow_redirects=True, timeout=None) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))

        with open(output_file, "wb") as f:
            with Progress(console=console) as progress:
                task = progress.add_task(
                    "Downloading...",
                    total=total or None,
                )
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    progress.update(task, advance=len(chunk))

    console.print(f"[green]Downloaded: {output_file}[/green]")

    # Create latest symlink
    latest_link = output_dir / "openstates-latest.pgdump"
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    latest_link.symlink_to(output_file.name)

    return output_file
