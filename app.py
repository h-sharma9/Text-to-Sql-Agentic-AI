"""
app.py
======
Interactive Web Dashboard for the Agentic Text-to-SQL & Document RAG Engine.
Built with Streamlit, Plotly, LangGraph, FAISS, and PostgreSQL.
"""

import sys
import os
import re
import pandas as pd
import plotly.express as px
import streamlit as st

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(__file__))

from config import LLM_MODEL_NAME, API_KEY, LLM_BASE_URL, FAISS_INDEX_DIR
from database.connection import get_engine
from agents.rag_engine import init_rag_engine
from agents.sql_agent import init_sql_agent
from agents.router import build_router_graph

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Agentic Text-to-SQL & RAG Engine",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS for Premium Aesthetics
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #4F46E5 0%, #7C3AED 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #9CA3AF;
        margin-bottom: 1.5rem;
    }
    .badge-sql {
        background-color: #1E3A8A;
        color: #93C5FD;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
        margin-bottom: 10px;
    }
    .badge-rag {
        background-color: #065F46;
        color: #6EE7B7;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
        margin-bottom: 10px;
    }
    .sql-box {
        background-color: #111827;
        border: 1px solid #374151;
        border-radius: 8px;
        padding: 12px;
        font-family: monospace;
        color: #10B981;
        margin-top: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Lazy Initialization of Backend Engine
# ---------------------------------------------------------------------------
@st.cache_resource
def get_initialized_router():
    """Initialize DB, RAG engine, SQL agent, and return compiled LangGraph router."""
    init_rag_engine()
    init_sql_agent()
    return build_router_graph()


# ---------------------------------------------------------------------------
# Main App Layout
# ---------------------------------------------------------------------------
def main():
    st.markdown('<div class="main-header">🤖 Agentic Text-to-SQL & RAG Engine</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Intelligent Supervisor Orchestrator powered by LangGraph, PostgreSQL, FAISS & Groq / LLM</div>',
        unsafe_allow_html=True,
    )

    # Initialize Backend
    with st.spinner("Initializing AI Agents & Databases..."):
        try:
            router = get_initialized_router()
        except Exception as e:
            st.error(f"Initialization Error: {e}")
            st.stop()

    # Sidebar: System Metrics & Sample Queries
    with st.sidebar:
        st.header("⚙️ System Status")
        
        provider_name = "Groq API (Free)" if LLM_BASE_URL else "OpenAI API"
        st.success(f"**LLM Provider**: {provider_name}")
        st.info(f"**Model**: `{LLM_MODEL_NAME}`")
        st.info(f"**Vector Store**: FAISS (Policy Corpus)")

        st.divider()

        st.header("💡 Sample Prompts for Report")
        st.caption("Click any button below to run impressive query demonstrations:")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 Top Categories"):
                st.session_state.pending_prompt = "What are the top 5 product categories by number of orders?"
            if st.button("💳 Payment Methods"):
                st.session_state.pending_prompt = "Which payment method is used most frequently by customers?"
            if st.button("🗺️ Top Buyer States"):
                st.session_state.pending_prompt = "What are the top 5 customer states by total number of customers?"

        with col2:
            if st.button("⭐ Review Ratings"):
                st.session_state.pending_prompt = "What is the distribution of order review scores from 1 to 5 stars?"
            if st.button("📦 Defective Return"):
                st.session_state.pending_prompt = "What is the policy for returning a defective or damaged item?"
            if st.button("⏱️ Delivery Rules"):
                st.session_state.pending_prompt = "What are the shipping SLAs and delivery delay rules?"

        st.divider()
        st.header("🧪 Automated Test Suite")
        st.caption("Run unit & integration tests for SQL safety, RAG, and Router:")
        if st.button("▶️ Run System Tests (pytest)"):
            st.session_state.run_tests = True

        st.divider()
        if st.button("🗑️ Clear Chat History", type="secondary"):
            st.session_state.messages = []
            st.rerun()

    # Section: Display Test Suite Results if Triggered
    if st.session_state.get("run_tests"):
        with st.expander("🧪 Automated Test Suite Results (`pytest`)", expanded=True):
            st.markdown("#### Running 7 Automated System Verification Tests...")
            with st.spinner("Executing pytest tests/ -v ..."):
                import subprocess
                res = subprocess.run(
                    [sys.executable, "-m", "pytest", "tests/", "-v"],
                    capture_output=True,
                    text=True,
                )
                if res.returncode == 0:
                    st.success("🎉 **ALL 7 AUTOMATED TESTS PASSED (100% SUCCESS RATE)**")
                else:
                    st.warning("Test suite completed with output below:")

                st.code(res.stdout if res.stdout else res.stderr, language="text")
        st.session_state.run_tests = False

    # Session State for Conversation Messages
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display Existing Chat Messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg.get("route"):
                if msg["route"] == "sql":
                    st.markdown('<span class="badge-sql">📊 SQL DATA AGENT</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="badge-rag">📚 POLICY RAG ENGINE</span>', unsafe_allow_html=True)
            
            st.markdown(msg["content"])

            # Render SQL Query if attached
            if msg.get("sql_query"):
                with st.expander("🔍 View Executed SQL Query"):
                    st.code(msg["sql_query"], language="sql")

            # Render Visual Plotly Chart if attached
            if msg.get("chart_data") is not None and not msg["chart_data"].empty:
                df = msg["chart_data"]
                if len(df.columns) >= 2:
                    col_x = df.columns[0]
                    num_cols = df.select_dtypes(include=["number"]).columns
                    if len(num_cols) > 0:
                        col_y = num_cols[0]
                        st.markdown("##### 📈 Interactive Data Chart")
                        fig = px.bar(
                            df,
                            x=col_x,
                            y=col_y,
                            color=col_x,
                            text_auto=True,
                            title=f"{col_y.replace('_', ' ').title()} by {col_x.replace('_', ' ').title()}",
                            template="plotly_dark",
                            color_discrete_sequence=px.colors.qualitative.Bold,
                        )
                        fig.update_layout(height=400, showlegend=False)
                        st.plotly_chart(fig, use_container_width=True)

                        with st.expander("📋 View Raw Data Table"):
                            st.dataframe(df, use_container_width=True)

    # Handle Input from Chat Box or Sample Button
    prompt = st.chat_input("Ask anything about orders, products, revenue, or store policies...")
    
    if getattr(st.session_state, "pending_prompt", None):
        prompt = st.session_state.pending_prompt
        st.session_state.pending_prompt = None

    if prompt:
        # Display User Message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Process with LangGraph Router
        with st.chat_message("assistant"):
            with st.spinner("Supervisor Agent routing and retrieving answer..."):
                try:
                    result = router.invoke({
                        "question": prompt,
                        "route": "",
                        "answer": "",
                    })

                    route = result.get("route", "sql")
                    full_answer = result.get("answer", "")

                    # Extract SQL Query if embedded in answer
                    sql_query = None
                    clean_answer = full_answer
                    if "[SQL Query Used]" in full_answer:
                        parts = full_answer.split("[SQL Query Used]")
                        clean_answer = parts[0].strip()
                        sql_query = parts[1].strip()

                    # Render Routing Badge
                    if route == "sql":
                        st.markdown('<span class="badge-sql">📊 SQL DATA AGENT</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="badge-rag">📚 POLICY RAG ENGINE</span>', unsafe_allow_html=True)

                    st.markdown(clean_answer)

                    # Expandable SQL Query Code Block
                    if sql_query:
                        with st.expander("🔍 View Executed SQL Query"):
                            st.code(sql_query, language="sql")

                    # Attempt Data Visualization for SQL Results
                    chart_df = None
                    if route == "sql" and sql_query:
                        try:
                            engine = get_engine()
                            chart_df = pd.read_sql(sql_query, con=engine)
                            if not chart_df.empty and len(chart_df.columns) >= 2:
                                num_cols = chart_df.select_dtypes(include=["number"]).columns
                                if len(num_cols) > 0:
                                    col_x = chart_df.columns[0]
                                    col_y = num_cols[0]
                                    st.markdown("##### 📈 Interactive Data Chart")
                                    fig = px.bar(
                                        chart_df,
                                        x=col_x,
                                        y=col_y,
                                        color=col_x,
                                        text_auto=True,
                                        title=f"{col_y.replace('_', ' ').title()} by {col_x.replace('_', ' ').title()}",
                                        template="plotly_dark",
                                        color_discrete_sequence=px.colors.qualitative.Bold,
                                    )
                                    fig.update_layout(height=400, showlegend=False)
                                    st.plotly_chart(fig, use_container_width=True)

                                    with st.expander("📋 View Raw Data Table"):
                                        st.dataframe(chart_df, use_container_width=True)
                        except Exception:
                            chart_df = None

                    # Save to Session State
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": clean_answer,
                        "route": route,
                        "sql_query": sql_query,
                        "chart_data": chart_df,
                    })

                except Exception as e:
                    st.error(f"Error processing query: {e}")


if __name__ == "__main__":
    main()
