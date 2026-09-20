"""
agents/router.py
================
LangGraph-based StateGraph orchestrator that classifies each user query as
either "sql" (structured data question) or "rag" (policy/document question),
routes it to the correct sub-agent, and returns the final answer.
"""

from typing import TypedDict, Literal, cast
from pydantic import SecretStr
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from config import API_KEY, LLM_BASE_URL, LLM_MODEL_NAME, LLM_TEMPERATURE
from agents.sql_agent import query_database
from agents.rag_engine import query_policies


# ===========================================================================
# STATE SCHEMA -- the data that flows through the graph
# ===========================================================================

class AgentState(TypedDict):
    """Typed dictionary representing the state passed between graph nodes."""
    question: str       # The user's original natural-language query
    route: str          # "sql" or "rag" -- set by the classifier node
    answer: str         # The final answer produced by the chosen sub-agent


# ===========================================================================
# INTENT CLASSIFIER -- the supervisor node
# ===========================================================================

_CLASSIFIER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a query router for an e-commerce platform. Your job is to "
            "classify the user's question into exactly one of two categories:\n\n"
            "1. **sql** -- The question asks about structured e-commerce DATA such as "
            "   orders, customers, products, sellers, payments, reviews, revenue, "
            "   delivery times, geographic distribution, sales trends, or any "
            "   question answerable by querying a database.\n\n"
            "2. **rag** -- The question asks about store POLICIES, rules, return "
            "   procedures, refund timelines, shipping SLAs, cancellation rights, "
            "   warranty, non-refundable items, or any question about how the "
            "   platform operates from a policy/legal perspective.\n\n"
            "Respond with ONLY the single word: sql  OR  rag\n"
            "Do not add any explanation.",
        ),
        ("human", "{question}"),
    ]
)


def _classify_intent(state: AgentState) -> AgentState:
    """
    Supervisor node: uses GPT to classify the user's question intent and
    writes the route ("sql" or "rag") into the state.
    """
    llm = ChatOpenAI(
        model=LLM_MODEL_NAME,
        temperature=0.0,
        api_key=SecretStr(API_KEY),
        base_url=LLM_BASE_URL,
    )
    chain = _CLASSIFIER_PROMPT | llm
    response = chain.invoke({"question": state["question"]})
    route = str(response.content).strip().lower()

    # Defensive fallback -- if the LLM returns something unexpected, default to sql
    if route not in ("sql", "rag"):
        route = "sql"

    print(f"  [ROUTER] Classified intent -> [{route.upper()}]")
    return {**state, "route": route}


# ===========================================================================
# SUB-AGENT NODES
# ===========================================================================

def _sql_agent_node(state: AgentState) -> AgentState:
    """Node that delegates to the Text-to-SQL pipeline."""
    print("  [SQL] Routing to SQL Agent...")
    answer = query_database(state["question"])
    return {**state, "answer": answer}


def _rag_agent_node(state: AgentState) -> AgentState:
    """Node that delegates to the RAG policy engine."""
    print("  [RAG] Routing to RAG Engine...")
    answer = query_policies(state["question"])
    return {**state, "answer": answer}


# ===========================================================================
# CONDITIONAL EDGE -- pick the next node based on the classified route
# ===========================================================================

def _route_decision(state: AgentState) -> Literal["sql_agent", "rag_agent"]:
    """Return the name of the next node based on the classifier's decision."""
    return "sql_agent" if state["route"] == "sql" else "rag_agent"


# ===========================================================================
# GRAPH CONSTRUCTION -- build and compile the LangGraph StateGraph
# ===========================================================================

def build_router_graph():
    """
    Construct the LangGraph StateGraph:
      START -> classify_intent -> (sql_agent | rag_agent) -> END

    Returns a compiled graph that can be invoked with
    graph.invoke({"question": "...", "route": "", "answer": ""}).
    """
    graph = StateGraph(state_schema=cast(type, AgentState))

    # Add nodes
    graph.add_node("classify_intent", _classify_intent)
    graph.add_node("sql_agent", _sql_agent_node)
    graph.add_node("rag_agent", _rag_agent_node)

    # Wire edges
    graph.add_edge(START, "classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        _route_decision,
        {
            "sql_agent": "sql_agent",
            "rag_agent": "rag_agent",
        },
    )
    graph.add_edge("sql_agent", END)
    graph.add_edge("rag_agent", END)

    return graph.compile()
