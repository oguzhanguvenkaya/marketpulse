import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import get_db
from app.core.config import settings


@pytest.fixture(scope="session")
def db_engine():
    """Create engine connected to real PostgreSQL (from DATABASE_URL)."""
    engine = create_engine(settings.DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """Each test runs inside a transaction that rolls back after the test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()

    session.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    """TestClient with DB session override for transaction isolation."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def api_key():
    """Return the configured API key for auth tests."""
    return (settings.INTERNAL_API_KEY or "").strip()


@pytest.fixture()
def auth_headers(api_key):
    """Headers with valid API key."""
    return {"X-API-Key": api_key}
