import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.models import User


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


def test_get_ranking_excludes_admin(test_client, db_session):
    # Setup users
    admin = User(nombre="admin", password_hash="hash", is_admin=True)
    cronix = User(nombre="Cronix", password_hash="hash", is_admin=True, puntos_totales=15)
    user1 = User(nombre="RegularUser1", password_hash="hash", is_admin=False, puntos_totales=10)
    user2 = User(nombre="RegularUser2", password_hash="hash", is_admin=False, puntos_totales=20)
    
    db_session.add_all([admin, cronix, user1, user2])
    db_session.commit()

    # Call endpoint
    response = test_client.get("/api/users")
    assert response.status_code == 200
    
    data = response.json()
    # Should return all users except "admin", so size should be 3
    assert len(data) == 3
    
    # Assert that admin user is NOT present, but Cronix and regular users are
    names = [u["nombre"] for u in data]
    assert "admin" not in [n.lower() for n in names]
    assert "Cronix" in names
    assert "RegularUser1" in names
    assert "RegularUser2" in names


def test_get_ranking_sorting_order(test_client, db_session):
    # Setup users
    # user_a: 10 pts, 2 perfect hits
    user_a = User(nombre="UserA", password_hash="hash", is_admin=False, puntos_totales=10, aciertos_perfectos=2)
    # user_b: 20 pts, 1 perfect hit (should be #1)
    user_b = User(nombre="UserB", password_hash="hash", is_admin=False, puntos_totales=20, aciertos_perfectos=1)
    # user_c: 10 pts, 3 perfect hits (should be #2, above user_a)
    user_c = User(nombre="UserC", password_hash="hash", is_admin=False, puntos_totales=10, aciertos_perfectos=3)
    # user_d: 5 pts, 0 perfect hits (should be #4)
    user_d = User(nombre="UserD", password_hash="hash", is_admin=False, puntos_totales=5, aciertos_perfectos=0)

    db_session.add_all([user_a, user_b, user_c, user_d])
    db_session.commit()

    # Call endpoint
    response = test_client.get("/api/users")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 4
    
    # Expected order: UserB (20 pts), UserC (10 pts, 3 aciertos), UserA (10 pts, 2 aciertos), UserD (5 pts)
    assert data[0]["nombre"] == "UserB"
    assert data[0]["posicion"] == 1
    
    assert data[1]["nombre"] == "UserC"
    assert data[1]["posicion"] == 2
    
    assert data[2]["nombre"] == "UserA"
    assert data[2]["posicion"] == 3
    
    assert data[3]["nombre"] == "UserD"
    assert data[3]["posicion"] == 4


def test_get_ranking_includes_points_breakdown(test_client, db_session):
    from datetime import datetime, timezone
    from app.models import Match

    # Setup user
    user = User(
        nombre="RegularUser",
        password_hash="hash",
        is_admin=False,
        puntos_totales=15,
        assigned_team="Argentina"
    )
    
    # Setup a finished match in league 1 (World Cup active)
    match = Match(
        equipo_local="Argentina",
        equipo_visitante="Brazil",
        fecha_hora=datetime.now(timezone.utc),
        goles_local_real=3,
        goles_visitante_real=3,  # 3 // 3 = 1. total points for underdog Argentina = 3 + 1 = 4 points
        grupo_o_fase="Group A",
        league_id=1
    )
    
    db_session.add_all([user, match])
    db_session.commit()

    # Call endpoint
    response = test_client.get("/api/users")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    u_data = data[0]
    
    # Argentina scored 3 goals, opponent scored 3 goals.
    # Underdog points = 3 + (3 // 3) = 4 points.
    assert u_data["puntos_underdog"] == 4
    assert u_data["puntos_predicciones"] == 11
    assert u_data["puntos_totales"] == 15

