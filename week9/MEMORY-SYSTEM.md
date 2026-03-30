# Memory System Architecture (Day 4)

## Overview

This document outlines the multi-tiered memory architecture implemented for the autonomous agent system. The system uses a hybrid approach, combining short-term conversational context with persistent, retrieval-augmented long-term memory to ensure the agent maintains consistency across sessions.

## Architecture & Components

The memory system is divided into three primary tiers:

1. Short-Term Memory (SessionMemory)

- Type: In-process / RAM

- Purpose: Maintains the immediate back-and-forth conversational context.

- Implementation: Keeps a sliding window of the last N (default: 20) messages. It automatically drops the oldest messages to prevent the LLM's context window from overflowing.

2. Vector Memory (VectorStore)

- Type: Persistent / FAISS

- Purpose: Enables semantic similarity search (understanding the "meaning" of a query).

- Implementation: Uses sentence-transformers (default: all-MiniLM-L6-v2) to convert text into embeddings. These embeddings are indexed using FAISS (IndexFlatIP) for rapid mathematical similarity matching.

3. Long-Term SQL Memory (LongTermStore)

- Type: Persistent / SQLite

- Purpose: Serves as a keyword-based fallback and exact-match storage.

- Implementation: Stores facts in a lightweight local long_term.db database. It allows the system to easily retrieve facts using exact word matching (e.g., retrieving "age" when the user asks "what is my age").

## AutoGen Integration (FactMemory)

To make these independent databases work seamlessly with Microsoft AutoGen, they are wrapped in a FactMemory class that strictly implements AutoGen's Memory protocol:

- add(): Saves a fact simultaneously to both FAISS and SQLite.

- query(): Performs a dual-search (Semantic + Keyword) and returns a deduplicated list of relevant facts.

- update_context(): Automatically inspects the latest user message, queries the database, and injects the retrieved facts directly into the agent's prompt before generation.

## Agentic Execution Flow (RAG Pattern)

The system operates on a Retrieval-Augmented Generation (RAG) loop combined with autonomous tool calling:

New Query: The user inputs a message (e.g., "What are my hobbies?").

Search Memory: The FactMemory.update_context() method catches the query.

Fetch Similar Context: Both FAISS (semantic) and SQLite (keyword) are queried for relevant past facts.

Inject in Prompt: The retrieved facts are formatted and injected invisibly into the LLM's system prompt as Relevant long-term facts:.

Generate with Context: The agent reads the injected context and answers the user accurately.

## Autonomous Fact Saving (Tool Calling)

Instead of polluting the vector database with every casual message ("hi", "thanks"), the agent is empowered to actively manage its own memory.

- The Tool: The agent is provided a save_core_fact tool.

- The Trigger: The agent's system prompt strictly instructs it: "If the user reveals a NEW important fact (name, preference, goal), you MUST call the save_core_fact tool."

- The Result: The agent acts as a gatekeeper, intelligently extracting only valuable information and committing it to long-term storage, while filtering out conversational noise.