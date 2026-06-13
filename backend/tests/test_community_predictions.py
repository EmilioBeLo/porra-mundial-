from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.models import Match, Prediction, User

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

def test_get_community_predictions_non_existent_match(test_client, db_session):
    response = test_client.get("/api/predictions/match/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Partido no encontrado"

def test_get_community_predictions_before_kickoff(test_client, db_session):
    # Match in the future
    future_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=2)
    match = Match(
        equipo_local="Team A",
        equipo_visitante="Team B",
        fecha_hora=future_time,
        grupo_o_fase="Grupo A",
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)

    response = test_client.get(f"/api/predictions/match/{match.id}")
    assert response.status_code == 403
    assert response.json()["detail"] == "Las predicciones de la comunidad solo están disponibles después del inicio del partido."

def test_get_community_predictions_after_kickoff(test_client, db_session):
    # Match in the past
    past_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
    match = Match(
        equipo_local="Team A",
        equipo_visitante="Team B",
        fecha_hora=past_time,
        grupo_o_fase="Grupo A",
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)

    # Users
    user1 = User(nombre="User 1", password_hash="hash", is_admin=False)
    user2 = User(nombre="User 2", password_hash="hash", is_admin=False)
    db_session.add_all([user1, user2])
    db_session.commit()

    # Predictions
    pred1 = Prediction(user_id=user1.id, match_id=match.id, goles_local_pred=2, goles_visitante_pred=1, puntos_obtenidos=3)
    pred2 = Prediction(user_id=user2.id, match_id=match.id, goles_local_pred=0, goles_visitante_pred=0, puntos_obtenidos=0)
    db_session.add_all([pred1, pred2])
    db_session.commit()

    response = test_client.get(f"/api/predictions/match/{match.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Map username to response item
    pred_map = {item["username"]: item for item in data}
    assert "User 1" in pred_map
    assert pred_map["User 1"]["goles_local"] == 2
    assert pred_map["User 1"]["goles_visitante"] == 1
    assert pred_map["User 1"]["puntos_ganados"] == 3

    assert "User 2" in pred_map
    assert pred_map["User 2"]["goles_local"] == 0
    assert pred_map["User 2"]["goles_visitante"] == 0
    assert pred_map["User 2"]["puntos_ganados"] == 0

def test_get_community_predictions_excludes_admin(test_client, db_session):
    # Match in the past
    past_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
    match = Match(
        equipo_local="Team A",
        equipo_visitante="Team B",
        fecha_hora=past_time,
        grupo_o_fase="Grupo A",
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)

    # Admin and normal user
    admin = User(nombre="Admin User", password_hash="hash", is_admin=True)
    user1 = User(nombre="Normal User", password_hash="hash", is_admin=False)
    db_session.add_all([admin, user1])
    db_session.commit()

    # Predictions
    pred_admin = Prediction(user_id=admin.id, match_id=match.id, goles_local_pred=3, goles_visitante_pred=3, puntos_obtenidos=1)
    pred_user = Prediction(user_id=user1.id, match_id=match.id, goles_local_pred=1, goles_visitante_pred=1, puntos_obtenidos=0)
    db_session.add_all([pred_admin, pred_user])
    db_session.commit()

    response = test_client.get(f"/api/predictions/match/{match.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["username"] == "Normal User"
    assert data[0]["goles_local"] == 1
