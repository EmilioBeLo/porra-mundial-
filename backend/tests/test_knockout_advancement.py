import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app
from app.database import get_db
from app.models import Match, User
from app.config import settings


@pytest.fixture
def test_client(db_session):
    def _get_db_override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def generate_admin_token(user_id: int) -> str:
    payload = {"user_id": user_id}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def test_normal_advancement(test_client, db_session):
    # Setup admin
    admin = User(nombre="Admin", password_hash="hash", is_admin=True)
    db_session.add(admin)
    db_session.commit()
    token = generate_admin_token(admin.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Create source match 73 and target match 90
    m73 = Match(id=73, equipo_local="Argentina", equipo_visitante="France", grupo_o_fase="Dieciseisavos de Final", fecha_hora=datetime.utcnow())
    m90 = Match(id=90, equipo_local="Winner Match 73", equipo_visitante="Winner Match 75", grupo_o_fase="Octavos de Final", fecha_hora=datetime.utcnow())
    db_session.add_all([m73, m90])
    db_session.commit()

    # Local team wins 2-1
    response = test_client.put(
        "/api/admin/matches/73/result",
        json={"goles_local_real": 2, "goles_visitante_real": 1},
        headers=headers,
    )
    assert response.status_code == 200
    db_session.refresh(m73)
    db_session.refresh(m90)
    assert m73.goles_local_real == 2
    assert m73.goles_visitante_real == 1
    assert m90.equipo_local == "Argentina"


def test_tie_penalty_validation_error(test_client, db_session):
    # Setup admin
    admin = User(nombre="Admin", password_hash="hash", is_admin=True)
    db_session.add(admin)
    db_session.commit()
    token = generate_admin_token(admin.id)
    headers = {"Authorization": f"Bearer {token}"}

    m73 = Match(id=73, equipo_local="Argentina", equipo_visitante="France", grupo_o_fase="Dieciseisavos de Final", fecha_hora=datetime.utcnow())
    db_session.add(m73)
    db_session.commit()

    # Tie without penalties_winner must fail with 400
    response = test_client.put(
        "/api/admin/matches/73/result",
        json={"goles_local_real": 1, "goles_visitante_real": 1},
        headers=headers,
    )
    assert response.status_code == 400
    assert "no pueden terminar en empate sin definir un ganador de penaltis" in response.json()["detail"]


def test_tie_penalty_local_winner(test_client, db_session):
    # Setup admin
    admin = User(nombre="Admin", password_hash="hash", is_admin=True)
    db_session.add(admin)
    db_session.commit()
    token = generate_admin_token(admin.id)
    headers = {"Authorization": f"Bearer {token}"}

    m73 = Match(id=73, equipo_local="Argentina", equipo_visitante="France", grupo_o_fase="Dieciseisavos de Final", fecha_hora=datetime.utcnow())
    m90 = Match(id=90, equipo_local="Winner Match 73", equipo_visitante="Winner Match 75", grupo_o_fase="Octavos de Final", fecha_hora=datetime.utcnow())
    db_session.add_all([m73, m90])
    db_session.commit()

    # Tie 1-1 with local team winning on penalties
    response = test_client.put(
        "/api/admin/matches/73/result",
        json={"goles_local_real": 1, "goles_visitante_real": 1, "penalties_winner": 1},
        headers=headers,
    )
    assert response.status_code == 200
    db_session.refresh(m73)
    db_session.refresh(m90)
    assert m73.goles_local_real == 1
    assert m73.goles_visitante_real == 1
    assert m90.equipo_local == "Argentina"

    # Visitor team winning on penalties
    response_visitor = test_client.put(
        "/api/admin/matches/73/result",
        json={"goles_local_real": 2, "goles_visitante_real": 2, "penalties_winner": 2},
        headers=headers,
    )
    assert response_visitor.status_code == 200
    db_session.refresh(m73)
    db_session.refresh(m90)
    assert m73.goles_local_real == 2
    assert m73.goles_visitante_real == 2
    assert m90.equipo_local == "France"


def test_semifinal_winner_loser_mapping(test_client, db_session):
    # Setup admin
    admin = User(nombre="Admin", password_hash="hash", is_admin=True)
    db_session.add(admin)
    db_session.commit()
    token = generate_admin_token(admin.id)
    headers = {"Authorization": f"Bearer {token}"}

    m101 = Match(id=101, equipo_local="Spain", equipo_visitante="Brazil", grupo_o_fase="Semifinales", fecha_hora=datetime.utcnow())
    m103 = Match(id=103, equipo_local="Loser Match 101", equipo_visitante="Loser Match 102", grupo_o_fase="Tercer Puesto", fecha_hora=datetime.utcnow())
    m104 = Match(id=104, equipo_local="Winner Match 101", equipo_visitante="Winner Match 102", grupo_o_fase="Final", fecha_hora=datetime.utcnow())
    db_session.add_all([m101, m103, m104])
    db_session.commit()

    # Spain wins 3-0
    response = test_client.put(
        "/api/admin/matches/101/result",
        json={"goles_local_real": 3, "goles_visitante_real": 0},
        headers=headers,
    )
    assert response.status_code == 200
    db_session.refresh(m101)
    db_session.refresh(m103)
    db_session.refresh(m104)

    assert m104.equipo_local == "Spain"  # Spain goes to final
    assert m103.equipo_local == "Brazil"  # Brazil goes to 3rd place match
