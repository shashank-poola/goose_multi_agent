"""
BAAI/bge-large-en-v1.5 — 1024 dims, MTEB top retrieval model (CPU-friendly).

BGE instruction convention:
  - Documents: no prefix (embed as-is)
  - Queries:   prepend QUERY_INSTRUCTION before encoding
"""

from __future__ import annotations

from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-large-en-v1.5"
EMBEDDING_DIM = 1024
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_papers(texts: list[str]) -> list[list[float]]:
    """Embed a batch of document texts (title + abstract). No instruction prefix."""
    model = _get_model()
    vecs = model.encode(texts, normalize_embeddings=True, batch_size=16, show_progress_bar=False)
    return vecs.tolist()


def embed_paper(title: str, abstract: str | None = None) -> list[float]:
    text = f"{title}\n\n{abstract}" if abstract else title
    return embed_papers([text])[0]


def embed_query(query: str) -> list[float]:
    """Embed a search query with BGE instruction prefix for best recall."""
    model = _get_model()
    vec = model.encode(
        [QUERY_INSTRUCTION + query],
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vec[0].tolist()
