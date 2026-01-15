"""Data ingestion pipeline for loading data into the unified database."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from civitas.california.client import CaliforniaLegislatureClient
from civitas.california.models import Bill as CABill
from civitas.california.models import BillVersion as CABillVersion
from civitas.california.models import BillHistory as CABillHistory
from civitas.california.models import BillSummaryVote as CABillSummaryVote
from civitas.california.models import BillDetailVote as CABillDetailVote
from civitas.california.models import Legislator as CALegislator
from civitas.california.models import LawCode as CALawCode
from civitas.california.models import LawSection as CALawSection

from civitas.congress.client import CongressClient
from civitas.congress.models import BillSummary as FedBillSummary

from civitas.db.models import (
    Base,
    Legislation,
    LegislationVersion,
    LegislationAction,
    Legislator,
    Vote,
    VoteRecord,
    LawCode,
    LawSection,
)


class DataIngester:
    """Ingests data from various sources into the unified database."""

    def __init__(self, db_path: str = "civitas.db"):
        """Initialize the ingester.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()

    # =========================================================================
    # California Legislature Ingestion
    # =========================================================================

    def ingest_california_session(
        self,
        session_year: int,
        data_dir: Optional[Path] = None,
        batch_size: int = 1000,
        progress_callback: Optional[callable] = None,
    ) -> dict[str, int]:
        """Ingest California Legislature data for a session.

        Args:
            session_year: Session year (e.g., 2023)
            data_dir: Directory containing downloaded data
            batch_size: Number of records to commit at once
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary with counts of ingested records
        """
        client = CaliforniaLegislatureClient(data_dir=data_dir or Path("data/california"))
        data_path = client.data_dir / str(session_year)

        if not data_path.exists():
            print(f"Downloading California {session_year} session...")
            data_path = client.download_session(session_year)

        counts = {
            "bills": 0,
            "versions": 0,
            "actions": 0,
            "legislators": 0,
            "votes": 0,
            "law_codes": 0,
            "law_sections": 0,
        }

        session = self.get_session()

        try:
            # Ingest law codes first (reference data)
            print("Ingesting California law codes...")
            for code in client.parse_law_codes(data_path):
                self._ingest_ca_law_code(session, code)
                counts["law_codes"] += 1
            session.commit()

            # Ingest legislators
            print("Ingesting California legislators...")
            legislator_map = {}  # name -> id mapping
            for leg in client.parse_legislators(data_path):
                db_leg = self._ingest_ca_legislator(session, leg)
                if db_leg:
                    legislator_map[leg.legislator_name] = db_leg.id
                counts["legislators"] += 1
            session.commit()

            # Build bill version map for subjects
            print("Building bill version index...")
            version_map = {}  # bill_id -> BillVersion
            for version in client.parse_bill_versions(data_path):
                if version.bill_id not in version_map:
                    version_map[version.bill_id] = version
                elif version.version_num > version_map[version.bill_id].version_num:
                    version_map[version.bill_id] = version

            # Ingest bills
            print("Ingesting California bills...")
            bill_id_map = {}  # source_id -> db_id
            for i, bill in enumerate(client.parse_bills(data_path)):
                version = version_map.get(bill.bill_id)
                db_bill = self._ingest_ca_bill(session, bill, version)
                if db_bill:
                    bill_id_map[bill.bill_id] = db_bill.id
                counts["bills"] += 1

                if i > 0 and i % batch_size == 0:
                    session.commit()
                    if progress_callback:
                        progress_callback("bills", counts["bills"])

            session.commit()

            # Ingest bill history/actions
            print("Ingesting California bill actions...")
            for i, action in enumerate(client.parse_bill_history(data_path)):
                if action.bill_id in bill_id_map:
                    self._ingest_ca_action(session, action, bill_id_map[action.bill_id])
                    counts["actions"] += 1

                if i > 0 and i % batch_size == 0:
                    session.commit()

            session.commit()

            # Ingest votes
            print("Ingesting California votes...")
            for i, vote in enumerate(client.parse_votes(data_path)):
                if vote.bill_id in bill_id_map:
                    self._ingest_ca_vote(session, vote, bill_id_map[vote.bill_id])
                    counts["votes"] += 1

                if i > 0 and i % batch_size == 0:
                    session.commit()

            session.commit()

            print(f"California {session_year} ingestion complete: {counts}")
            return counts

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
            client.close()

    def _ingest_ca_bill(
        self,
        session: Session,
        bill: CABill,
        version: Optional[CABillVersion] = None,
    ) -> Optional[Legislation]:
        """Ingest a California bill."""
        # Check if already exists
        existing = session.query(Legislation).filter_by(
            jurisdiction="california",
            source_id=bill.bill_id,
        ).first()

        if existing:
            return existing

        # Map measure type to legislation type
        type_map = {
            "AB": "bill",
            "SB": "bill",
            "ACA": "constitutional_amendment",
            "SCA": "constitutional_amendment",
            "ACR": "concurrent_resolution",
            "SCR": "concurrent_resolution",
            "AJR": "joint_resolution",
            "SJR": "joint_resolution",
            "AR": "resolution",
            "SR": "resolution",
        }

        chamber_map = {
            "AB": "house",
            "ACA": "house",
            "ACR": "house",
            "AJR": "house",
            "AR": "house",
            "SB": "senate",
            "SCA": "senate",
            "SCR": "senate",
            "SJR": "senate",
            "SR": "senate",
        }

        db_bill = Legislation(
            jurisdiction="california",
            source_id=bill.bill_id,
            legislation_type=type_map.get(bill.measure_type, "bill"),
            number=bill.measure_num,
            chamber=chamber_map.get(bill.measure_type, "house"),
            session=bill.session_year,
            citation=bill.citation,
            title=version.subject if version else None,
            status=bill.current_status,
            current_location=bill.current_location,
            is_enacted=bill.is_chaptered,
            chapter_number=bill.chapter_num,
            enacted_date=None,  # Would need to parse from history
            full_text=version.bill_xml if version else None,
            summary=version.subject if version else None,
        )

        session.add(db_bill)
        session.flush()
        return db_bill

    def _ingest_ca_action(
        self,
        session: Session,
        action: CABillHistory,
        legislation_id: int,
    ) -> None:
        """Ingest a California bill action."""
        if not action.action_date:
            return

        db_action = LegislationAction(
            legislation_id=legislation_id,
            action_date=action.action_date.date() if isinstance(action.action_date, datetime) else action.action_date,
            action_text=action.action or "",
            action_code=action.action_code,
            committee=action.primary_location,
        )
        session.add(db_action)

    def _ingest_ca_vote(
        self,
        session: Session,
        vote: CABillSummaryVote,
        legislation_id: int,
    ) -> None:
        """Ingest a California vote."""
        db_vote = Vote(
            legislation_id=legislation_id,
            vote_date=vote.vote_date_time.date() if isinstance(vote.vote_date_time, datetime) else vote.vote_date_time,
            chamber="house" if vote.location_code.startswith("A") else "senate",
            ayes=vote.ayes,
            nays=vote.noes,
            abstain=vote.abstain,
            result=vote.vote_result,
            source_id=f"{vote.bill_id}_{vote.vote_date_time}_{vote.motion_id}",
        )
        session.add(db_vote)

    def _ingest_ca_legislator(
        self,
        session: Session,
        leg: CALegislator,
    ) -> Optional[Legislator]:
        """Ingest a California legislator."""
        # Check if exists
        existing = session.query(Legislator).filter_by(
            jurisdiction="california",
            full_name=leg.full_name,
        ).first()

        if existing:
            return existing

        db_leg = Legislator(
            jurisdiction="california",
            source_id=leg.district,
            full_name=leg.full_name,
            first_name=leg.first_name,
            last_name=leg.last_name,
            chamber="house" if leg.house_type == "A" else "senate" if leg.house_type == "S" else None,
            state="California",
            district=leg.district,
            party=leg.party,
            is_current=leg.active_legislator == "Y",
        )
        session.add(db_leg)
        session.flush()
        return db_leg

    def _ingest_ca_law_code(
        self,
        session: Session,
        code: CALawCode,
    ) -> None:
        """Ingest a California law code."""
        existing = session.query(LawCode).filter_by(
            jurisdiction="california",
            code=code.code,
        ).first()

        if not existing:
            db_code = LawCode(
                jurisdiction="california",
                code=code.code,
                title=code.title or code.code,
            )
            session.add(db_code)

    # =========================================================================
    # Federal Congress Ingestion
    # =========================================================================

    def ingest_federal_congress(
        self,
        congress: int,
        laws_only: bool = True,
        batch_size: int = 100,
        progress_callback: Optional[callable] = None,
    ) -> dict[str, int]:
        """Ingest federal legislation from Congress.gov.

        Args:
            congress: Congress number (e.g., 118)
            laws_only: Only ingest enacted laws (faster)
            batch_size: Number of records per API call
            progress_callback: Optional callback for progress

        Returns:
            Dictionary with counts of ingested records
        """
        client = CongressClient()
        counts = {"bills": 0, "laws": 0}

        session = self.get_session()

        try:
            offset = 0
            total = None

            while True:
                print(f"Fetching federal laws (offset {offset})...")
                response = client.get_laws(congress=congress, limit=batch_size, offset=offset)

                if total is None:
                    total = response.get("pagination", {}).get("count", 0)
                    print(f"Total laws in Congress {congress}: {total}")

                bills = response.get("bills", [])
                if not bills:
                    break

                for bill_data in bills:
                    db_bill = self._ingest_federal_bill(session, bill_data, congress)
                    if db_bill:
                        counts["bills"] += 1
                        if db_bill.is_enacted:
                            counts["laws"] += 1

                session.commit()

                if progress_callback:
                    progress_callback("laws", counts["laws"])

                offset += batch_size
                if offset >= total:
                    break

            print(f"Federal Congress {congress} ingestion complete: {counts}")
            return counts

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
            client.close()

    def _ingest_federal_bill(
        self,
        session: Session,
        bill_data: dict,
        congress: int,
    ) -> Optional[Legislation]:
        """Ingest a federal bill."""
        source_id = f"{congress}_{bill_data['type']}_{bill_data['number']}"

        # Check if exists
        existing = session.query(Legislation).filter_by(
            jurisdiction="federal",
            source_id=source_id,
        ).first()

        if existing:
            return existing

        # Map type
        type_map = {
            "HR": ("bill", "house"),
            "S": ("bill", "senate"),
            "HJRES": ("joint_resolution", "house"),
            "SJRES": ("joint_resolution", "senate"),
            "HCONRES": ("concurrent_resolution", "house"),
            "SCONRES": ("concurrent_resolution", "senate"),
            "HRES": ("resolution", "house"),
            "SRES": ("resolution", "senate"),
        }

        leg_type, chamber = type_map.get(bill_data["type"], ("bill", "house"))

        # Parse public law number
        public_law = None
        is_enacted = False
        if bill_data.get("laws"):
            for law in bill_data["laws"]:
                if law.get("type") == "Public Law":
                    public_law = f"P.L. {congress}-{law['number']}"
                    is_enacted = True
                    break

        # Parse latest action date
        last_action_date = None
        if bill_data.get("latestAction", {}).get("actionDate"):
            try:
                last_action_date = datetime.strptime(
                    bill_data["latestAction"]["actionDate"],
                    "%Y-%m-%d"
                ).date()
            except (ValueError, TypeError):
                pass

        # Format citation
        citation_map = {
            "HR": "H.R.",
            "S": "S.",
            "HJRES": "H.J.Res.",
            "SJRES": "S.J.Res.",
            "HCONRES": "H.Con.Res.",
            "SCONRES": "S.Con.Res.",
            "HRES": "H.Res.",
            "SRES": "S.Res.",
        }
        citation = f"{citation_map.get(bill_data['type'], bill_data['type'])} {bill_data['number']}"

        db_bill = Legislation(
            jurisdiction="federal",
            source_id=source_id,
            legislation_type=leg_type,
            number=int(bill_data["number"]),
            chamber=chamber,
            session=str(congress),
            citation=citation,
            title=bill_data.get("title"),
            last_action_date=last_action_date,
            is_enacted=is_enacted,
            public_law_number=public_law,
            source_url=bill_data.get("url"),
        )

        session.add(db_bill)
        session.flush()
        return db_bill

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_stats(self) -> dict:
        """Get database statistics."""
        session = self.get_session()
        try:
            return {
                "total_legislation": session.query(Legislation).count(),
                "federal_legislation": session.query(Legislation).filter_by(jurisdiction="federal").count(),
                "california_legislation": session.query(Legislation).filter_by(jurisdiction="california").count(),
                "enacted_laws": session.query(Legislation).filter_by(is_enacted=True).count(),
                "legislators": session.query(Legislator).count(),
                "votes": session.query(Vote).count(),
                "actions": session.query(LegislationAction).count(),
                "law_codes": session.query(LawCode).count(),
            }
        finally:
            session.close()
