import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app
from app.database import get_db
from app.models import Match, Prediction, SystemSetting, User
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


def test_cors_configuration(test_client):
    response = test_client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:4200",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:4200"

    response_vercel = test_client.options(
        "/api/health",
        headers={
            "Origin": "https://my-app.vercel.app",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response_vercel.status_code == 200
    assert response_vercel.headers.get("access-control-allow-origin") == "https://my-app.vercel.app"


def test_get_competitions(test_client):
    response = test_client.get("/api/settings/competitions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 6
    assert data[0]["league_id"] == 1
    assert data[0]["name"] == "Mundial de Fútbol"


def test_get_active_setting_default(test_client, db_session):
    active_league_id = db_session.query(SystemSetting).filter(SystemSetting.key == "active_league_id").first()
    assert active_league_id is not None
    assert active_league_id.value == "1"

    response = test_client.get("/api/settings/active")
    assert response.status_code == 200
    data = response.json()
    assert data["league_id"] == 1
    assert data["name"] == "Mundial de Fútbol"
    assert data["season"] == 2026


def test_update_active_setting_requires_admin(test_client, db_session):
    response = test_client.put("/api/settings/active", json={"league_id": 140})
    assert response.status_code == 401

    user = User(nombre="Juan", password_hash="hash", is_admin=False)
    db_session.add(user)
    db_session.commit()

    token = generate_admin_token(user.id)
    response = test_client.put(
        "/api/settings/active",
        json={"league_id": 140},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_update_active_setting_and_recalculate_points(test_client, db_session):
    admin = User(nombre="Admin", password_hash="hash", is_admin=True)
    db_session.add(admin)
    
    user = User(nombre="Diego", password_hash="hash", is_admin=False)
    db_session.add(user)
    db_session.commit()

    match_l1 = Match(
        equipo_local="Argentina",
        equipo_visitante="Francia",
        fecha_hora=datetime(2026, 6, 11, 18, 0, 0),
        grupo_o_fase="Final",
        goles_local_real=3,
        goles_visitante_real=3,
        es_partido_doble=True,
        league_id=1,
    )
    match_l140 = Match(
        equipo_local="Real Madrid",
        equipo_visitante="Barcelona",
        fecha_hora=datetime(2025, 10, 26, 20, 0, 0),
        grupo_o_fase="Jornada 11",
        goles_local_real=2,
        goles_visitante_real=1,
        es_partido_doble=False,
        league_id=140,
    )
    db_session.add_all([match_l1, match_l140])
    db_session.commit()

    pred_l1 = Prediction(
        user_id=user.id,
        match_id=match_l1.id,
        goles_local_pred=3,
        goles_visitante_pred=3,
        puntos_obtenidos=6,
    )
    pred_l140 = Prediction(
        user_id=user.id,
        match_id=match_l140.id,
        goles_local_pred=2,
        goles_visitante_pred=1,
        puntos_obtenidos=3,
    )
    db_session.add_all([pred_l1, pred_l140])
    db_session.commit()

    token = generate_admin_token(admin.id)
    response = test_client.put(
        "/api/settings/active",
        json={"league_id": 140},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["league_id"] == 140
    assert data["name"] == "LaLiga (España)"

    active_league_id = db_session.query(SystemSetting).filter(SystemSetting.key == "active_league_id").first()
    assert active_league_id.value == "140"

    db_session.refresh(user)
    assert user.puntos_totales == 3
    assert user.aciertos_perfectos == 1

    response = test_client.put(
        "/api/settings/active",
        json={"league_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    
    db_session.refresh(user)
    assert user.puntos_totales == 6
    assert user.aciertos_perfectos == 1


def test_list_matches_filters_by_active_league(test_client, db_session):
    match_l1 = Match(
        equipo_local="Argentina",
        equipo_visitante="Francia",
        fecha_hora=datetime(2026, 6, 11, 18, 0, 0),
        grupo_o_fase="Final",
        league_id=1,
    )
    match_l140 = Match(
        equipo_local="Real Madrid",
        equipo_visitante="Barcelona",
        fecha_hora=datetime(2025, 10, 26, 20, 0, 0),
        grupo_o_fase="Jornada 11",
        league_id=140,
    )
    db_session.add_all([match_l1, match_l140])
    db_session.commit()

    response = test_client.get("/api/matches")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["equipo_local"] == "Argentina"

    admin = User(nombre="Admin", password_hash="hash", is_admin=True)
    db_session.add(admin)
    db_session.commit()

    token = generate_admin_token(admin.id)
    test_client.put(
        "/api/settings/active",
        json={"league_id": 140},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = test_client.get("/api/matches")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["equipo_local"] == "Real Madrid"
