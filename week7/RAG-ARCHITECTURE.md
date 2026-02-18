# RAG Architecture — Day 1

## What is RAG?

Retrieval-Augmented Generation (RAG) is an architecture that improves the quality of AI-generated answers by first retrieving relevant information from a knowledge base before generating a response. Instead of relying solely on what an LLM has memorised during training, RAG grounds the answer in actual documents you provide. This makes responses more accurate, up-to-date, and verifiable.

---

## Core Concepts

### Document Loading
- Raw documents (PDF, TXT, DOCX, CSV) are loaded and each page or row is treated as a document object.
- Metadata is attached at load time — including the file path, page number, file type, and a tag — so that every chunk can be traced back to its original source later.

### Chunking
- A full document is too large to embed as a single unit, so it is split into smaller overlapping chunks.
- Chunk size is set to 800 tokens with a 100-token overlap. The overlap ensures that sentences or ideas split across a boundary are still represented in at least one chunk.
- Smaller chunks improve retrieval precision because the vector more accurately captures a single idea rather than a mix of many.

### Embeddings
- Each chunk is converted into a dense numerical vector (an embedding) using a local sentence-transformer model (`all-MiniLM-L6-v2`).
- Embedding maps the semantic meaning of text into a 384-dimensional vector space, so chunks with similar meaning end up close together regardless of exact wording.
- The same model must be used both at ingest time and at query time. If different models are used, the vector spaces will not align and retrieval will be meaningless.
- This model runs entirely on CPU — no GPU or API key is needed.

### Vector Store (FAISS)
- All chunk embeddings are stored in a FAISS index on disk.
- FAISS (Facebook AI Similarity Search) performs fast nearest-neighbour search over the stored vectors.
- When a query comes in, FAISS finds the chunks whose embeddings are closest (most similar in meaning) to the query embedding.
- The Flat L2 index used here performs exact search, which is reliable for datasets up to around 100k chunks.

### Retriever
- The query engine takes a user's natural language question, embeds it, and runs a similarity search against the FAISS index.
- It returns the top-k most relevant chunks along with a similarity score. A lower score means higher similarity (L2 distance).
- Each result includes the source file, page number, file type, and the chunk content — giving full traceability.

---

## Key Principles

- **Separation of concerns** — ingestion, embedding, storage, and retrieval are each handled by a dedicated module so any part can be swapped independently.
- **Metadata is first-class** — every chunk carries its origin metadata, which is essential for building trust in retrieved results and enabling filtered search in later days.
- **Local-first** — the entire Day 1 pipeline runs offline with no external API calls. Embeddings are generated locally using HuggingFace.
- **Reproducibility** — running `ingest.py` on the same documents should always produce the same index. The chunk preview file written to `data/chunks/` lets you audit exactly what was stored.
