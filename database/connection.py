"""
database/connection.py
======================
Creates the SQLAlchemy engine and session factory, providing get_engine() and
get_session() helpers that every other module uses to talk to PostgreSQL.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine

from config import DATABASE_URL

# ---------------------------------------------------------------------------
# Module-level singletons — created once, reused everywhere.
# ---------------------------------------------------------------------------
_engine: Engine | None = None
_SessionFactory: sessionmaker | None = None


def get_engine() -> Engine:
    """
    Return the singleton SQLAlchemy engine connected to the PostgreSQL
    database specified in DATABASE_URL.  The engine is created lazily on
    first call and reused for every subsequent call.
    """
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            echo=False,             # Set True for SQL debug logging
            pool_pre_ping=True,     # Verify connections before checkout
            pool_size=5,            # Connection pool size
            max_overflow=10,        # Extra connections allowed beyond pool_size
        )
    return _engine


def get_session() -> Session:
    """
    Return a new SQLAlchemy ORM session bound to the singleton engine.
    Callers should use this inside a `with` block or call session.close()
    when finished.
    """
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine())
    return _SessionFactory()
