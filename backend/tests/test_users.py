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
    admin = User(nombre="AdminUser", password_hash="hash", is_admin=True)
    user1 = User(nombre="RegularUser1", password_hash="hash", is_admin=False, puntos_totales=10)
    user2 = User(nombre="RegularUser2", password_hash="hash", is_admin=False, puntos_totales=20)
    
    db_session.add_all([admin, user1, user2])
    db_session.commit()

    # Call endpoint
    response = test_client.get("/api/users")
    assert response.status_code == 200
    
    data = response.json()
    # Should only return regular users, so size should be 2
    assert len(data) == 2
    
    # Assert that admin user is NOT present
    names = [u["nombre"] for u in data]
    assert "AdminUser" not in names
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
