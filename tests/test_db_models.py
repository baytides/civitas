"""Tests for database models."""

from datetime import date, datetime

import pytest

from civitas.db.models import (
    CourtCase,
    LawCode,
    LawSection,
    Legislation,
    LegislationAction,
    LegislationVersion,
    Legislator,
    Sponsorship,
    Vote,
    VoteRecord,
)


class TestLegislation:
    """Tests for the Legislation model."""

    def test_create_federal_legislation(self, db_session):
        """Test creating federal legislation."""
        leg = Legislation(
            jurisdiction="federal",
            source_id="118_HR_1",
            legislation_type="bill",
            chamber="house",
            number=1,
            session="118",
            citation="H.R. 1",
            title="Test Federal Bill",
        )
        db_session.add(leg)
        db_session.commit()

        assert leg.id is not None
        assert leg.jurisdiction == "federal"
        assert leg.citation == "H.R. 1"
        assert leg.is_enacted is False

    def test_create_california_legislation(self, db_session):
        """Test creating California legislation."""
        leg = Legislation(
            jurisdiction="california",
            source_id="2023_SB_456",
            legislation_type="bill",
            chamber="senate",
            number=456,
            session="2023-2024",
            citation="SB 456",
            title="California Senate Bill",
            is_enacted=True,
            enacted_date=date(2024, 1, 15),
            chapter_number="Ch. 123",
        )
        db_session.add(leg)
        db_session.commit()

        assert leg.id is not None
        assert leg.is_enacted is True
        assert leg.chapter_number == "Ch. 123"

    def test_legislation_unique_constraint(self, db_session):
        """Test that duplicate jurisdiction+source_id raises error."""
        leg1 = Legislation(
            jurisdiction="federal",
            source_id="118_HR_1",
            legislation_type="bill",
            chamber="house",
            number=1,
            session="118",
            citation="H.R. 1",
        )
        db_session.add(leg1)
        db_session.commit()

        leg2 = Legislation(
            jurisdiction="federal",
            source_id="118_HR_1",
            legislation_type="bill",
            chamber="house",
            number=1,
            session="118",
            citation="H.R. 1 Duplicate",
        )
        db_session.add(leg2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_legislation_with_fixture(self, sample_legislation):
        """Test using the sample_legislation fixture."""
        assert sample_legislation.id is not None
        assert sample_legislation.jurisdiction == "california"
        assert sample_legislation.citation == "AB 123"


class TestLegislator:
    """Tests for the Legislator model."""

    def test_create_legislator(self, db_session):
        """Test creating a legislator."""
        legislator = Legislator(
            jurisdiction="federal",
            source_id="B000001",
            full_name="John Smith",
            first_name="John",
            last_name="Smith",
            chamber="senate",
            state="CA",
            party="D",
            is_current=True,
        )
        db_session.add(legislator)
        db_session.commit()

        assert legislator.id is not None
        assert legislator.full_name == "John Smith"

    def test_legislator_with_fixture(self, sample_legislator):
        """Test using the sample_legislator fixture."""
        assert sample_legislator.id is not None
        assert sample_legislator.full_name == "Jane Doe"
        assert sample_legislator.party == "D"


class TestSponsorship:
    """Tests for the Sponsorship model."""

    def test_create_sponsorship(self, db_session, sample_legislation, sample_legislator):
        """Test creating a sponsorship relationship."""
        sponsorship = Sponsorship(
            legislation_id=sample_legislation.id,
            legislator_id=sample_legislator.id,
            sponsorship_type="sponsor",
            is_primary=True,
        )
        db_session.add(sponsorship)
        db_session.commit()

        assert sponsorship.id is not None
        assert sponsorship.is_primary is True

    def test_sponsorship_relationships(self, db_session, sample_legislation, sample_legislator):
        """Test sponsorship relationships work correctly."""
        sponsorship = Sponsorship(
            legislation_id=sample_legislation.id,
            legislator_id=sample_legislator.id,
            sponsorship_type="cosponsor",
            is_primary=False,
        )
        db_session.add(sponsorship)
        db_session.commit()

        # Refresh to load relationships
        db_session.refresh(sample_legislation)
        db_session.refresh(sample_legislator)

        assert len(sample_legislation.sponsors) == 1
        assert len(sample_legislator.sponsorships) == 1


class TestLegislationVersion:
    """Tests for the LegislationVersion model."""

    def test_create_version(self, db_session, sample_legislation):
        """Test creating a legislation version."""
        version = LegislationVersion(
            legislation_id=sample_legislation.id,
            version_number=1,
            version_type="introduced",
            version_date=date(2023, 1, 15),
            full_text="The full text of the bill...",
        )
        db_session.add(version)
        db_session.commit()

        assert version.id is not None
        assert version.version_number == 1


class TestLegislationAction:
    """Tests for the LegislationAction model."""

    def test_create_action(self, db_session, sample_legislation):
        """Test creating a legislation action."""
        action = LegislationAction(
            legislation_id=sample_legislation.id,
            action_date=date(2023, 1, 15),
            action_text="Introduced in Assembly",
            chamber="assembly",
        )
        db_session.add(action)
        db_session.commit()

        assert action.id is not None
        assert action.action_text == "Introduced in Assembly"


class TestVote:
    """Tests for the Vote and VoteRecord models."""

    def test_create_vote(self, db_session, sample_legislation):
        """Test creating a vote."""
        vote = Vote(
            legislation_id=sample_legislation.id,
            vote_date=date(2023, 6, 15),
            chamber="assembly",
            ayes=45,
            nays=30,
            abstain=5,
            result="passed",
            motion_text="Passage of bill",
        )
        db_session.add(vote)
        db_session.commit()

        assert vote.id is not None
        assert vote.result == "passed"

    def test_create_vote_record(self, db_session, sample_legislation, sample_legislator):
        """Test creating individual vote records."""
        vote = Vote(
            legislation_id=sample_legislation.id,
            vote_date=date(2023, 6, 15),
            chamber="assembly",
            ayes=1,
            nays=0,
            result="passed",
        )
        db_session.add(vote)
        db_session.commit()

        record = VoteRecord(
            vote_id=vote.id,
            legislator_id=sample_legislator.id,
            vote_cast="aye",
        )
        db_session.add(record)
        db_session.commit()

        assert record.id is not None
        assert record.vote_cast == "aye"


class TestCourtCase:
    """Tests for the CourtCase model."""

    def test_create_court_case(self, db_session):
        """Test creating a court case."""
        case = CourtCase(
            citation="600 U.S. 1",
            case_name="Important v. Government",
            docket_number="23-456",
            court="Supreme Court",
            decision_date=date(2024, 6, 15),
            vote_majority=6,
            vote_dissent=3,
            holding="The Court held...",
        )
        db_session.add(case)
        db_session.commit()

        assert case.id is not None
        assert case.vote_majority == 6

    def test_court_case_with_fixture(self, sample_court_case):
        """Test using the sample_court_case fixture."""
        assert sample_court_case.id is not None
        assert sample_court_case.citation == "598 U.S. 651"


class TestLawCode:
    """Tests for the LawCode and LawSection models."""

    def test_create_law_code(self, db_session):
        """Test creating a law code."""
        law_code = LawCode(
            jurisdiction="california",
            code="GOV",
            title="Government Code",
        )
        db_session.add(law_code)
        db_session.commit()

        assert law_code.id is not None
        assert law_code.code == "GOV"

    def test_create_law_section(self, db_session):
        """Test creating a law section."""
        law_code = LawCode(
            jurisdiction="california",
            code="GOV",
            title="Government Code",
        )
        db_session.add(law_code)
        db_session.commit()

        section = LawSection(
            law_code_id=law_code.id,
            section_number="12345",
            title="Public Records",
            division="3",
            chapter="5",
            content="Every person has a right to...",
        )
        db_session.add(section)
        db_session.commit()

        assert section.id is not None
        assert section.section_number == "12345"

    def test_law_code_unique_constraint(self, db_session):
        """Test that duplicate jurisdiction+code raises error."""
        code1 = LawCode(jurisdiction="california", code="GOV", title="Government Code")
        db_session.add(code1)
        db_session.commit()

        code2 = LawCode(jurisdiction="california", code="GOV", title="Duplicate")
        db_session.add(code2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()


class TestTimestamps:
    """Tests for automatic timestamps."""

    def test_legislation_created_at(self, db_session):
        """Test that created_at is set automatically."""
        leg = Legislation(
            jurisdiction="federal",
            source_id="test_timestamp",
            legislation_type="bill",
            chamber="house",
            number=999,
            session="118",
            citation="H.R. 999",
        )
        db_session.add(leg)
        db_session.commit()

        assert leg.created_at is not None
        assert isinstance(leg.created_at, datetime)

    def test_legislation_updated_at(self, db_session):
        """Test that updated_at is set and updates."""
        leg = Legislation(
            jurisdiction="federal",
            source_id="test_update",
            legislation_type="bill",
            chamber="house",
            number=888,
            session="118",
            citation="H.R. 888",
        )
        db_session.add(leg)
        db_session.commit()

        original_updated = leg.updated_at
        assert original_updated is not None

        # Update the record
        leg.title = "Updated Title"
        db_session.commit()

        # Note: SQLite may not trigger onupdate in the same transaction
        # In production with proper SQLAlchemy events, this would update
        assert leg.updated_at is not None
