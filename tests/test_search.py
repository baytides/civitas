"""Tests for FTS5 full-text search."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from civitas.db.models import Base, CourtCase, Legislation, setup_fts
from civitas.db.search import (
    count_search_results,
    search_all,
    search_court_cases,
    search_legislation,
)


@pytest.fixture
def fts_engine():
    """Create an in-memory SQLite database with FTS5 enabled."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    setup_fts(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def fts_session(fts_engine):
    """Create a database session with FTS5."""
    Session = sessionmaker(bind=fts_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def populated_db(fts_session):
    """Populate database with sample legislation for testing."""
    legislation = [
        Legislation(
            jurisdiction="federal",
            source_id="118_HR_1",
            legislation_type="bill",
            chamber="house",
            number=1,
            session="118",
            citation="H.R. 1",
            title="For the People Act",
            summary="A bill to expand voting rights and election security.",
            is_enacted=False,
        ),
        Legislation(
            jurisdiction="federal",
            source_id="118_HR_2",
            legislation_type="bill",
            chamber="house",
            number=2,
            session="118",
            citation="H.R. 2",
            title="Secure the Border Act",
            summary="A bill to secure the southern border.",
            is_enacted=False,
        ),
        Legislation(
            jurisdiction="california",
            source_id="2023_AB_1",
            legislation_type="bill",
            chamber="assembly",
            number=1,
            session="2023-2024",
            citation="AB 1",
            title="Clean Water Protection Act",
            summary="A bill to protect California water resources and ensure clean drinking water.",
            is_enacted=True,
        ),
        Legislation(
            jurisdiction="california",
            source_id="2023_SB_1",
            legislation_type="bill",
            chamber="senate",
            number=1,
            session="2023-2024",
            citation="SB 1",
            title="Climate Action Plan",
            summary="A bill to address climate change and reduce emissions.",
            is_enacted=True,
        ),
        Legislation(
            jurisdiction="federal",
            source_id="118_HR_3",
            legislation_type="bill",
            chamber="house",
            number=3,
            session="118",
            citation="H.R. 3",
            title="Environmental Protection Enhancement Act",
            summary="A bill to strengthen environmental regulations and protect water quality.",
            is_enacted=False,
        ),
    ]

    for leg in legislation:
        fts_session.add(leg)
    fts_session.commit()

    return fts_session


class TestSearchLegislation:
    """Tests for legislation search."""

    def test_simple_search(self, populated_db):
        """Test basic keyword search."""
        results = search_legislation(populated_db, "water")
        assert len(results) >= 2
        titles = [r.title for r in results]
        assert "Clean Water Protection Act" in titles

    def test_phrase_search(self, populated_db):
        """Test phrase search with quotes."""
        results = search_legislation(populated_db, '"voting rights"')
        assert len(results) == 1
        assert results[0].title == "For the People Act"

    def test_boolean_or_search(self, populated_db):
        """Test boolean OR search."""
        results = search_legislation(populated_db, "voting OR border")
        assert len(results) == 2

    def test_boolean_and_search(self, populated_db):
        """Test boolean AND search."""
        results = search_legislation(populated_db, "water AND quality")
        assert len(results) == 1
        assert results[0].citation == "H.R. 3"

    def test_jurisdiction_filter(self, populated_db):
        """Test filtering by jurisdiction."""
        federal = search_legislation(populated_db, "water", jurisdiction="federal")
        california = search_legislation(populated_db, "water", jurisdiction="california")

        assert all(r.jurisdiction == "federal" for r in federal)
        assert all(r.jurisdiction == "california" for r in california)

    def test_enacted_only_filter(self, populated_db):
        """Test filtering for enacted legislation only."""
        results = search_legislation(populated_db, "water OR climate", enacted_only=True)
        assert all(r.is_enacted for r in results)

    def test_session_filter(self, populated_db):
        """Test filtering by session."""
        results = search_legislation(populated_db, "water OR voting", session_filter="118")
        assert all(r.session == "118" for r in results)

    def test_limit_and_offset(self, populated_db):
        """Test pagination with limit and offset."""
        all_results = search_legislation(populated_db, "bill", limit=100)
        page1 = search_legislation(populated_db, "bill", limit=2, offset=0)
        page2 = search_legislation(populated_db, "bill", limit=2, offset=2)

        assert len(page1) == 2
        # page2 may have fewer if not enough results
        assert len(page2) <= 2

    def test_empty_results(self, populated_db):
        """Test search that returns no results."""
        results = search_legislation(populated_db, "xyznonexistent")
        assert results == []


class TestSearchCourtCases:
    """Tests for court case search."""

    @pytest.fixture
    def db_with_cases(self, fts_session):
        """Add court cases to database."""
        cases = [
            CourtCase(
                citation="598 U.S. 1",
                case_name="United States v. Environmental Corp",
                court="Supreme Court",
                holding="The Court held that environmental regulations are constitutional.",
            ),
            CourtCase(
                citation="599 U.S. 1",
                case_name="Voting Rights Council v. State",
                court="Supreme Court",
                holding="The Court upheld voting rights protections.",
            ),
        ]
        for case in cases:
            fts_session.add(case)
        fts_session.commit()
        return fts_session

    def test_case_search(self, db_with_cases):
        """Test searching court cases."""
        results = search_court_cases(db_with_cases, "environmental")
        assert len(results) == 1
        assert "Environmental" in results[0].case_name

    def test_case_search_by_holding(self, db_with_cases):
        """Test searching by holding text."""
        results = search_court_cases(db_with_cases, "voting rights")
        assert len(results) == 1
        assert "Voting" in results[0].case_name


class TestSearchAll:
    """Tests for unified search across all content types."""

    def test_search_all_types(self, populated_db):
        """Test searching across all content types."""
        # Add a court case
        case = CourtCase(
            citation="600 U.S. 1",
            case_name="Water Quality Association v. EPA",
            court="Supreme Court",
            holding="Water quality standards upheld.",
        )
        populated_db.add(case)
        populated_db.commit()

        results = search_all(populated_db, "water")

        assert "legislation" in results
        assert "court_cases" in results
        assert "law_sections" in results
        assert len(results["legislation"]) > 0
        assert len(results["court_cases"]) > 0


class TestCountSearchResults:
    """Tests for counting search results."""

    def test_count_results(self, populated_db):
        """Test counting search results."""
        count = count_search_results(populated_db, "water", table="legislation")
        assert count >= 2

    def test_count_no_results(self, populated_db):
        """Test counting when no results."""
        count = count_search_results(populated_db, "xyznonexistent", table="legislation")
        assert count == 0
