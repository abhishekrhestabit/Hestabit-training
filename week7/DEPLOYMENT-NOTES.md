# DEPLOYMENT-NOTES.md — Day 5 Capstone

## Overview
The system is a unified CLI-based RAG engine exposing three endpoints: `/ask` (text RAG), `/ask-sql` (structured data), and `/ask-image` (multimodal retrieval). All three share a common memory, evaluation, and refinement layer.

## Architecture

**`/ask`** loads a `ContextBuilder` which runs hybrid retrieval (FAISS MMR + BM25 with manual RRF fusion) followed by cross-encoder reranking. The top chunks are injected into a Gemini prompt. The response is evaluated for faithfulness; if flagged, a stricter prompt is issued and re-evaluated.

**`/ask-sql`** loads CSVs into an in-memory SQLite database. A `SQLGenerator` uses the schema to produce a SELECT query via Gemini. The results are fetched and summarised by a second LLM call. Unsafe DML/DDL is blocked at the generator level. Failed queries are auto-corrected once before returning an error.

**`/ask-image`** uses two separate FAISS indices built during ingestion. For text→image search, the query is embedded with CLIP and searched against a pure CLIP image embedding index. For image→image search, the query image is captioned with BLIP, the caption and image are embedded independently with CLIP, fused (60/40 weighted), and searched against the fused index. OCR text is incorporated into the fused vector when present.

## Memory
`MemoryStore` persists every interaction to `CHAT-LOGS.json` with a timestamp and evaluation metadata. The file is trimmed to the last 5 exchanges (10 messages) on every write, so it never grows beyond that limit. The last 5 exchanges are prepended to each prompt as conversational context.

A dedicated `/history` endpoint displays all stored exchanges with timestamps and roles at any point during the session, independent of the other endpoints.

## Evaluation & Self-Refinement
`RAGEvaluator` submits a structured judge prompt to Gemini and expects a JSON response containing `is_faithful`, `confidence_score`, and `critique`. If `is_faithful` is false, the engine automatically re-runs the endpoint with a stricter prompt and re-evaluates. The second result is used regardless.

## Lazy Loading
Each pipeline (text retriever, SQL engine, image engine) is initialised only on first use via Python properties. This keeps startup time minimal and avoids loading unused models.

## Known Limitations
- The in-memory SQLite database is rebuilt on every run from source CSVs.
- The evaluator adds one additional LLM round-trip per query; this increases latency.
- Image→image search requires the query BLIP caption to be a good proxy for visual content, which may degrade on abstract or non-photographic images.


## Outputs

- /ask-image
![alt text](Day5/ask-image.png)

- /ask-sql
![alt text](Day5/ask-sql.png) 

- /ask
![alt text](Day5/ask.png) 

- /ask-image (via text)
![alt text](Day5/ask-text-image.png)

- /history
![alt text](Day5/history.png)