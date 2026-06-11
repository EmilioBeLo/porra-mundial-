import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.routers.auth import _hash_password, _verify_password


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


def test_register_disabled(test_client):
    response = test_client.post(
        "/api/auth/register",
        json={"nombre": "NuevoUsuario", "password": "somepassword123"},
    )
    assert response.status_code == 403
    assert "cerrado" in response.json()["detail"]



def test_hash_password_generates_valid_hash():
    password = "supersecretpassword123"
    hashed = _hash_password(password)
    
    assert hashed != password
    assert len(hashed) > 0
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")  # Valid bcrypt prefix


def test_verify_password_correct():
    password = "mypassword"
    hashed = _hash_password(password)
    
    assert _verify_password(password, hashed) is True


def test_verify_password_incorrect():
    password = "mypassword"
    hashed = _hash_password(password)
    
    assert _verify_password("wrongpassword", hashed) is False


def test_unicode_passwords():
    password = "ñandú_123_🔥"
    hashed = _hash_password(password)
    
    assert _verify_password(password, hashed) is True
    assert _verify_password("nandu_123_🔥", hashed) is False
