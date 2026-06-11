import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.pool import StaticPool

from app.database import Base
from app import models  # Ensure models are imported so they register on Base



@pytest.fixture
def db_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


    session = TestSession()
    # Seed default system settings
    session.add_all([
        models.SystemSetting(key="active_league_id", value="1"),
        models.SystemSetting(key="active_season", value="2026"),
        models.SystemSetting(key="active_league_name", value="Mundial de Fútbol"),
    ])
    session.commit()
    try:

        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
