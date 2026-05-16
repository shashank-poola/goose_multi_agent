# Goose — Multi-Tier AI Research Agent

Differentiator: contradiction detection + research gap analysis across papers. Not summarization.

## Tiers (each = separate LangGraph graph)

| Tier | Agents | Papers | Models | Cost cap | Time |
|------|--------|--------|--------|----------|------|
| Ultra | 7, parallel | 10–20 | Sonnet synthesis | $1.50 | 2–4 min |
| Maverick | 5, single stream | 5–10 | Haiku synthesis | $0.30 | <90s |
| Remi | 3, sequential | 2–5 | Gemini Flash synthesis | $0.05 | 15–30s |

**Build order: Remi → Maverick → Ultra.**

## Stack

- Backend: Python 3.13, FastAPI (async only), LangGraph
- Models: OpenRouter with OpenAI-compatible SDK (one client, routing table in `backend/models/router.py`)
- Search: Exa — `search` for queries, `find_similar` for seed URL expansion
- Cache: Redis — Exa results (7-day TTL, keyed by URL hash)
- Vectors: Qdrant + sentence-transformers (CPU). Dedup threshold: cosine 0.92
- DB: PostgreSQL — sessions, reports, paper metadata
- Queue: BullMQ (Redis) — async Ultra jobs
- Frontend: Next.js, SSE streaming

## Model Routing

| Agent | Model |
|-------|-------|
| Search, Decompose | Gemini Flash 2.0 |
| Contradiction, Gap | Claude Haiku 4.5 |
| Synthesis (Ultra) | Claude Sonnet 4.5 |
| Synthesis (Maverick) | Claude Haiku 4.5 |
| Synthesis (Remi) | Gemini Flash 2.0 |

## Shared State (`ResearchState` TypedDict)

`query`, `tier`, `papers`, `claims`, `primitives`, `contradictions`, `gaps`, `synthesis`, `citations`, `confidence_scores`, `cost_usd` (Annotated[float, operator.add]), `agent_log` (append-only)

## Cost Guard

Every agent node checks `cost_usd < tier_cap` before any LLM call. On breach → emergency synthesis node returns partial report + warning.

## Folder Layout

```
backend/
  agents/      # one file per agent, pure state→state functions
  graphs/      # ultra.py, maverick.py, remi.py, base.py
  models/      # router.py, client.py, prompts.py
  services/    # exa.py, embeddings.py, qdrant.py
  api/         # FastAPI: POST /research, GET /session/{id}/stream (SSE), GET /sessions
  core/        # config, cost_guard, logger, exceptions
frontend/
  src/components/  # TierSelector, ResearchStream, ReportView, AgentTimeline, CostBadge
```

## Exa Pattern

1. Check Qdrant (cosine > 0.92 → skip)
2. Check Redis cache (URL hash → return cached)
3. Call Exa → cache in Redis → embed → store in Qdrant
4. `find_similar` on top 3 results to expand paper set

## 5 Classifier Primitives (Ultra/Maverick)

task complexity, skill level required, use case type, AI autonomy level, success likelihood
(from Anthropic Economic Index methodology)
