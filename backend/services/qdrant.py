from __future__ import annotations

import uuid
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    HnswConfigDiff,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    ScalarQuantization,
    ScalarQuantizationConfig,
    ScalarType,
    SearchParams,
    VectorParams,
)

from backend.core.config import settings
from backend.core.exceptions import QdrantError
from backend.services.embeddings import EMBEDDING_DIM, embed_paper, embed_query

COLLECTION = settings.qdrant_collection


def _client() -> AsyncQdrantClient:
    return AsyncQdrantClient(url=settings.qdrant_cluster_id, api_key=settings.qdrant_api_key)


async def ensure_collection() -> None:
    """Idempotent — creates collection + payload indexes if missing."""
    async with _client() as client:
        if await client.collection_exists(COLLECTION):
            return

        await client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(
                size=EMBEDDING_DIM,
                distance=Distance.COSINE,
                on_disk=False,
            ),
            hnsw_config=HnswConfigDiff(
                m=16,
                ef_construct=200,
                full_scan_threshold=10_000,  # exact search below this count
                on_disk=False,
            ),
            quantization_config=ScalarQuantization(
                scalar=ScalarQuantizationConfig(
                    type=ScalarType.INT8,
                    quantile=0.99,   # clip top 1% of values for better quantization
                    always_ram=True, # keep quantized vectors in RAM
                )
            ),
            on_disk_payload=False,
        )

        # Payload indexes for filtered search
        await client.create_payload_index(COLLECTION, "url_hash", PayloadSchemaType.KEYWORD)
        await client.create_payload_index(COLLECTION, "year", PayloadSchemaType.INTEGER)
        await client.create_payload_index(COLLECTION, "source", PayloadSchemaType.KEYWORD)


async def upsert_paper(
    *,
    paper_id: str,
    url_hash: str,
    title: str,
    abstract: str | None,
    year: int | None,
    source: str,
    extra_payload: dict[str, Any] | None = None,
) -> str:
    """Embed + upsert one paper. Returns the Qdrant point ID (UUID string)."""
    vector = embed_paper(title, abstract)
    point_id = str(uuid.uuid4())

    payload: dict[str, Any] = {
        "paper_id": paper_id,
        "url_hash": url_hash,
        "title": title,
        "year": year,
        "source": source,
    }
    if extra_payload:
        payload.update(extra_payload)

    async with _client() as client:
        await client.upsert(
            collection_name=COLLECTION,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )
    return point_id


async def search_similar(
    query: str,
    *,
    top_k: int = 10,
    score_threshold: float = 0.0,
    year_min: int | None = None,
) -> list[dict[str, Any]]:
    """
    Semantic search with BGE query instruction.
    Returns list of {qdrant_id, score, payload} dicts.
    """
    vector = embed_query(query)

    filters: list[FieldCondition] = []
    if year_min is not None:
        from qdrant_client.models import Range
        filters.append(FieldCondition(key="year", range=Range(gte=year_min)))

    query_filter = Filter(must=filters) if filters else None

    async with _client() as client:
        results = await client.search(
            collection_name=COLLECTION,
            query_vector=vector,
            limit=top_k,
            query_filter=query_filter,
            score_threshold=score_threshold,
            search_params=SearchParams(
                hnsw_ef=128,     # higher ef = better recall at query time
                exact=False,     # flip to True for tiny collections (<10k)
            ),
            with_payload=True,
        )

    return [
        {"qdrant_id": str(r.id), "score": r.score, "payload": r.payload}
        for r in results
    ]


async def is_duplicate(vector: list[float], threshold: float | None = None) -> bool:
    """True if any stored paper has cosine similarity >= threshold to this vector."""
    threshold = threshold or settings.qdrant_dedup_threshold
    async with _client() as client:
        results = await client.search(
            collection_name=COLLECTION,
            query_vector=vector,
            limit=1,
            score_threshold=threshold,
            search_params=SearchParams(hnsw_ef=64, exact=False),
            with_payload=False,
        )
    return len(results) > 0


async def get_by_url_hash(url_hash: str) -> dict[str, Any] | None:
    """Fetch a stored point by url_hash payload field."""
    async with _client() as client:
        results, _ = await client.scroll(
            collection_name=COLLECTION,
            scroll_filter=Filter(
                must=[FieldCondition(key="url_hash", match=MatchValue(value=url_hash))]
            ),
            limit=1,
            with_payload=True,
            with_vectors=False,
        )
    if not results:
        return None
    r = results[0]
    return {"qdrant_id": str(r.id), "payload": r.payload}
