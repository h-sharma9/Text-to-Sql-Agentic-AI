"""
agents/sql_agent.py
===================
Text-to-SQL agent that inspects the live PostgreSQL schema, sends it along
with the user's natural-language question to GPT to generate a valid SELECT
query, executes it safely (read-only), and returns a human-readable answer.
"""

from pydantic import SecretStr
from sqlalchemy import text, inspect
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from config import API_KEY, LLM_BASE_URL, LLM_MODEL_NAME, LLM_TEMPERATURE
from database.connection import get_engine


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------
_llm: ChatOpenAI | None = None
_schema_description: str = ""


# ===========================================================================
# SCHEMA INTROSPECTION -- build a text description of every table + column
# ===========================================================================

def _introspect_schema() -> str:
    """
    Use SQLAlchemy's inspector to read the live database and produce a
    plain-text description of every table, its columns (with types), and
    primary/foreign keys -- this is what the LLM sees when generating SQL.
    """
    engine = get_engine()
    insp = inspect(engine)
    lines: list[str] = []

    for table_name in sorted(insp.get_table_names()):
        lines.append(f"\nTABLE: {table_name}")
        lines.append("-" * (len(table_name) + 7))

        # Columns
        columns = insp.get_columns(table_name)
        pk_constraint = insp.get_pk_constraint(table_name)
        pk_cols = pk_constraint.get("constrained_columns", []) or []

        for col in columns:
            pk_marker = " [PK]" if col["name"] in pk_cols else ""
            nullable = " (nullable)" if col.get("nullable") else ""
            lines.append(f"  {col['name']:40s} {str(col['type']):20s}{pk_marker}{nullable}")

        # Foreign keys
        fks = insp.get_foreign_keys(table_name)
        if fks:
            lines.append("  Foreign Keys:")
            for fk in fks:
                src = ", ".join(fk["constrained_columns"])
                tgt_table = fk["referred_table"]
                tgt_cols = ", ".join(fk["referred_columns"])
                lines.append(f"    {src} -> {tgt_table}({tgt_cols})")

    return "\n".join(lines)


# ===========================================================================
# INITIALIZATION
# ===========================================================================

def init_sql_agent() -> None:
    """
    Initialize the SQL agent by introspecting the database schema and
    instantiating the LLM used for query generation.
    """
    global _llm, _schema_description

    print("[Phase 3] Initializing SQL agent...")
    _schema_description = _introspect_schema()
    print(f"         [OK] Introspected live database schema.")

    _llm = ChatOpenAI(
        model=LLM_MODEL_NAME,
        temperature=LLM_TEMPERATURE,
        api_key=SecretStr(API_KEY),
        base_url=LLM_BASE_URL,
    )
    print("[Phase 3] [DONE] SQL agent ready.\n")


# ===========================================================================
# SQL GENERATION PROMPT
# ===========================================================================

_SQL_GENERATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert PostgreSQL analyst. Given the database schema below "
            "and a user question, generate a SINGLE valid PostgreSQL SELECT query "
            "that answers the question.\n\n"
            "RULES:\n"
            "1. Output ONLY the raw SQL query -- no markdown, no explanation, no backticks.\n"
            "2. Use ONLY SELECT statements. Never generate INSERT, UPDATE, DELETE, DROP, "
            "   ALTER, CREATE, or any DDL/DML that modifies data.\n"
            "3. Always LIMIT results to at most 20 rows unless the user explicitly asks "
            "   for more.\n"
            "4. Use table and column names EXACTLY as shown in the schema.\n"
            "5. Prefer JOINs over subqueries when possible for readability.\n\n"
            "--- DATABASE SCHEMA ---\n{schema}\n--- END SCHEMA ---",
        ),
        ("human", "{question}"),
    ]
)

_ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a friendly data analyst. The user asked a question about an "
            "e-commerce database. Below is the SQL query that was executed and its "
            "results. Summarize the results in clear, natural language. "
            "Include specific numbers. If the results are empty, say so.\n\n"
            "SQL Query:\n{sql}\n\n"
            "Results:\n{results}",
        ),
        ("human", "{question}"),
    ]
)


# ===========================================================================
# QUERY EXECUTION -- the core Text-to-SQL pipeline
# ===========================================================================

def query_database(question: str) -> str:
    """
    Answer a natural-language question about the e-commerce database by:
      1. Generating a SQL query via GPT using the live schema.
      2. Validating the query is a safe SELECT.
      3. Executing it against PostgreSQL.
      4. Sending the raw results back to GPT for a natural-language summary.

    Returns the final human-readable answer string.
    """
    if _llm is None:
        return "[!] SQL agent not initialized. Call init_sql_agent() first."

    # --- Step 1: Generate SQL ---
    gen_chain = _SQL_GENERATION_PROMPT | _llm
    sql_response = gen_chain.invoke({
        "schema": _schema_description,
        "question": question,
    })
    generated_sql = str(sql_response.content).strip()

    # --- Step 2: Safety check -- only allow SELECT ---
    sql_upper = generated_sql.upper().lstrip()
    if not sql_upper.startswith("SELECT"):
        return (
            "[!] The generated query was not a SELECT statement and was blocked "
            "for safety. Only read-only queries are permitted."
        )

    # Block dangerous keywords even inside a SELECT (e.g., SELECT ... INTO)
    dangerous = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE"}
    # Tokenize the SQL (rough but effective for a safety gate)
    tokens = set(sql_upper.replace("(", " ").replace(")", " ").split())
    if tokens & dangerous:
        return "[!] The generated query contained disallowed keywords and was blocked."

    # --- Step 3: Execute the query ---
    engine = get_engine()
    try:
        with engine.connect() as conn:
            result = conn.execute(text(generated_sql))
            columns = list(result.keys())
            rows = result.fetchall()
    except Exception as e:
        return f"[!] SQL execution error: {e}\n\nGenerated SQL:\n{generated_sql}"

    # Format results as a readable table string for the LLM
    if not rows:
        results_text = "(No results returned)"
    else:
        header = " | ".join(columns)
        separator = "-+-".join("-" * len(c) for c in columns)
        row_lines = [" | ".join(str(val) for val in row) for row in rows[:20]]
        results_text = f"{header}\n{separator}\n" + "\n".join(row_lines)
        if len(rows) > 20:
            results_text += f"\n... ({len(rows)} total rows, showing first 20)"

    # --- Step 4: Generate natural-language answer ---
    answer_chain = _ANSWER_PROMPT | _llm
    answer_response = answer_chain.invoke({
        "sql": generated_sql,
        "results": results_text,
        "question": question,
    })

    # Return the answer with the SQL query appended for transparency
    return (
        f"{str(answer_response.content)}\n\n"
        f"[SQL Query Used]\n{generated_sql}"
    )
