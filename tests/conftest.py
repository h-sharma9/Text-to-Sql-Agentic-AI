"""
tests/conftest.py
==================
Shared pytest fixtures for testing DB connection, RAG engine, SQL agent, and Router graph.
"""

import sys
import os
import pytest

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import get_engine
from agents.rag_engine import init_rag_engine
from agents.sql_agent import init_sql_agent
from agents.router import build_router_graph


@pytest.fixture(scope="session")
def db_engine():
    """Return singleton database engine."""
    return get_engine()


@pytest.fixture(scope="session")
def initialized_rag():
    """Ensure RAG engine is initialized once for the test session."""
    init_rag_engine()
    return True


@pytest.fixture(scope="session")
def initialized_sql():
    """Ensure SQL agent is initialized once for the test session."""
    init_sql_agent()
    return True


@pytest.fixture(scope="session")
def router_graph(initialized_rag, initialized_sql):
    """Return compiled router state graph."""
    return build_router_graph()
