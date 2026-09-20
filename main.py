"""
main.py
=======
Central interactive CLI that initializes all components (database ingestion,
FAISS index, SQL agent, LangGraph router) and accepts user queries in a
loop, displaying the routed answers from either the SQL or RAG sub-agent.
"""

import sys
import os
import warnings

# Fix Windows console encoding for Unicode output
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        reconfig_out = getattr(sys.stdout, "reconfigure", None)
        if callable(reconfig_out):
            reconfig_out(encoding="utf-8")
        reconfig_err = getattr(sys.stderr, "reconfigure", None)
        if callable(reconfig_err):
            reconfig_err(encoding="utf-8")
    except Exception:
        pass

# Suppress noisy warnings from transformers/torch during startup
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)


def main() -> None:
    """
    Master entry point:
      1. Loads CSV data into PostgreSQL (idempotent -- skips if already loaded).
      2. Initializes the RAG engine (FAISS index + embedding model).
      3. Initializes the SQL agent (schema introspection + LLM).
      4. Builds the LangGraph router graph.
      5. Enters an interactive query loop.
    """
    # ------------------------------------------------------------------
    # Banner
    # ------------------------------------------------------------------
    print("=" * 70)
    print("  [*] AGENTIC TEXT-TO-SQL & DOCUMENT RAG ENGINE")
    print("      Powered by LangGraph | LangChain | FAISS | PostgreSQL")
    print("=" * 70)
    print()

    # ------------------------------------------------------------------
    # Phase 1: Data ingestion (CSV -> PostgreSQL)
    # ------------------------------------------------------------------
    from database.load_data import load_all_data
    load_all_data()

    # ------------------------------------------------------------------
    # Phase 2: RAG engine initialization (FAISS + sentence-transformers)
    # ------------------------------------------------------------------
    from agents.rag_engine import init_rag_engine
    init_rag_engine()

    # ------------------------------------------------------------------
    # Phase 3: SQL agent initialization (schema introspection + LLM)
    # ------------------------------------------------------------------
    from agents.sql_agent import init_sql_agent
    init_sql_agent()

    # ------------------------------------------------------------------
    # Phase 4: Build the LangGraph router
    # ------------------------------------------------------------------
    from agents.router import build_router_graph
    print("[Phase 4] Building LangGraph router...")
    router = build_router_graph()
    print("[Phase 4] [OK] Router compiled.\n")

    # ------------------------------------------------------------------
    # Interactive loop
    # ------------------------------------------------------------------
    print("=" * 70)
    print("  SYSTEM READY -- Ask anything about orders, products,")
    print("  customers, revenue, or platform policies.")
    print("  Type 'quit' or 'exit' to stop.")
    print("=" * 70)
    print()

    while True:
        try:
            question = input("[?] You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[*] Goodbye!")
            break

        # Skip empty input
        if not question:
            continue

        # Exit commands
        if question.lower() in ("quit", "exit", "q"):
            print("[*] Goodbye!")
            break

        # Invoke the LangGraph router with the user's question
        print()
        try:
            result = router.invoke({
                "question": question,
                "route": "",
                "answer": "",
            })
            print()
            print("-" * 70)
            print(f"[Answer]\n\n{result['answer']}")
            print("-" * 70)
        except Exception as e:
            print(f"\n[!] Error processing query: {e}")

        print()


if __name__ == "__main__":
    main()
