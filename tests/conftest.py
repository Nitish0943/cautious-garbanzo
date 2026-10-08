import os
import tempfile
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.core.database import get_db, SessionLocal
from app.models.base import Base
from app.main import app
from app.core.config import settings

# Test in-memory SQLite database
TEST_DATABASE_URL = "sqlite:///:memory:"

engine_test = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="session", autouse=True)
def setup_test_directories():
    """Create a temporary storage directory for tests and clean up after."""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_storage_dir = settings.STORAGE_DIR
        settings.STORAGE_DIR = Path(temp_dir)
        yield
        settings.STORAGE_DIR = original_storage_dir


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Provides a fresh transactional database session for each test function."""
    import app.services.job_processor as jp
    original_session_local = jp.SessionLocal
    jp.SessionLocal = TestingSessionLocal

    Base.metadata.create_all(bind=engine_test)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine_test)
        jp.SessionLocal = original_session_local


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
