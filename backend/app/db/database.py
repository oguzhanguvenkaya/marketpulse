import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

_engine = None
_SessionLocal = None


def _get_connect_args(url: str) -> dict:
    if url.startswith("postgresql"):
        return {
            "connect_timeout": 10,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        }
    return {}


def _ensure_engine():
    global _engine, _SessionLocal
    if _engine is None:
        database_url = (settings.DATABASE_URL or "").strip()
        if not database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        _engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT_SECONDS,
            pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
            pool_use_lifo=True,
            connect_args=_get_connect_args(database_url),
        )
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_engine():
    return _ensure_engine()


def get_session_local():
    _ensure_engine()
    return _SessionLocal


class _LazyEngine:
    def __getattr__(self, name):
        return getattr(get_engine(), name)

    def connect(self):
        return get_engine().connect()

    def begin(self):
        return get_engine().begin()

    def dispose(self):
        return get_engine().dispose()


class _LazySessionLocal:
    def __call__(self, *args, **kwargs):
        return get_session_local()(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(get_session_local(), name)


engine = _LazyEngine()
SessionLocal = _LazySessionLocal()


def get_db():
    session_factory = get_session_local()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
