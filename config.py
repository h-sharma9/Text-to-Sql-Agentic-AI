"""
config.py
=========
Central configuration file that loads environment variables from .env and
exposes all shared constants (database URL, API keys, model names, file paths)
used by every other module in the project.
"""

import os
from dotenv import load_dotenv  # pyrefly: ignore[missing-import]

# ---------------------------------------------------------------------------
# Load the .env file from the project root so that OPENAI_API_KEY and
# DATABASE_URL become available as environment variables.
# ---------------------------------------------------------------------------
load_dotenv()

# Fallback to Streamlit secrets when running on Streamlit Community Cloud
_st_secrets = {}
try:
    import streamlit as _st
    if hasattr(_st, "secrets"):
        _st_secrets = dict(_st.secrets)
except Exception:
    pass

# ---------------------------------------------------------------------------
# Database configuration
# ---------------------------------------------------------------------------
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    _st_secrets.get("DATABASE_URL", "postgresql://postgres:password@localhost:5432/agentic_db")
)

# ---------------------------------------------------------------------------
# LLM configuration (OpenAI / Groq auto-detection)
# ---------------------------------------------------------------------------
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", _st_secrets.get("OPENAI_API_KEY", ""))
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", _st_secrets.get("GROQ_API_KEY", ""))

# Prioritize Groq API key if provided or if OPENAI_API_KEY starts with gsk_
API_KEY: str = GROQ_API_KEY or OPENAI_API_KEY
LLM_BASE_URL: str | None = None

if API_KEY.startswith("gsk_") or GROQ_API_KEY:
    LLM_BASE_URL = "https://api.groq.com/openai/v1"
    LLM_MODEL_NAME: str = "openai/gpt-oss-20b"
else:
    LLM_MODEL_NAME: str = "gpt-4o-mini"

LLM_TEMPERATURE: float = 0.0

# ---------------------------------------------------------------------------
# Embedding model (sentence-transformers) -- runs locally, no API cost
# ---------------------------------------------------------------------------
EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"

# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------
DATA_DIR: str = os.path.join(os.path.dirname(__file__), "data")
POLICY_FILE: str = os.path.join(DATA_DIR, "ecommerce_policies.txt")
FAISS_INDEX_DIR: str = os.path.join(os.path.dirname(__file__), "faiss_index")

# ---------------------------------------------------------------------------
# RAG chunking parameters
# ---------------------------------------------------------------------------
CHUNK_SIZE: int = 500          # Characters per chunk
CHUNK_OVERLAP: int = 50        # Overlap between consecutive chunks

# ---------------------------------------------------------------------------
# CSV file manifest -- order matters for FK-safe loading
# ---------------------------------------------------------------------------
CSV_FILES: list[str] = [
    "olist_geolocation_dataset.csv",
    "olist_customers_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
    "olist_products_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
]
