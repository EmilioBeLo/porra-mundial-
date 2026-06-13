import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app
from app.database import get_db
from app.models import Match, Prediction, SystemSetting, User
from app.config import settings
from app.services.scoring_service import calculate_assigned_team_points, recalculate_all_users_points


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


def test_draw_endpoint_authorization(test_client, db_session):
    # Setup users
    admin = User(nombre="AdminUser", password_hash="hash", is_admin=True)
    regular = User(nombre="RegularUser", password_hash="hash", is_admin=False)
    db_session.add_all([admin, regular])
    db_session.commit()

    # Unauthenticated request
    response = test_client.post("/api/admin/draw-teams")
    assert response.status_code == 401

    # Regular user request (should get 403)
    token_regular = generate_token(regular.id)
    response = test_client.post(
        "/api/admin/draw-teams",
        headers={"Authorization": f"Bearer {token_regular}"}
    )
    assert response.status_code == 403

    # Admin user request (should succeed)
    token_admin = generate_token(admin.id)
    response = test_client.post(
        "/api/admin/draw-teams",
        headers={"Authorization": f"Bearer {token_admin}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "assignments" in data
    assert "RegularUser" in data["assignments"]
    assert "AdminUser" not in data["assignments"]  # Admins should be excluded from draw


def test_draw_distribution(test_client, db_session):
    admin = User(nombre="AdminUser", password_hash="hash", is_admin=True)
    # Add 12 regular users to test cycling of the 10 teams
    users = [User(nombre=f"User{i}", password_hash="hash", is_admin=False) for i in range(12)]
    db_session.add_all([admin] + users)
    db_session.commit()

    token_admin = generate_token(admin.id)
    response = test_client.post(
        "/api/admin/draw-teams",
        headers={"Authorization": f"Bearer {token_admin}"}
    )
    assert response.status_code == 200
    assignments = response.json()["assignments"]

    # Verify that all 12 users have a team assigned
    assert len(assignments) == 12
    # Verify that all assigned teams are valid underdog teams
    from app.routers.admin import UNDERDOG_TEAMS
    assigned_teams = set(assignments.values())
    assert assigned_teams.issubset(set(UNDERDOG_TEAMS))

    # Clean up and refresh users in session to verify DB persist
    for u in users:
        db_session.refresh(u)
        assert u.assigned_team in UNDERDOG_TEAMS


def test_minigame_scoring_logic(db_session):
    # Setup regular user with an assigned team "Haiti"
    user = User(nombre="HaitiFan", password_hash="hash", is_admin=False, assigned_team="Haiti")
    db_session.add(user)
    db_session.commit()

    # Active league is 1 (seeded in conftest.py)

    # 1. Test Goals scored: 2 goals scored -> +2 points
    match1 = Match(
        equipo_local="Haiti",
        equipo_visitante="Canada",
        fecha_hora=datetime.now(),
        grupo_o_fase="Group Stage",
        goles_local_real=2,
        goles_visitante_real=0,  # conceded 0 (0 points conceded)
        league_id=1
    )
    db_session.add(match1)
    db_session.commit()

    points = calculate_assigned_team_points(db_session, user)
    assert points == 2  # 2 goals scored + 0 conceded points

    # 2. Test Goals conceded: 1 match conceded 3 goals -> +1 point.
    match2 = Match(
        equipo_local="Mexico",
        equipo_visitante="Haiti",
        fecha_hora=datetime.now(),
        grupo_o_fase="Group Stage",
        goles_local_real=3,  # Haiti conceded 3
        goles_visitante_real=1,  # Haiti scored 1
        league_id=1
    )
    db_session.add(match2)
    db_session.commit()

    # Total:
    # Match 1: 2 scored, 0 conceded -> 2 points
    # Match 2: 1 scored, 3 conceded -> 1 + (3 // 3) = 2 points
    # Total = 4 points
    points = calculate_assigned_team_points(db_session, user)
    assert points == 4

    # 3. Test Goals conceded: 1 match conceded 6 goals -> +2 points
    match3 = Match(
        equipo_local="Haiti",
        equipo_visitante="Brazil",
        fecha_hora=datetime.now(),
        grupo_o_fase="Group Stage",
        goles_local_real=0,  # Haiti scored 0
        goles_visitante_real=6,  # Haiti conceded 6 -> 6 // 3 = 2 points
        league_id=1
    )
    db_session.add(match3)
    db_session.commit()

    # Total: Previous 4 + (0 + 2) = 6 points
    points = calculate_assigned_team_points(db_session, user)
    assert points == 6

    # 4. Test Goals conceded: 1 match conceded 2 goals -> 0 points
    match4 = Match(
        equipo_local="Haiti",
        equipo_visitante="USA",
        fecha_hora=datetime.now(),
        grupo_o_fase="Group Stage",
        goles_local_real=0,  # Haiti scored 0
        goles_visitante_real=2,  # Haiti conceded 2 -> 2 // 3 = 0 points
        league_id=1
    )
    db_session.add(match4)
    db_session.commit()

    # Total: Previous 6 + 0 = 6 points
    points = calculate_assigned_team_points(db_session, user)
    assert points == 6


def test_minigame_scoring_non_accumulative_conceded(db_session):
    # Setup regular user with an assigned team "Curaçao"
    user = User(nombre="CuracaoFan", password_hash="hash", is_admin=False, assigned_team="Curaçao")
    db_session.add(user)
    db_session.commit()

    # Match 1: Curaçao concedes 2 goals
    match1 = Match(
        equipo_local="Curaçao",
        equipo_visitante="Jamaica",
        fecha_hora=datetime.now(),
        grupo_o_fase="Group Stage",
        goles_local_real=0,
        goles_visitante_real=2,  # Conceded 2 -> 2 // 3 = 0 points
        league_id=1
    )
    # Match 2: Curaçao concedes 1 goal
    match2 = Match(
        equipo_local="Costa Rica",
        equipo_visitante="Curaçao",
        fecha_hora=datetime.now(),
        grupo_o_fase="Group Stage",
        goles_local_real=1,  # Conceded 1 -> 1 // 3 = 0 points
        goles_visitante_real=0,
        league_id=1
    )
    db_session.add_all([match1, match2])
    db_session.commit()

    # If it was accumulative, 2 + 1 = 3 conceded goals -> 1 point.
    # Since it is non-accumulative, it must yield 0 points.
    points = calculate_assigned_team_points(db_session, user)
    assert points == 0


def test_minigame_scoring_only_league_1(db_session):
    user = User(nombre="GhanaFan", password_hash="hash", is_admin=False, assigned_team="Ghana")
    db_session.add(user)
    db_session.commit()

    # Match in League 1 (active league)
    match_l1 = Match(
        equipo_local="Ghana",
        equipo_visitante="Uruguay",
        fecha_hora=datetime.now(),
        grupo_o_fase="Group Stage",
        goles_local_real=2,
        goles_visitante_real=0,
        league_id=1
    )
    # Match in League 140 (LaLiga, not league 1)
    match_l140 = Match(
        equipo_local="Ghana",
        equipo_visitante="Uruguay",
        fecha_hora=datetime.now(),
        grupo_o_fase="Group Stage",
        goles_local_real=5,
        goles_visitante_real=0,
        league_id=140
    )
    db_session.add_all([match_l1, match_l140])
    db_session.commit()

    # The calculation should ignore league 140 match completely
    points = calculate_assigned_team_points(db_session, user)
    assert points == 2  # Only match_l1 counts

    # If active league changes to 140, minigame points should return 0 (as league_id != 1)
    active_league_setting = db_session.query(SystemSetting).filter(SystemSetting.key == "active_league_id").first()
    active_league_setting.value = "140"
    db_session.commit()

    points = calculate_assigned_team_points(db_session, user)
    assert points == 0
