import os, sys, yaml, time
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

    # ── /ask ──────────────────────────────────────────────
    def ask(self, query: str):
        t0 = time.time()
        history = self.memory.format_history_for_prompt()
        self._trace("MEMORY", f"{len(self.memory.get_history())} msgs in context")

        context_str, docs = self.ctx_builder.build_context(query)
        self._trace("RETRIEVAL", f"{len(docs)} chunks retrieved")

        prompt = (
            "Use ONLY the context below to answer. If insufficient, say so.\n\n"
            f"Chat History:\n{history}\n\nContext:\n{context_str}\n\n"
            f"Question: {query}\nAnswer:"
        )
        answer = self._llm(prompt)
        self._trace("GENERATION", f"Answer generated ({len(answer)} chars)")

        ev = self.evaluator.evaluate_response(query, context_str, answer)
        self._trace("EVAL", f"Faithful={ev.get('is_faithful')} Confidence={ev.get('confidence_score')}%")

        if not ev.get("is_faithful", True):
            self._trace("REFINE", "Hallucination detected — refining...")
            answer = self._llm(
                f"Previous answer was unfaithful. Critique: {ev.get('critique')}\n\n"
                f"Context:\n{context_str}\n\nQuestion: {query}\n"
                "Provide a corrected answer using ONLY the context."
            )
            ev = self.evaluator.evaluate_response(query, context_str, answer)
            self._trace("EVAL-2", f"Faithful={ev.get('is_faithful')} Confidence={ev.get('confidence_score')}%")

        self._trace("TIME", f"{time.time()-t0:.1f}s")
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
        self.memory.add_interaction(query, answer, metadata=ev, endpoint="/ask-sql")
        return answer, sql, results, ev

    # ── /ask-image ────────────────────────────────────────
    def ask_image_text(self, query: str, top_k: int = 3):
        t0 = time.time()
        results = self.img_engine.search_by_text(query, top_k=top_k)
        formatted = self._format_image_results(results)
        context = "\n".join(r["metadata"]["caption"] for r in results)
        ev = self.evaluator.evaluate_response(query, context, formatted)
        self._trace("IMAGE-TEXT", f"{len(results)} results in {time.time()-t0:.1f}s")
        self.memory.add_interaction(query, formatted, metadata=ev, endpoint="/ask-image:text")
        return results, formatted, ev

    def ask_image_image(self, image_path: str, top_k: int = 3):
        t0 = time.time()
        results = self.img_engine.search_by_image(image_path, top_k=top_k)
        formatted = self._format_image_results(results)
        context = "\n".join(r["metadata"]["caption"] for r in results)
        ev = self.evaluator.evaluate_response(image_path, context, formatted)
        self._trace("IMAGE-IMG", f"{len(results)} results in {time.time()-t0:.1f}s")
        self.memory.add_interaction(f"[image:{image_path}]", formatted, metadata=ev, endpoint="/ask-image:image")
        return results, formatted, ev

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
            mode = input("Mode (text / image): ").strip().lower()
            if mode == "text":
                query = input("Query: ").strip()
                if not query:
                    continue
                _, formatted, ev = engine.ask_image_text(query)
                print(f"\n{SEP}\nQuery   : {query}\n{SEP}")
                print(f"Results :\n{formatted}")
                print_eval(ev)
            elif mode == "image":
                path = input("Image path: ").strip()
                if not path or not os.path.exists(path):
                    print("Invalid path.")
                    continue
                _, formatted, ev = engine.ask_image_image(path)
                print(f"\n{SEP}\nQuery   : {path}\n{SEP}")
                print(f"Results :\n{formatted}")
                print_eval(ev)
            else:
                print("Use 'text' or 'image'.")
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