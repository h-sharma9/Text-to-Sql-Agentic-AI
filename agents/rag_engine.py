"""
agents/rag_engine.py
====================
Chunks the e-commerce policy document, embeds each chunk with sentence-
transformers, builds/loads a FAISS vector index, and provides a
query_policies() function that retrieves relevant chunks and sends them to
GPT for a grounded, citation-backed answer.
"""

import os
import json
import numpy as np
import faiss
from pydantic import SecretStr
from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from config import (
    POLICY_FILE,
    FAISS_INDEX_DIR,
    EMBEDDING_MODEL_NAME,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    API_KEY,
    LLM_BASE_URL,
    LLM_MODEL_NAME,
    LLM_TEMPERATURE,
)


# ---------------------------------------------------------------------------
# Module-level singletons -- initialized once by init_rag_engine().
# ---------------------------------------------------------------------------
_faiss_index: faiss.Index | None = None
_chunks: list[str] = []
_embedder: SentenceTransformer | None = None
_llm: ChatOpenAI | None = None


# ===========================================================================
# CHUNKING -- split the policy text into overlapping windows
# ===========================================================================

def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split the input text into overlapping chunks of approximately `size`
    characters, with `overlap` characters shared between consecutive chunks
    to preserve context across boundaries.
    """
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += size - overlap
    return chunks


# ===========================================================================
# EMBEDDING + FAISS INDEX MANAGEMENT
# ===========================================================================

def _build_faiss_index(chunks: list[str], embedder: SentenceTransformer) -> faiss.Index:
    """
    Encode all chunks into dense vectors and build an L2 FAISS index for
    fast nearest-neighbor retrieval at query time.
    """
    # Encode chunks -> numpy float32 matrix  (n_chunks x embedding_dim)
    embeddings = embedder.encode(chunks, show_progress_bar=True, convert_to_numpy=True)
    embeddings = np.array(embeddings, dtype="float32")

    # Normalize for cosine-similarity via inner-product after normalization
    faiss.normalize_L2(embeddings)

    # Build a flat (brute-force) inner-product index -- exact search,
    # perfectly adequate for a small document corpus.
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    return index


def _save_index(index: faiss.Index, chunks: list[str]) -> None:
    """Persist the FAISS index and chunk metadata to disk for fast reload."""
    os.makedirs(FAISS_INDEX_DIR, exist_ok=True)
    faiss.write_index(index, os.path.join(FAISS_INDEX_DIR, "policy.index"))
    with open(os.path.join(FAISS_INDEX_DIR, "chunks.json"), "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)


def _load_index() -> tuple[faiss.Index, list[str]] | None:
    """Load a previously saved FAISS index and chunks from disk, or None."""
    idx_path = os.path.join(FAISS_INDEX_DIR, "policy.index")
    chunks_path = os.path.join(FAISS_INDEX_DIR, "chunks.json")
    if os.path.isfile(idx_path) and os.path.isfile(chunks_path):
        index = faiss.read_index(idx_path)
        with open(chunks_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        return index, chunks
    return None


# ===========================================================================
# INITIALIZATION -- call once at startup
# ===========================================================================

def init_rag_engine() -> None:
    """
    Initialize the RAG engine by:
      1. Loading the sentence-transformer embedding model.
      2. Loading or building the FAISS index from the policy document.
      3. Instantiating the LLM used for answer generation.
    """
    global _faiss_index, _chunks, _embedder, _llm

    print("[Phase 2] Initializing RAG engine...")

    # --- Embedding model (runs locally on CPU) ---
    print("         Loading embedding model:", EMBEDDING_MODEL_NAME)
    _embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)

    # --- Try loading a cached index first ---
    cached = _load_index()
    if cached is not None:
        _faiss_index, _chunks = cached
        print(f"         [OK] Loaded cached FAISS index ({len(_chunks)} chunks).")
    else:
        # Read the policy file
        print("         Reading policy document:", POLICY_FILE)
        with open(POLICY_FILE, "r", encoding="utf-8") as f:
            raw_text = f.read()

        # Chunk and index
        _chunks = _chunk_text(raw_text)
        print(f"         Chunked into {len(_chunks)} segments. Building FAISS index...")
        _faiss_index = _build_faiss_index(_chunks, _embedder)
        _save_index(_faiss_index, _chunks)
        print("         [OK] FAISS index built and saved to disk.")

    # --- LLM for answer synthesis ---
    _llm = ChatOpenAI(
        model=LLM_MODEL_NAME,
        temperature=LLM_TEMPERATURE,
        api_key=SecretStr(API_KEY),
        base_url=LLM_BASE_URL,
    )
    print("[Phase 2] [DONE] RAG engine ready.\n")


# ===========================================================================
# QUERY -- retrieve relevant chunks and generate an answer
# ===========================================================================

# The prompt template instructs GPT to answer ONLY from the provided context.
_RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful e-commerce policy assistant for the Olist platform. "
            "Answer the user's question based ONLY on the policy context provided below. "
            "If the context does not contain enough information to answer, say so clearly. "
            "Cite the relevant policy section number(s) in your answer.\n\n"
            "--- POLICY CONTEXT ---\n{context}\n--- END CONTEXT ---",
        ),
        ("human", "{question}"),
    ]
)


def query_policies(question: str, top_k: int = 3) -> str:
    """
    Answer a user question about e-commerce policies by:
      1. Embedding the question with the same sentence-transformer model.
      2. Retrieving the top-k most similar chunks from the FAISS index.
      3. Sending the retrieved context + question to GPT for a grounded answer.

    Returns the LLM-generated answer string.
    """
    if _faiss_index is None or _embedder is None or _llm is None:
        return "[!] RAG engine not initialized. Call init_rag_engine() first."

    # Embed the query
    q_vec = _embedder.encode([question], convert_to_numpy=True).astype("float32")
    faiss.normalize_L2(q_vec)

    # Search the index
    scores, indices = _faiss_index.search(q_vec, top_k)

    # Gather retrieved chunks
    retrieved = [_chunks[i] for i in indices[0] if i < len(_chunks)]
    context = "\n\n".join(retrieved)

    # Generate answer via LLM
    chain = _RAG_PROMPT | _llm
    response = chain.invoke({"context": context, "question": question})

    return str(response.content)
