from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app
from app.database import get_db
from app.models import Match, Prediction, SystemSetting, User, TournamentPrediction
from app.config import settings
from app.services.scoring_service import calculate_tournament_points

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


def generate_token(user_id: int) -> str:
    payload = {"user_id": user_id}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def test_get_my_prediction_empty(test_client, db_session):
    user = User(nombre="TestUser", password_hash="hash", is_admin=False)
    db_session.add(user)
    db_session.commit()

    token = generate_token(user.id)
    response = test_client.get(
        "/api/predictions/tournament",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 0
    assert data["user_id"] == user.id
    assert data["campeon"] == ""
    assert data["subcampeon"] == ""
    assert data["maximo_goleador"] == ""
    assert data["maximo_asistente"] == ""


def test_post_prediction_success_before_deadline(test_client, db_session):
    user = User(nombre="TestUser", password_hash="hash", is_admin=False)
    db_session.add(user)
    
    # Unlock predictions
    setting = db_session.query(SystemSetting).filter_by(key="tournament_predictions_locked").first()
    if setting:
        setting.value = "false"
    else:
        db_session.add(SystemSetting(key="tournament_predictions_locked", value="false"))
    db_session.commit()

    token = generate_token(user.id)
    payload = {
        "campeon": "Argentina",
        "subcampeon": "Francia",
        "maximo_goleador": "Messi",
        "maximo_asistente": "Messi",
    }

    response = test_client.post(
        "/api/predictions/tournament",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["campeon"] == "Argentina"
    assert data["subcampeon"] == "Francia"
    assert data["maximo_goleador"] == "Messi"
    assert data["maximo_asistente"] == "Messi"

    # Query DB directly to verify
    db_pred = db_session.query(TournamentPrediction).filter_by(user_id=user.id).first()
    assert db_pred is not None
    assert db_pred.campeon == "Argentina"


def test_post_prediction_lockout_after_deadline(test_client, db_session):
    user = User(nombre="TestUser", password_hash="hash", is_admin=False)
    db_session.add(user)
    
    # Lock predictions
    setting = db_session.query(SystemSetting).filter_by(key="tournament_predictions_locked").first()
    if setting:
        setting.value = "true"
    else:
        db_session.add(SystemSetting(key="tournament_predictions_locked", value="true"))
    db_session.commit()

    token = generate_token(user.id)
    payload = {
        "campeon": "Argentina",
        "subcampeon": "Francia",
        "maximo_goleador": "Messi",
        "maximo_asistente": "Messi",
    }

    response = test_client.post(
        "/api/predictions/tournament",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 403
    assert "cerrado" in response.json()["detail"]


def test_get_community_predictions_before_lockout(test_client, db_session):
    user = User(nombre="TestUser", password_hash="hash", is_admin=False)
    db_session.add(user)
    
    # Unlock predictions, meaning community view is locked
    setting = db_session.query(SystemSetting).filter_by(key="tournament_predictions_locked").first()
    if setting:
        setting.value = "false"
    else:
        db_session.add(SystemSetting(key="tournament_predictions_locked", value="false"))
    db_session.commit()

    token = generate_token(user.id)
    response = test_client.get(
        "/api/predictions/tournament/community",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 403
    assert "fecha límite" in response.json()["detail"]


def test_get_community_predictions_after_lockout(test_client, db_session):
    admin = User(nombre="admin", password_hash="hash", is_admin=True)
    user1 = User(nombre="UserOne", password_hash="hash", is_admin=False)
    user2 = User(nombre="UserTwo", password_hash="hash", is_admin=False)
    cronix = User(nombre="cronix", password_hash="hash", is_admin=True)
    db_session.add_all([admin, user1, user2, cronix])
    
    # Lock predictions, meaning community view is unlocked
    setting = db_session.query(SystemSetting).filter_by(key="tournament_predictions_locked").first()
    if setting:
        setting.value = "true"
    else:
        db_session.add(SystemSetting(key="tournament_predictions_locked", value="true"))
    db_session.commit()

    pred1 = TournamentPrediction(
        user_id=user1.id,
        campeon="Argentina",
        subcampeon="Francia",
        maximo_goleador="Messi",
        maximo_asistente="Messi",
    )
    pred2 = TournamentPrediction(
        user_id=user2.id,
        campeon="Brasil",
        subcampeon="Alemania",
        maximo_goleador="Neymar",
        maximo_asistente="Neymar",
    )
    pred_admin = TournamentPrediction(
        user_id=admin.id,
        campeon="España",
        subcampeon="Italia",
        maximo_goleador="Pedri",
        maximo_asistente="Pedri",
    )
    pred_cronix = TournamentPrediction(
        user_id=cronix.id,
        campeon="Uruguay",
        subcampeon="Inglaterra",
        maximo_goleador="Suarez",
        maximo_asistente="De Arrascaeta",
    )
    db_session.add_all([pred1, pred2, pred_admin, pred_cronix])
    db_session.commit()

    token = generate_token(user1.id)
    response = test_client.get(
        "/api/predictions/tournament/community",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    names = [p["username"] for p in data]
    assert "admin" not in names
    assert "cronix" in names
    assert "UserOne" in names
    assert "UserTwo" in names


def test_scoring_points_calculation(db_session):
    user = User(nombre="Predictor", password_hash="hash", is_admin=False)
    db_session.add(user)
    db_session.commit()

    # User predicts: Argentina (Champion), Francia (Runner-up), Messi (Scorer), Mbappé (Assister)
    pred = TournamentPrediction(
        user_id=user.id,
        campeon=" Argentina ",
        subcampeon="Francia",
        maximo_goleador="messi",
        maximo_asistente="Mbappé",
    )
    db_session.add(pred)
    db_session.commit()

    # Set real outcomes
    db_session.add_all([
        SystemSetting(key="real_campeon", value="argentina"),
        SystemSetting(key="real_subcampeon", value="Francia "),
        SystemSetting(key="real_maximo_goleador", value="Messi"),
        SystemSetting(key="real_maximo_asistente", value="Neymar"),
    ])
    db_session.commit()

    points = calculate_tournament_points(db_session, user.id)
    assert points == 20


def test_admin_results_update_and_recalculation(test_client, db_session):
    admin = User(nombre="Admin", password_hash="hash", is_admin=True)
    user = User(nombre="Predictor", password_hash="hash", is_admin=False)
    db_session.add_all([admin, user])
    db_session.commit()

    pred = TournamentPrediction(
        user_id=user.id,
        campeon="Argentina",
        subcampeon="Francia",
        maximo_goleador="Messi",
        maximo_asistente="Mbappé",
    )
    db_session.add(pred)
    db_session.commit()

    admin_token = generate_token(admin.id)
    results_payload = {
        "real_campeon": "Argentina",
        "real_subcampeon": "Francia",
        "real_maximo_goleador": "Messi",
        "real_maximo_asistente": "Mbappé",
    }

    response = test_client.put(
        "/api/admin/tournament/results",
        json=results_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"

    db_session.refresh(user)
    assert user.puntos_totales == 25

    real_camp = db_session.query(SystemSetting).filter_by(key="real_campeon").first()
    assert real_camp is not None
    assert real_camp.value == "Argentina"


def test_get_tournament_lock(test_client, db_session):
    # Set to true
    setting = db_session.query(SystemSetting).filter_by(key="tournament_predictions_locked").first()
    if setting:
        setting.value = "true"
    else:
        db_session.add(SystemSetting(key="tournament_predictions_locked", value="true"))
    db_session.commit()

    response = test_client.get("/api/settings/tournament-lock")
    assert response.status_code == 200
    assert response.json() == {"locked": True}

    # Set to false
    setting.value = "false"
    db_session.commit()

    response = test_client.get("/api/settings/tournament-lock")
    assert response.status_code == 200
    assert response.json() == {"locked": False}


def test_toggle_tournament_lock_requires_admin(test_client, db_session):
    # Public fails
    response = test_client.post("/api/admin/settings/toggle-tournament-lock")
    assert response.status_code == 401

    # Regular user fails
    user = User(nombre="Juan", password_hash="hash", is_admin=False)
    db_session.add(user)
    db_session.commit()

    token = generate_token(user.id)
    response = test_client.post(
        "/api/admin/settings/toggle-tournament-lock",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_toggle_tournament_lock_success(test_client, db_session):
    admin = User(nombre="AdminUser", password_hash="hash", is_admin=True)
    db_session.add(admin)

    # Initialize to true
    setting = db_session.query(SystemSetting).filter_by(key="tournament_predictions_locked").first()
    if setting:
        setting.value = "true"
    else:
        db_session.add(SystemSetting(key="tournament_predictions_locked", value="true"))
    db_session.commit()

    token = generate_token(admin.id)
    response = test_client.post(
        "/api/admin/settings/toggle-tournament-lock",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success", "locked": False}

    # Verify DB setting
    db_session.refresh(setting)
    assert setting.value == "false"

    # Toggle back
    response = test_client.post(
        "/api/admin/settings/toggle-tournament-lock",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success", "locked": True}
    db_session.refresh(setting)
    assert setting.value == "true"
