import os
import sys
import yaml
import time
import tempfile
import google.genai as genai
import streamlit as st
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


def _get_engine():
    if "engine" not in st.session_state:
        st.session_state.engine = RAGEngine()
    return st.session_state.engine


def _init_state():
    if "selected_endpoint" not in st.session_state:
        st.session_state.selected_endpoint = "/ask"
    if "ui_messages" not in st.session_state:
        st.session_state.ui_messages = {
            "/ask": [],
            "/ask-sql": [],
            "/ask-image": [],
        }


def _render_messages(endpoint):
    for msg in st.session_state.ui_messages[endpoint]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sql"):
                st.caption("Generated SQL")
                st.code(msg["sql"], language="sql")
            if msg.get("results") is not None:
                if endpoint == "/ask-image":
                    _render_image_matches(msg["results"])
                else:
                    st.caption("Result preview")
                    st.write(msg["results"])
            if msg.get("eval"):
                ev = msg["eval"]
                st.caption(
                    f"Faithful: {ev.get('is_faithful', '?')} | Confidence: {ev.get('confidence_score', '?')}%"
                )


def _append_message(endpoint, role, content, sql=None, results=None, ev=None):
    st.session_state.ui_messages[endpoint].append(
        {
            "role": role,
            "content": content,
            "sql": sql,
            "results": results,
            "eval": ev,
        }
    )


def _get_image_path(meta):
    raw_path = meta.get("filepath")
    if raw_path and os.path.exists(raw_path):
        return raw_path

    filename = meta.get("filename")
    if not filename:
        return None

    fallback = os.path.join(BASE_DIR, "data", "images", filename)
    if os.path.exists(fallback):
        return fallback
    return None


def _render_image_matches(results):
    if not results:
        st.caption("No image matches found.")
        return

    st.caption("Matched images")
    for item in results:
        meta = item.get("metadata", {})
        score = round(item.get("score", 0) * 100, 1)
        image_path = _get_image_path(meta)
        caption = f"{meta.get('filename', 'unknown')} | score: {score}% | {meta.get('caption', '')}"
        if image_path:
            st.image(image_path, caption=caption, use_container_width=True)
        else:
            st.write(caption)
            st.caption("Image file not found on disk.")


def _submit_ask(engine, query):
    _append_message("/ask", "user", query)
    with st.chat_message("assistant"):
        with st.spinner("Generating answer..."):
            answer, ev = engine.ask(query)
        st.markdown(answer)
        st.caption(f"Faithful: {ev.get('is_faithful', '?')} | Confidence: {ev.get('confidence_score', '?')}%")
    _append_message("/ask", "assistant", answer, ev=ev)


def _submit_ask_sql(engine, query):
    _append_message("/ask-sql", "user", query)
    with st.chat_message("assistant"):
        with st.spinner("Running SQL pipeline..."):
            answer, sql, results, ev = engine.ask_sql(query)
        st.markdown(answer)
        st.caption(f"Faithful: {ev.get('is_faithful', '?')} | Confidence: {ev.get('confidence_score', '?')}%")
        st.caption("Generated SQL")
        st.code(sql, language="sql")
        st.caption("Result preview")
        st.write(results[:3] if isinstance(results, list) else results)
    _append_message("/ask-sql", "assistant", answer, sql=sql, results=results[:3] if isinstance(results, list) else results, ev=ev)


def _submit_ask_image(engine, query, top_k):
    _append_message("/ask-image", "user", query)
    with st.chat_message("assistant"):
        with st.spinner("Searching similar images..."):
            results, answer, ev = engine.ask_image(query, top_k=top_k)
        st.markdown(answer)
        st.caption(f"Faithful: {ev.get('is_faithful', '?')} | Confidence: {ev.get('confidence_score', '?')}%")
        _render_image_matches(results)
    _append_message("/ask-image", "assistant", answer, results=results, ev=ev)


def main():
    st.set_page_config(page_title="Week7 RAG Assistant", layout="wide")
    _init_state()
    engine = _get_engine()

    st.title("Week7 RAG Assistant")
    st.caption("Use Streamlit for endpoint chat. Backend traces continue in terminal logs.")

    col_left, col_right = st.columns([3, 1])

    with col_right:
        st.subheader("Controls")
        endpoint = st.radio(
            "Endpoint",
            ["/ask", "/ask-sql", "/ask-image"],
            key="selected_endpoint",
        )
        if st.button("Clear Chat UI", use_container_width=True):
            st.session_state.ui_messages[endpoint] = []
            st.rerun()
        if st.button("Clear Stored Memory", use_container_width=True):
            engine.memory.clear()
            st.success("Memory cleared.")
        st.markdown("---")
        st.subheader("Feedback")
        rating = st.slider("Rating", min_value=1, max_value=5, value=5)
        comment = st.text_area("Comment", value="")
        if st.button("Submit Feedback", use_container_width=True):
            engine.memory.log_feedback(rating, comment)
            st.success("Feedback logged.")

        st.markdown("---")
        with st.expander("Conversation History"):
            history = engine.memory.get_history()
            if not history:
                st.write("No history yet.")
            else:
                for msg in history[-20:]:
                    ts = msg.get("timestamp", "")[:19]
                    role = msg.get("role", "unknown").upper()
                    st.write(f"[{ts}] {role}: {msg.get('content', '')[:160]}")

    with col_left:
        _render_messages(endpoint)

        if endpoint in ["/ask", "/ask-sql"]:
            prompt = st.chat_input("Type your question")
            if prompt:
                try:
                    if endpoint == "/ask":
                        _submit_ask(engine, prompt)
                    else:
                        _submit_ask_sql(engine, prompt)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Request failed: {exc}")
        else:
            st.caption("Send a text query, or upload an image and submit it.")
            top_k = st.slider("Top K", min_value=1, max_value=10, value=3)
            text_prompt = st.chat_input("Type an image search question")
            if text_prompt:
                try:
                    _submit_ask_image(engine, text_prompt, top_k)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Image query failed: {exc}")

            uploaded = st.file_uploader(
                "Upload image for /ask-image",
                type=["png", "jpg", "jpeg", "webp"],
                key="image_upload",
            )
            if uploaded is not None and st.button("Submit Uploaded Image"):
                suffix = os.path.splitext(uploaded.name)[1] or ".png"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded.getbuffer())
                    temp_path = tmp.name
                try:
                    _submit_ask_image(engine, temp_path, top_k)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Uploaded image failed: {exc}")


if __name__ == "__main__":
    main()