from __future__ import annotations
from typing import List

from autogen_core.memory import Memory, MemoryContent, MemoryMimeType, MemoryQueryResult
from autogen_core.models import UserMessage

from memory.vector_store import VectorStore, LongTermStore

class SessionMemory(Memory):
    def __init__(self, max_entries: int = 20) -> None:
        self._entries: List[MemoryContent] = []
        self.max_entries = max_entries

    async def add(self, content: MemoryContent, **_) -> None:
        self._entries.append(content)
        if len(self._entries) > self.max_entries:
            self._entries.pop(0)  # drop oldest

    async def query(self, query: MemoryContent, **_) -> MemoryQueryResult:
        return MemoryQueryResult(results=list(self._entries))

    async def update_context(self, model_context) -> None:
        if not self._entries:
            return
        lines = "\n".join(f"{i+1}. {e.content}" for i, e in enumerate(self._entries))
        await model_context.add_message(
            UserMessage(content=f"Session memory:\n{lines}", source="memory")
        )

    async def clear(self) -> None: self._entries.clear()
    async def close(self) -> None: self._entries.clear()
    def __len__(self) -> int: return len(self._entries)


class FactMemory(Memory):
    """Bridges FAISS and SQLite to AutoGen's Memory Protocol."""
    def __init__(self, vector_store: VectorStore, long_term_store: LongTermStore):
        self.vector = vector_store
        self.long_term = long_term_store

    async def add(self, content: MemoryContent, **_) -> None:
        # Save fact to both vector store and sqlite fallback
        category = (content.metadata or {}).get("category", "general")
        self.vector.add(content.content, metadata=content.metadata)
        self.long_term.save(content.content, category=category, metadata=content.metadata)

    async def query(self, query: MemoryContent, **_) -> MemoryQueryResult:
        seen, results = set(), []
        max_results = 5

        for hit in self.vector.search(query.content):  # semantic search (scored, threshold-filtered)
            if hit["text"] not in seen:
                results.append(MemoryContent(content=hit["text"], mime_type=MemoryMimeType.TEXT))
                seen.add(hit["text"])
            if len(results) >= max_results:
                break

        # Only fall back to keyword search if semantic search found nothing
        if not results:
            for fact in self.long_term.search(query.content, top_k=max_results):
                if fact not in seen:
                    results.append(MemoryContent(content=fact, mime_type=MemoryMimeType.TEXT))
                    seen.add(fact)
                if len(results) >= max_results:
                    break

        return MemoryQueryResult(results=results)

    async def update_context(self, model_context) -> None:
        messages = await model_context.get_messages()
        if not messages: return
        last_msg = messages[-1].content
        query_text = last_msg if isinstance(last_msg, str) else str(last_msg)

        res = await self.query(MemoryContent(content=query_text, mime_type=MemoryMimeType.TEXT))
        if res.results:
            facts = "\n".join(f"- {r.content}" for r in res.results)
            await model_context.add_message(UserMessage(content=f"Relevant long-term facts:\n{facts}", source="memory"))
        else:
            await model_context.add_message(UserMessage(content="No relevant memories found for this query.", source="memory"))

    async def clear(self) -> None:
        self.vector.clear()
        self.long_term.clear()
        
    async def close(self) -> None: pass


class MemorySystem:
    def __init__(
        self,
        db_path:       str = "memory/long_term.db",
        vector_dir:    str = "memory/vector_store",
        session_limit: int = 20,
        vector_top_k:  int = 5,
    ) -> None:
        self.session     = SessionMemory(max_entries=session_limit)
        self.vector      = VectorStore(store_dir=vector_dir, top_k=vector_top_k)
        self.long_term   = LongTermStore(db_path=db_path)
        self.fact_memory = FactMemory(self.vector, self.long_term)  # The new memory wrapper

    async def store_turn(self, role: str, text: str) -> None:
        # Only populate session memory with general conversation turns
        await self.session.add(MemoryContent(content=f"[{role}] {text}", mime_type=MemoryMimeType.TEXT))

    async def store_fact(self, fact: str, category: str = "general", metadata: dict | None = None) -> None:
        # Triggered by agent tool to save explicitly requested facts
        meta = metadata or {}
        meta["category"] = category
        await self.fact_memory.add(MemoryContent(content=fact, mime_type=MemoryMimeType.TEXT, metadata=meta))

    async def clear(self) -> None:
        await self.session.clear()
        await self.fact_memory.clear()

    def stats(self) -> dict:
        return {
            "session_entries": len(self.session),
            "vector_entries":  self.vector.size,
            "long_term_facts": len(self.long_term.all_facts()),
        }
