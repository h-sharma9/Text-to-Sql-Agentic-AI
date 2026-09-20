"""
tests/test_sql_agent.py
========================
Unit and integration tests for the Text-to-SQL agent safety checks and execution.
"""

import pytest
from sqlalchemy import text
from agents.sql_agent import _introspect_schema, query_database


def test_schema_introspection(db_engine):
    """Verify that schema introspection returns valid text listing database tables."""
    schema_text = _introspect_schema()
    assert isinstance(schema_text, str)
    assert len(schema_text) > 0
    assert "TABLE: orders" in schema_text
    assert "TABLE: customers" in schema_text


def test_sql_safety_gate_blocks_dangerous_queries():
    """Verify that query_database blocks non-SELECT or dangerous keywords."""
    # Test non-SELECT
    result_delete = query_database("DELETE FROM orders;")
    assert "[!]" in result_delete
    assert "blocked" in result_delete.lower() or "not a select" in result_delete.lower()

    # Test DROP table query
    result_drop = query_database("DROP TABLE customers;")
    assert "[!]" in result_drop


def test_sql_query_database_execution(initialized_sql):
    """Test natural language database query execution on structured tables."""
    answer = query_database("What are the top 3 customer states by total customers?")
    assert isinstance(answer, str)
    assert len(answer) > 0
    assert "[SQL Query Used]" in answer
    assert "SELECT" in answer.upper()
