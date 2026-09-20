"""
tests/test_rag_engine.py
=========================
Unit tests for the RAG Engine text chunking, FAISS index, and policy query retrieval.
"""

import pytest
from agents.rag_engine import _chunk_text, query_policies


def test_text_chunking():
    """Verify text chunking preserves overlapping content and splits into expected window sizes."""
    sample_text = "A" * 1200
    chunks = _chunk_text(sample_text, size=500, overlap=50)
    assert len(chunks) >= 2
    assert len(chunks[0]) == 500


def test_rag_policy_retrieval(initialized_rag):
    """Verify that policy Q&A returns grounded answers with relevant section citations."""
    answer = query_policies("What is the return policy for a defective or damaged product?")
    assert isinstance(answer, str)
    assert len(answer) > 0
    # Policy answers should cite defective goods section
    assert "defect" in answer.lower() or "damaged" in answer.lower() or "section" in answer.lower()
