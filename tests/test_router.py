"""
tests/test_router.py
=====================
Integration tests for the LangGraph orchestrator graph routing decisions.
"""

import pytest
from agents.router import _route_decision, AgentState


def test_route_decision_logic():
    """Verify conditional route decision logic selects correct agent node."""
    state_sql: AgentState = {"question": "What is total revenue?", "route": "sql", "answer": ""}
    state_rag: AgentState = {"question": "What is the return window?", "route": "rag", "answer": ""}

    assert _route_decision(state_sql) == "sql_agent"
    assert _route_decision(state_rag) == "rag_agent"


def test_full_graph_invocation(router_graph):
    """Verify end-to-end routing through compiled StateGraph."""
    result = router_graph.invoke({
        "question": "How many total orders are in the database?",
        "route": "",
        "answer": "",
    })

    assert isinstance(result, dict)
    assert result["route"] in ("sql", "rag")
    assert len(result["answer"]) > 0
