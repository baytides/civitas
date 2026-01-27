"""API metadata and linking tests."""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from civitas.api.main import create_app
from civitas.db.models import (
    Base,
    CourtCase,
    LegalChallenge,
    P2025Implementation,
    Project2025Policy,
    StateResistanceAction,
)


def _setup_db(db_url: str) -> None:
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        policy = Project2025Policy(
            section="Test Section",
            chapter="Test Chapter",
            page_number=1,
            agency="Test Agency",
            proposal_text="Test proposal text",
            proposal_summary="Test proposal summary",
            category="environment",
            action_type="modify",
            priority="high",
            implementation_timeline="first_year",
            status="in_progress",
            confidence=0.7,
        )
        policy_two = Project2025Policy(
            section="Another Section",
            chapter=None,
            page_number=2,
            agency="Another Agency",
            proposal_text="Another proposal text",
            proposal_summary="Another summary",
            category="civil_rights",
            action_type="eliminate",
            priority="low",
            implementation_timeline="day_one",
            status="proposed",
            confidence=0.6,
        )
        session.add_all([policy, policy_two])
        session.flush()

        case = CourtCase(
            citation="123 U.S. 456",
            case_name="Policy v. Agency",
            court="Supreme Court",
            court_level="scotus",
            holding="Test holding",
        )
        session.add(case)
        session.flush()

        implementation = P2025Implementation(
            policy_id=policy.id,
            action_type="executive_order",
            action_reference="EO 14001",
            status="announced",
        )
        session.add(implementation)
        session.flush()

        challenge = LegalChallenge(
            implementation_id=implementation.id,
            challenge_type="constitutional",
            legal_basis="First Amendment",
            court_level="scotus",
            court_name="Supreme Court of the United States",
            court_case_id=case.id,
            status="filed",
        )
        session.add(challenge)

        resistance_action = StateResistanceAction(
            state_code="CA",
            state_name="California",
            category="environment",
            action_type="state_lawsuit",
            title="California v. Agency",
            description="State legal challenge to protect environment.",
            status="filed",
        )
        session.add(resistance_action)

        session.commit()
    finally:
        session.close()


def _create_client(tmp_path) -> TestClient:
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    _setup_db(db_url)
    app = create_app(db_url=db_url)
    return TestClient(app)


def test_objective_metadata_endpoint(tmp_path):
    client = _create_client(tmp_path)
    response = client.get("/api/v1/objectives/metadata")
    assert response.status_code == 200
    data = response.json()
    assert "environment" in data["categories"]
    assert "civil_rights" in data["categories"]
    assert "in_progress" in data["statuses"]
    assert "proposed" in data["statuses"]
    assert "high" in data["priorities"]
    assert "low" in data["priorities"]
    assert "first_year" in data["timelines"]
    assert "day_one" in data["timelines"]


def test_resistance_meta_endpoint(tmp_path):
    client = _create_client(tmp_path)
    response = client.get("/api/v1/resistance/meta")
    assert response.status_code == 200
    data = response.json()
    assert len(data["tiers"]) >= 1
    assert len(data["organization_sections"]) >= 1


def test_case_links_objectives(tmp_path):
    client = _create_client(tmp_path)
    response = client.get("/api/v1/cases/1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["linked_objectives"]) == 1
    assert data["linked_objectives"][0]["agency"] == "Test Agency"
