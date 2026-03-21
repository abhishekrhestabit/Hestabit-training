# MEMORY-SYSTEM.md — Day 4

## Overview

Day 4 is a memory-augmented chat system demonstrating three distinct
memory layers — each with a different purpose, storage mechanism, and
retrieval strategy.

```
User message
    ↓
RECALL  — search all 3 layers → inject relevant context into prompt
    ↓
RESPOND — LLM answers using message + recalled context
    ↓
STORE   — extract only new, non-duplicate facts → save to vector + LTM
    ↓
Next message
```

---

## The Three Memory Layers

### Layer 1 — Session Memory (`memory/session_memory.py`)

| Property     | Value |
|---|---|
| Storage      | RAM only |
| Lifetime     | Current process — resets on exit |
| What it stores | Every conversation turn (user + assistant) |
| Window size  | Last 10 turns |
| Used for     | Rolling context so the model remembers earlier turns in THIS conversation |

Session memory is intentionally ephemeral — exactly like any chat app.
It does not persist to disk. When you exit, the conversation is gone.

---

### Layer 2 — Vector Store (`memory/vector_store.py`)

| Property     | Value |
|---|---|
| Storage      | `memory/memory.faiss` + `memory/memory.json` (disk) |
| Lifetime     | Persists across sessions |
| What it stores | **Distilled facts only** — not raw Q&A transcripts |
| Model        | `all-MiniLM-L6-v2` (384-dim, CPU-fast, ~80MB, downloads once) |
| Index        | FAISS IndexFlatL2 — exact nearest-neighbour search |
| Used for     | **Semantic recall** — find facts by *meaning*, not exact words |

**Why only facts, not everything?**
Storage is not the concern (1.5KB per vector). Search quality is.
If raw Q&A noise like `"Q: what's your name"` fills the index,
it crowds out real facts from the top-3 recall slots.
Only storing distilled facts keeps search quality high.

**What semantic search means in practice:**
```
You ask:  "what do I enjoy?"
FAISS finds: "user likes hiking"   ← 'enjoy' ≈ 'like' semantically
             "user loves Python"   ← found even without the word 'enjoy'
```
FAISS cannot filter by category. It only finds by similarity.

---

### Layer 3 — Long-Term DB (`memory/long_term.py` → `memory/long_term.db`)

| Property     | Value |
|---|---|
| Storage      | SQLite file (disk) |
| Lifetime     | Persists across sessions |
| What it stores | Same facts as vector store + **category tags** |
| Schema       | `facts(id, fact, source, tags, created, accessed)` |
| Used for     | **Structured recall** — filter by category, browse, delete |

**Why is LTM not a duplicate of Vector Store?**

Vector store finds by *meaning*. LTM organises by *category*.

```
"what do I enjoy?"          → Vector  (semantic — finds 'like', 'love', 'prefer')
"show me my health facts"   → LTM     (SQL: WHERE tags='health')
"show me my work facts"     → LTM     (SQL: WHERE tags='work')
"anything about hiking?"    → Vector  (semantic similarity)
```

Each fact is tagged automatically with one of:
`personal | preference | work | health | location | knowledge | other`

---

## How Facts Are Stored (Deduplication)

Before storing anything, the system checks existing facts against what
was just said. Only genuinely new, non-duplicate information is stored.

```
Session 1:  "My name is Abhishek"
            → new fact → stores: "The user's name is Abhishek" [personal]

Session 2:  "My name is Abhishek"
            → already known → stores nothing

Session 2:  "I'm 22 years old"
            → new fact → stores: "The user is 22 years old" [personal]
```

This mirrors how ChatGPT/Claude memory works — the system learns
incrementally, not by appending everything every time.

---

## What Each Layer Owns

```
Layer           Recall method           Write method
──────────────────────────────────────────────────────────────
SessionMemory   recall_context()        add_user() / add_assistant()
VectorStore     recall_context(query)   store_fact(fact)
LongTermMemory  get_as_context(kw)      store(fact, tags=[tag])
                get_by_source(tag)      store_episode(q, a)
```

No shared manager class — each layer owns its own recall and store logic.

---

## File Structure

```
day4/
├── day4_pipeline.py        ← entry point (run this)
├── model.yaml              ← Ollama / Gemini / Groq config
├── memory/
│   ├── __init__.py
│   ├── session_memory.py   ← RAM, current session
│   ├── vector_store.py     ← FAISS semantic search, persists
│   ├── long_term.py        ← SQLite tagged facts, persists
│   ├── memory.faiss        ← auto-created on first run
│   ├── memory.json         ← auto-created on first run
│   └── long_term.db        ← auto-created on first run
├── config/
│   └── model_loader.py
└── tools/
    ├── code_executor.py
    ├── db_agent.py
    └── file_agent.py
```

---

## How to Run

```bash
cd day4

# Local (Ollama)
ollama serve
ollama pull qwen2.5:3b-instruct-q4_K_M
python day4_pipeline.py

# Cloud (Gemini/Groq) — edit model.yaml first
python day4_pipeline.py
```

First run auto-installs `faiss-cpu` and `sentence-transformers` (~80MB, once only).

---

## CLI Commands

| Command | What it demonstrates |
|---|---|
| Any message | Full recall → respond → store cycle |
| `memory` | Shows all 3 layers: session turns, vector facts, LTM facts |
| `recall <category>` | **LTM's unique capability** — e.g. `recall personal`, `recall work` |
| `clear` | Wipes all memory across all 3 layers |
| `exit` | Quit (session resets, vector + LTM persist on disk) |

---

## Key Design Decisions

**Session resets on exit** — intentional. Same as any real chat app.
The conversation window is per-session. What persists is *what was learned*,
not the conversation transcript.

**Vector store = facts only** — storing raw Q&A inflates the index with
noise and degrades search quality. Only distilled facts go into FAISS.

**LTM = structured + tagged** — SQL lets you filter, delete, and audit
individual facts. FAISS cannot do any of that. Both are needed.

**Deduplication before storing** — the LLM checks existing facts before
adding new ones, preventing the same fact from being stored 50 times
across sessions.