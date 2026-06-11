import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
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


@patch("app.routers.sync.sync_match_results")
def test_sync_endpoint_valid_secret(mock_sync, test_client):
    # Setup mock return value
    mock_sync.return_value = {"status": "success", "updated_matches_count": 5}

    # Make request with valid secret (configured in settings.SYNC_SECRET_KEY)
    response = test_client.get(
        "/api/sync/results",
        params={"secret": settings.SYNC_SECRET_KEY}
    )

    # Asserts
    assert response.status_code == 200
    assert response.json() == {"status": "success", "updated_matches_count": 5}
    mock_sync.assert_called_once()


def test_sync_endpoint_invalid_secret(test_client):
    # Make request with invalid secret
    response = test_client.get(
        "/api/sync/results",
        params={"secret": "wrong-secret-key-123"}
    )

    # Asserts
    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"


def test_sync_endpoint_missing_secret(test_client):
    # Make request with missing secret parameter
    response = test_client.get("/api/sync/results")

    # Asserts
    assert response.status_code == 422
