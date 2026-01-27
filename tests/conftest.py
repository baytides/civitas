"""Pytest fixtures for Civitas tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from civitas.db.models import Base


@pytest.fixture
def db_engine():
    """Create an in-memory SQLite database engine."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Create a database session for testing."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_legislation(db_session):
    """Create sample legislation for testing."""
    from civitas.db.models import Legislation

    leg = Legislation(
        jurisdiction="california",
        source_id="2023_AB_123",
        legislation_type="bill",
        chamber="assembly",
        number=123,
        session="2023-2024",
        citation="AB 123",
        title="Test Bill for Water Conservation",
        is_enacted=False,
    )
    db_session.add(leg)
    db_session.commit()
    return leg


@pytest.fixture
def sample_legislator(db_session):
    """Create sample legislator for testing."""
    from civitas.db.models import Legislator

    legislator = Legislator(
        jurisdiction="california",
        source_id="CA_ASM_001",
        full_name="Jane Doe",
        first_name="Jane",
        last_name="Doe",
        chamber="assembly",
        party="D",
        state="CA",
        district="15",
        is_current=True,
    )
    db_session.add(legislator)
    db_session.commit()
    return legislator


@pytest.fixture
def sample_court_case(db_session):
    """Create sample court case for testing."""
    from civitas.db.models import CourtCase

    case = CourtCase(
        citation="598 U.S. 651",
        case_name="Test v. United States",
        docket_number="22-1234",
        court="Supreme Court",
        holding="The Court held that test cases are important.",
    )
    db_session.add(case)
    db_session.commit()
    return case
