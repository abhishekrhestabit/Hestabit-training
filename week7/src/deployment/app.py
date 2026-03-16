import os
import sys
import yaml
import time
import google.genai as genai
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.pipelines.context_builder import ContextBuilder
from src.pipelines.sql_pipeline import SQLQAPipeline
from src.retriever.image_search import ImageSearchEngine
from src.memory.memory_store import MemoryStore
from src.evaluation.rag_eval import RAGEvaluator

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "model.yaml")
LOGS_PATH = os.path.join(BASE_DIR, "CHAT-LOGS.json")


class RAGEngine:
    def __init__(self):
        cfg = yaml.safe_load(open(CONFIG_PATH))
        api_key = os.environ.get(cfg["api_key_env"], "")
        self._client = genai.Client(api_key=api_key)
        self._model = cfg["model_name"]
        self.memory = MemoryStore(filepath=LOGS_PATH)
        self.evaluator = RAGEvaluator(config_path=CONFIG_PATH)
        self._ctx_builder = None
        self._sql_pipeline = None
        self._img_engine = None

    @property
    def ctx_builder(self):
        if not self._ctx_builder:
            print("[INIT] Loading text retrieval pipeline...")
            self._ctx_builder = ContextBuilder()
        return self._ctx_builder

    @property
    def sql_pipeline(self):
        if not self._sql_pipeline:
            print("[INIT] Loading SQL pipeline...")
            self._sql_pipeline = SQLQAPipeline(config_path=CONFIG_PATH)
        return self._sql_pipeline

    @property
    def img_engine(self):
        if not self._img_engine:
            print("[INIT] Loading image search engine...")
            self._img_engine = ImageSearchEngine()
        return self._img_engine

    def _llm(self, prompt: str) -> str:
        return self._client.models.generate_content(model=self._model, contents=prompt).text.strip()

    def _trace(self, tag, msg):
        print(f"  [{tag}] {msg}")

    def _reformulate_query(self, query: str, history: str) -> str:
        """Rewrites pronoun-heavy queries into standalone questions using chat history."""
        if not history or history == "No previous conversation.":
            return query
            
        prompt = f"""Given the chat history and the new user query, rewrite the query to be a standalone question. 
Replace pronouns (it, that, them, this animal) with the actual subject from the history.
If the query is already standalone, just return the exact original query.
Return ONLY the rewritten query. No explanations.

Chat History:
{history}

New Query: {query}
Rewritten Query:"""
        
        return self._llm(prompt)

    # ── /ask ──────────────────────────────────────────────
    def ask(self, query: str):
        t0 = time.time()
        history_pairs = 5
        history = self.memory.format_history_for_prompt(chat_pairs=history_pairs)
        self._trace("MEMORY", "Loaded recent chat history")

        # 1. REFORMULATE THE QUERY
        standalone_query = self._reformulate_query(query, history)
        if standalone_query.lower() != query.lower():
            self._trace("REWRITE", f"'{query}' → '{standalone_query}'")
        else:
            self._trace("REWRITE", "No rewrite needed")

        # 2. SEARCH USING THE STANDALONE QUERY
        context_str, docs = self.ctx_builder.build_context(standalone_query)
        self._trace("RETRIEVAL", f"{len(docs)} chunks retrieved for '{standalone_query}'")

        # 3. GENERATE THE ANSWER (WITH FALLBACK)
        prompt = f"""You are an intelligent assistant. You have access to the recent CHAT HISTORY and a retrieved DATABASE CONTEXT.

--- CHAT HISTORY ---
{history}

--- DATABASE CONTEXT ---
{context_str}

--- USER QUESTION ---
{query} (Interpreted as: {standalone_query})

INSTRUCTIONS:
1. Identify the subject from the CHAT HISTORY (e.g., if the user says "that animal", look at the history to know they mean "cat").
2. Try to answer the question using ONLY the DATABASE CONTEXT.
3. DEBUGGING OVERRIDE: If the DATABASE CONTEXT contains zero relevant information about the subject, DO NOT just say "Insufficient." 
4. Instead, explicitly state: "I see from our history you are asking about [Subject], but my database has no information on this. However, using my general knowledge..." and provide the answer using your own capabilities.
"""
        answer = self._llm(prompt)
        self._trace("GENERATION", f"Answer generated ({len(answer)} chars)")

        eval_context = f"Chat History:\n{history}\n\nDatabase Context:\n{context_str}"
        ev = self.evaluator.evaluate_response(standalone_query, eval_context, answer)
        self._trace("EVAL", f"Faithful={ev.get('is_faithful')} Confidence={ev.get('confidence_score')}%")

        # 4. REFINEMENT (Relaxed for debugging)
        if not ev.get("is_faithful", True):
            self._trace("REFINE", "Hallucination detected — checking if it's an authorized fallback...")
            
            if "general knowledge" in answer.lower() or "my database has no information" in answer.lower():
                self._trace("REFINE", "Authorized general knowledge fallback detected. Bypassing refinement.")
            else:
                answer = self._llm(
                    f"Previous answer was unfaithful. Critique: {ev.get('critique')}\n\n"
                    f"Chat History:\n{history}\n\n"
                    f"Database Context:\n{context_str}\n\nQuestion: {standalone_query}\n"
                    "If the database lacks info, it is OK to use general knowledge AS LONG AS you explicitly warn the user with: 'Using my general knowledge...'. Provide the final answer."
                )
                ev = self.evaluator.evaluate_response(standalone_query, eval_context, answer)
                self._trace("EVAL-2", f"Faithful={ev.get('is_faithful')} Confidence={ev.get('confidence_score')}%")

        self._trace("TIME", f"{time.time()-t0:.1f}s")
        # FIX: Directly use 'answer' instead of letting the evaluator overwrite it.
        self.memory.add_interaction(query, answer, metadata=ev, endpoint="/ask")
        return answer, ev

    # ── /ask-sql ──────────────────────────────────────────
    def ask_sql(self, query: str):
        t0 = time.time()
        history = self.memory.format_history_for_prompt()
        contextualized = f"Previous Chat:\n{history}\n\nNew Question: {query}"

        answer, sql, results = self.sql_pipeline.run(contextualized, display_query=query)
        context_used = str(results[:20])
        self._trace("SQL", "Query executed and summarized")

        ev = self.evaluator.evaluate_response(query, context_used, answer)
        self._trace("EVAL", f"Faithful={ev.get('is_faithful')} Confidence={ev.get('confidence_score')}%")

        if not ev.get("is_faithful", True):
            self._trace("REFINE", "Hallucination detected — re-running strict...")
            strict = contextualized + "\nCRITICAL: Answer strictly from database. No hallucination."
            answer, sql, results = self.sql_pipeline.run(strict, display_query=query)
            ev = self.evaluator.evaluate_response(query, context_used, answer)
            self._trace("EVAL-2", f"Faithful={ev.get('is_faithful')} Confidence={ev.get('confidence_score')}%")

        self._trace("TIME", f"{time.time()-t0:.1f}s")
        # FIX: Directly use 'answer' 
        self.memory.add_interaction(query, answer, metadata=ev, endpoint="/ask-sql")
        return answer, sql, results, ev

    # ── /ask-image ────────────────────────────────────────
    def ask_image(self, query: str, top_k: int = 3):
        t0 = time.time()
        is_image = os.path.isfile(query)

        if is_image:
            query_info = self.img_engine.extract_caption_ocr(query)
            results = self.img_engine.search_by_image(query, top_k=top_k)
            query_desc = query_info["caption"]
            query_context = f"Given image caption: {query_info['caption']}\n"
            if query_info["ocr"]:
                query_context += f"Given image text/OCR: {query_info['ocr']}\n"
        else:
            results = self.img_engine.search_by_text(query, top_k=top_k)
            query_desc = query
            query_context = f"User query: {query}\n"

        similar_parts = []
        for r in results:
            m = r["metadata"]
            part = f"- {m['filename']} (caption: {m['caption']}" + (f", text: {m['ocr']}" if m.get('ocr') else "") + ")"
            similar_parts.append(part)

        retrieved_images_text = "\n".join(similar_parts)
        prompt = f"""You are a helpful, expert visual search assistant. 
Your goal is to answer the user's query and clearly explain the visually similar images we found in the database.

--- USER QUERY ---
{query_context}

--- RETRIEVED IMAGES FROM DATABASE ---
{retrieved_images_text}

--- INSTRUCTIONS ---
1. Opening: Start with a brief, natural summary directly addressing the user's query.
2. The Handoff: Smoothly transition to mentioning the similar images we retrieved.
3. The Breakdown: Describe each retrieved image concisely. Highlight why it is relevant to the query.
4. The Reference: You MUST include the exact filename for every image you mention, wrapped in parentheses at the end of its description (e.g., (diagram_v2.png)).
5. Formatting: Use bullet points when listing the similar images so it is easy for the user to scan. 
"""

        answer = self._llm(prompt)
        
        context = f"Query: {query_desc}\nSimilar: {', '.join(r['metadata']['filename'] + ': ' + r['metadata']['caption'] for r in results)}"
        
        ev = self.evaluator.evaluate_response(query, context, answer)
        mode = "image" if is_image else "text"
        
        self._trace(f"IMAGE-{mode.upper()}", f"{len(results)} results in {time.time()-t0:.1f}s")
        # FIX: Directly use 'answer'
        self.memory.add_interaction(query, answer, metadata=ev, endpoint="/ask-image")
        
        return results, answer, ev

    def _format_image_results(self, results):
        lines = []
        for i, r in enumerate(results, 1):
            m = r["metadata"]
            confidence = round(r["score"] * 100, 1)
            lines.append(
                f"  {i}. {m['filename']}\n"
                f"     Path      : {m['filepath']}\n"
                f"     Confidence: {confidence}%\n"
                f"     Caption   : {m['caption']}"
            )
        return "\n".join(lines)


# ── CLI ────────────────────────────────────────────────────
SEP = "-" * 50

def print_eval(ev):
    print(SEP)
    print(f"  Confidence : {ev.get('confidence_score', '?')}%")
    print(f"  Faithful   : {ev.get('is_faithful', '?')}")
    print(f"  Critique   : {ev.get('critique', 'N/A')}")
    print(SEP)


def main():
    print("=" * 55)
    print("  RAG CLI Engine — Day 5 Capstone")
    print("  Endpoints: /ask  /ask-image  /ask-sql  /quit /history /clear")
    print("=" * 55)

    engine = RAGEngine()

    while True:
        try:
            cmd = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not cmd:
            continue
        if cmd == "/quit":
            print("Goodbye.")
            break
        elif cmd == "/ask":
            query = input("Query: ").strip()
            if not query:
                continue
            answer, ev = engine.ask(query)
            print(f"\n{SEP}\nQuery   : {query}\n{SEP}")
            print(f"Answer  :\n{answer}")
            print_eval(ev)
        elif cmd == "/ask-sql":
            query = input("Query: ").strip()
            if not query:
                continue
            answer, sql, results, ev = engine.ask_sql(query)
            print(f"\n{SEP}\nQuery   : {query}\n{SEP}")
            print(f"SQL     :\n{sql}")
            print(f"\n{SEP}\nResults (first 3):\n{results[:3]}")
            print(f"\n{SEP}\nAnswer  :\n{answer}")
            print_eval(ev)
        elif cmd == "/ask-image":
            query = input("Query (text or image path): ").strip()
            if not query:
                continue
            _, answer, ev = engine.ask_image(query)
            print(f"\n{SEP}\nQuery   : {query}\n{SEP}")
            print(f"Answer  :\n{answer}")
            print_eval(ev)
        elif cmd == "/feedback":
            try:
                rating = int(input("Rating (1-5): ").strip())
                if rating not in range(1, 6):
                    print("Rating must be 1-5.")
                    continue
            except ValueError:
                print("Enter a number 1-5.")
                continue
            comment = input("Comment (optional): ").strip()
            engine.memory.log_feedback(rating, comment)
            print("Feedback logged.")
        elif cmd == "/history":
            history = engine.memory.get_history()
            if not history:
                print("  No history yet.")
            else:
                print(f"\n{SEP}")
                for m in history:
                    role = m['role'].upper()
                    ts = m.get('timestamp', '')[:19]
                    print(f"  [{ts}] {role}:\n  {m['content'][:200]}\n")
                print(SEP)
        elif cmd == "/clear":
            engine.memory.clear()
            print("Memory cleared.")
        else:
            print("Commands: /ask  /ask-image  /ask-sql  /feedback  /history  /clear  /quit")


if __name__ == "__main__":
    main()