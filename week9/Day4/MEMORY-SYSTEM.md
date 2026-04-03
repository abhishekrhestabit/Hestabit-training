# Day 4 — Memory System Architecture

## Overview

A multi-tiered memory system for an autonomous agent that maintains context across sessions. Combines short-term conversational memory, FAISS-based semantic search, and SQLite persistent storage with category-based organization.

## Architecture

```
User Query
    │
    ▼
┌────────────────────────────────────────────────────────┐
│                    MemoryAgent                          │
│                                                         │
│  Before every LLM call, AutoGen auto-injects:          │
│    1. SessionMemory  → recent conversation turns        │
│    2. FactMemory     → semantically relevant facts      │
│                                                         │
│  Agent Tools:                                           │
│    save_core_fact(fact, category)                        │
│    get_facts_by_date(YYYY-MM-DD)                        │
│    get_facts_by_category(category)                      │
└────────────────────────────────────────────────────────┘
    │                           │
    ▼                           ▼
┌──────────────┐    ┌───────────────────────┐
│ SessionMemory │    │      FactMemory       │
│  (in-process) │    │  (FAISS + SQLite)     │
│  sliding 20   │    │                       │
│  messages     │    │  write → both stores  │
└──────────────┘    │  read  → vector first, │
                     │          SQL fallback  │
                     └───────────────────────┘
                         │              │
                         ▼              ▼
                   ┌──────────┐  ┌────────────┐
                   │  FAISS   │  │   SQLite    │
                   │ (semantic│  │ (keyword +  │
                   │  search) │  │  category)  │
                   └──────────┘  └────────────┘
```

## Memory Tiers

### 1. Session Memory (volatile)

- **Type:** In-process / RAM
- **Purpose:** Maintains the conversational context for the current session
- **Behavior:** Sliding window of last 20 messages. Oldest dropped automatically. Lost on restart.
- **Injection:** Formatted as a numbered list and added as a `UserMessage` before each LLM call.

### 2. Vector Store (persistent, semantic)

- **Type:** FAISS `IndexFlatIP` with normalized embeddings (cosine similarity)
- **Model:** `all-MiniLM-L6-v2` (sentence-transformers)
- **Purpose:** Semantic similarity search — understands the *meaning* of a query
- **Threshold:** 0.2 (tuned for short fact strings vs. conversational queries)
- **Top-k:** 5 results per query

### 3. Long-Term SQL Store (persistent, structured)

- **Type:** SQLite (`long_term.db`)
- **Purpose:** Keyword fallback, exact-match retrieval, and **category-based filtering**
- **Schema:**
  ```sql
  facts (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      content    TEXT NOT NULL,
      category   TEXT DEFAULT 'general',
      metadata   TEXT DEFAULT '{}',
      created_at TEXT NOT NULL
  )
  ```
- **Categories:** `personal`, `preference`, `work`, `health`, `hobby`, `goal`, `general`
- **Auto-migration:** Older DBs without the `category` column get it added via `ALTER TABLE` on startup.

## AutoGen Integration (FactMemory)

The `FactMemory` class implements AutoGen's `Memory` protocol, bridging FAISS and SQLite:

- **`add()`** — Saves a fact to both FAISS (for semantic search) and SQLite (for keyword/category search).
- **`query()`** — Runs FAISS semantic search first. Falls back to SQLite keyword search only if semantic search returns nothing.
- **`update_context()`** — Called automatically before every LLM turn. Takes the user's latest message, queries for relevant facts, and injects them into the prompt as `"Relevant long-term facts"`.

## Query Flow (per user message)

1. **Auto-injection:** Before each LLM call, `FactMemory.update_context()` runs a FAISS search on the user's message and injects top matches. This happens transparently on every turn.

2. **Tool-based retrieval:** For broad questions ("tell me about myself") or topic-specific queries ("what are my hobbies?"), the agent calls `get_facts_by_category` to pull the *complete* set of facts from SQLite — not just the top vector matches.

3. **Autonomous saving:** When the user reveals new facts, the agent calls `save_core_fact(fact, category)`. Compound statements are decomposed into atomic facts (e.g., "I'm 21 and like dogs" → 2 separate saves with different categories). Facts already in the injected context are skipped.

## Agent Tools

| Tool | Purpose | When Used |
|---|---|---|
| `save_core_fact(fact, category)` | Persist a new fact to FAISS + SQLite | User reveals personal info |
| `get_facts_by_date(YYYY-MM-DD)` | Retrieve all facts from a specific date | "What did we discuss yesterday?" |
| `get_facts_by_category(category)` | Retrieve ALL facts in a category via SQL | "Tell me about myself", "What are my hobbies?" |

## CLI Commands

| Command | Action |
|---|---|
| `stats` | Print memory state (session entries, vector entries, long-term facts) |
| `clear` | Wipe all memory (session + vector + SQLite) |
| `exit` | Quit and print final stats |

## File Structure

```
Day4/
├── day4.py                        ← Entry point, agent + CLI loop
├── memory/
│   ├── __init__.py
│   ├── session_memory.py          ← SessionMemory, FactMemory, MemorySystem
│   ├── vector_store.py            ← VectorStore (FAISS), LongTermStore (SQLite)
│   ├── long_term.db               ← SQLite persistent storage
│   └── vector_store/
│       ├── index.faiss            ← FAISS index file
│       └── meta.pkl               ← Vector metadata
├── config/
│   ├── __init__.py
│   ├── model_client.py
│   ├── gemini_client.py
│   └── models.yaml
└── MEMORY-SYSTEM.md
```

## Usage

```bash
python day4.py
# Interactive loop — memory persists across sessions

python day4.py "what do you know about me?"
# Single query mode — runs one turn and exits
```
