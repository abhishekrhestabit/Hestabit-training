import os
import sys
import yaml
import time
import shutil
import tempfile
import google.genai as genai
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.pipelines.context_builder import ContextBuilder
from src.pipelines.ingest import load_documents, split_text, save_vector_db
from src.pipelines.sql_pipeline import SQLQAPipeline
from src.retriever.image_search import ImageSearchEngine
from src.memory.memory_store import MemoryStore
from src.evaluation.rag_eval import RAGEvaluator

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "model.yaml")
LOGS_PATH = os.path.join(BASE_DIR, "CHAT-LOGS.json")
RAW_DATA_PATH = "/home/abhishekrai/Training/week7/src/data/raw"


class RAGEngine:
    def __init__(self):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        self._client = genai.Client(api_key=os.environ.get(cfg["api_key_env"], ""))
        self._model = cfg["model_name"]
        self.memory = MemoryStore(filepath=LOGS_PATH)
        self.evaluator = RAGEvaluator(config_path=CONFIG_PATH)
        self._ctx_builder = self._sql_pipeline = self._img_engine = None
        # Custom CSV pipeline state
        self._custom_sql_pipeline = None
        self._custom_csv_name = None
        self._custom_csv_tmpdir = None

    # ── Lazy-loaded pipelines ─────────────────────────────
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

    # ── Custom CSV pipeline ───────────────────────────────
    def load_csv_as_pipeline(self, uploaded_file) -> str:
        """Save an uploaded CSV to a temp dir and build a fresh SQLQAPipeline from it."""
        # Clean up any previous temp dir
        if self._custom_csv_tmpdir and os.path.exists(self._custom_csv_tmpdir):
            shutil.rmtree(self._custom_csv_tmpdir, ignore_errors=True)

        tmpdir = tempfile.mkdtemp()
        csv_path = os.path.join(tmpdir, uploaded_file.name)
        with open(csv_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        print(f"[CSV] Loading '{uploaded_file.name}' into custom pipeline...")
        self._custom_sql_pipeline = SQLQAPipeline(csv_dir=tmpdir, config_path=CONFIG_PATH)
        self._custom_csv_name = uploaded_file.name
        self._custom_csv_tmpdir = tmpdir
        return uploaded_file.name

    def reset_custom_pipeline(self):
        """Discard the custom CSV pipeline and return to the default DB."""
        if self._custom_csv_tmpdir and os.path.exists(self._custom_csv_tmpdir):
            shutil.rmtree(self._custom_csv_tmpdir, ignore_errors=True)
        self._custom_sql_pipeline = None
        self._custom_csv_name = None
        self._custom_csv_tmpdir = None

    # ── Document ingestion for /ask ──────────────────────
    def ingest_document(self, uploaded_file) -> str:
        """Save uploaded file to raw data dir, re-run ingest, reload ContextBuilder."""
        os.makedirs(RAW_DATA_PATH, exist_ok=True)
        dest = os.path.join(RAW_DATA_PATH, uploaded_file.name)
        with open(dest, "wb") as f:
            f.write(uploaded_file.getbuffer())
        print(f"[INGEST] Saved '{uploaded_file.name}' to {RAW_DATA_PATH}")

        print("[INGEST] Running ingestion pipeline...")
        docs = load_documents()
        if not docs:
            raise RuntimeError("No documents found after upload — ingestion aborted.")
        chunks = split_text(docs)
        save_vector_db(chunks)

        # Force ContextBuilder to reload with the fresh FAISS index
        self._ctx_builder = None
        print("[INGEST] ContextBuilder reset — next query will use updated vectorstore.")
        return uploaded_file.name

    # ── Core helpers ──────────────────────────────────────
    def _llm(self, prompt: str) -> str:
        return self._client.models.generate_content(model=self._model, contents=prompt).text.strip()

    def _trace(self, tag, msg):
        print(f"  [{tag}] {msg}")

    def _reformulate_query(self, query: str, history: str) -> str:
        if not history or history == "No previous conversation.":
            return query
        prompt = f"""Rewrite the query as a standalone question using the chat history.
Replace pronouns (it, that, them, this) with the actual subject from history.
If already standalone, return the original query exactly.
Return ONLY the rewritten query.

Chat History:
{history}

New Query: {query}
Rewritten Query:"""
        return self._llm(prompt)

    # ── /ask ──────────────────────────────────────────────
    def ask(self, query: str):
        t0 = time.time()
        history = self.memory.format_history_for_prompt(chat_pairs=5)
        standalone_query = self._reformulate_query(query, history)
        self._trace("REWRITE", f"'{query}' → '{standalone_query}'" if standalone_query.lower() != query.lower() else "No rewrite needed")

        context_str, docs, top_score = self.ctx_builder.build_context(standalone_query)
        self._trace("RETRIEVAL", f"{len(docs)} chunks retrieved for '{standalone_query}' (best score: {round(top_score, 4) if docs else 'n/a'})")

        # Context is empty if: no docs returned, OR all chunks scored below the
        # reranker's relevance threshold (top_score == -inf signals this).
        import math
        context_is_empty = not docs or math.isinf(top_score)

        if context_is_empty:
            prompt = f"""You are an intelligent assistant. The document database returned no results for this query.

--- CHAT HISTORY ---
{history}

--- USER QUESTION ---
{query}

The database has no information on this topic. Answer using your general knowledge and explicitly start your response with:
"My document database has no information on this, but based on my general knowledge: "
"""
        else:
            prompt = f"""You are an intelligent assistant. You have been given retrieved document chunks that are relevant to the user's question.

--- CHAT HISTORY ---
{history}

--- RETRIEVED DOCUMENT CONTEXT ---
{context_str}

--- USER QUESTION ---
{query} (Interpreted as: {standalone_query})

INSTRUCTIONS:
1. Your PRIMARY source is the RETRIEVED DOCUMENT CONTEXT above. It contains real chunks from the user's documents.
2. Extract and present the specific facts, figures, and details from those chunks that answer the question.
3. If the chunks contain partial information, present what IS there and note what is missing.
4. DO NOT say the database has no information — chunks were retrieved. Use them.
5. Cite the source and page when referencing a chunk (e.g. "According to [source], page X...").
6. Only supplement with general knowledge if the chunks are genuinely silent on a specific sub-point, and clearly label it as such.
"""
        answer = self._llm(prompt)
        self._trace("GENERATION", f"Answer generated ({len(answer)} chars)")

        eval_context = f"Chat History:\n{history}\n\nDatabase Context:\n{context_str}"
        ev = self.evaluator.evaluate_response(standalone_query, eval_context, answer)
        self._trace("EVAL", f"Faithful={ev.get('is_faithful')} Confidence={ev.get('confidence_score')}%")

        # Only refine if: context existed, evaluator flagged unfaithful, AND the answer
        # didn't legitimately use the context (i.e. it hallucinated or ignored chunks).
        if not context_is_empty and not ev.get("is_faithful", True):
            self._trace("REFINE", "Answer ignored retrieved chunks — forcing grounded retry...")
            answer = self._llm(
                f"Your previous answer ignored the retrieved document chunks. Critique: {ev.get('critique')}\n\n"
                f"Chat History:\n{history}\n\n"
                f"Retrieved Document Context:\n{context_str}\n\n"
                f"Question: {standalone_query}\n\n"
                "You MUST answer using the document context above. Quote or paraphrase specific facts from the chunks. "
                "Do not say the database is empty — it is not. Provide the corrected final answer."
            )
            ev = self.evaluator.evaluate_response(standalone_query, eval_context, answer)
            self._trace("EVAL-2", f"Faithful={ev.get('is_faithful')} Confidence={ev.get('confidence_score')}%")

        self._trace("TIME", f"{time.time()-t0:.1f}s")
        self.memory.add_interaction(query, answer, metadata=ev, endpoint="/ask")
        return answer, ev

    # ── /ask-sql ──────────────────────────────────────────
    def ask_sql(self, query: str):
        t0 = time.time()
        # Route to custom pipeline if one has been loaded, otherwise use default
        pipeline = self._custom_sql_pipeline if self._custom_sql_pipeline else self.sql_pipeline
        source = f"custom ({self._custom_csv_name})" if self._custom_sql_pipeline else "default"
        self._trace("SQL-SOURCE", f"Using {source} pipeline")

        history = self.memory.format_history_for_prompt()
        contextualized = f"Previous Chat:\n{history}\n\nNew Question: {query}"

        answer, sql, results = pipeline.run(contextualized, display_query=query)
        context_used = str(results[:20])
        self._trace("SQL", "Query executed and summarized")

        ev = self.evaluator.evaluate_response(query, context_used, answer)
        self._trace("EVAL", f"Faithful={ev.get('is_faithful')} Confidence={ev.get('confidence_score')}%")

        if not ev.get("is_faithful", True):
            self._trace("REFINE", "Hallucination detected — re-running strict...")
            answer, sql, results = pipeline.run(
                contextualized + "\nCRITICAL: Answer strictly from database. No hallucination.",
                display_query=query
            )
            ev = self.evaluator.evaluate_response(query, context_used, answer)
            self._trace("EVAL-2", f"Faithful={ev.get('is_faithful')} Confidence={ev.get('confidence_score')}%")

        self._trace("TIME", f"{time.time()-t0:.1f}s")
        self.memory.add_interaction(query, answer, metadata=ev, endpoint="/ask-sql")
        return answer, sql, results, ev

    # ── /ask-image ────────────────────────────────────────
    def ask_image(self, query: str, top_k: int = 3, user_query: str = None):
        t0 = time.time()
        is_image = os.path.isfile(query)
        history = self.memory.format_history_for_prompt(chat_pairs=5)

        if is_image:
            query_info = self.img_engine.extract_caption_ocr(query)
            results = self.img_engine.search_by_image(query, top_k=top_k)
            normalized_user_query = (user_query or "").strip()
            standalone_query = self._reformulate_query(normalized_user_query, history) if normalized_user_query else query_info["caption"]
            context_lines = []
            if normalized_user_query:
                context_lines += [f"User question: {normalized_user_query}", f"Interpreted question: {standalone_query}"]
            context_lines.append(f"Given image caption: {query_info['caption']}")
            if query_info["ocr"]:
                context_lines.append(f"Given image text/OCR: {query_info['ocr']}")
            query_context = "\n".join(context_lines)
        else:
            results = self.img_engine.search_by_text(query, top_k=top_k)
            standalone_query = self._reformulate_query(query, history)
            query_context = f"User query: {query}\nInterpreted query using history: {standalone_query}\n"

        retrieved_images_text = "\n".join(
            f"- filename: {r['metadata']['filename']}, similarity_score: {float(r.get('score', 0)):.4f}, "
            f"caption: {r['metadata'].get('caption', '')}"
            + (f", ocr: {r['metadata'].get('ocr', '')}" if r['metadata'].get('ocr') else "")
            for r in results
        )

        prompt = f"""You are an expert visual assistant with broad knowledge across all domains — nature, objects, people, places, art, technology, food, and more.

--- CHAT HISTORY ---
{history}

--- USER + IMAGE CONTEXT ---
{query_context}

--- RETRIEVED IMAGES ---
{retrieved_images_text}

TASK: Answer the user's query: "{standalone_query}"

RULES:
1. Identify the subject from the caption, OCR, and retrieved metadata. It could be anything — an animal, a product, a landmark, a person, a document, a scene, etc.
2. Use the retrieved metadata as your anchor, then EXPAND using your own expert knowledge about that subject.
3. Shape your response to match exactly what the user asked:
   - Detailed question → thorough explanation with relevant facts, context, and characteristics
   - Summary request → concise overview
   - Comparison → compare the retrieved items meaningfully on relevant dimensions
   - Identification → name/classify the subject and explain what it is
   - Any other intent → respond naturally in the way that best fits the question
4. Be conversational and informative — not robotic or templated.
5. Vary your structure freely (paragraphs, bullets, short or long) to best fit the query.
6. Only say "I don't have enough information" if the subject is truly unidentifiable from all available evidence.

Write your response now, then end with exactly this line on its own:
Here are some similar images:
"""
        answer = self._llm(prompt)

        context = f"Query: {standalone_query}\nSimilar: {', '.join(r['metadata']['filename'] + ': ' + r['metadata']['caption'] for r in results)}"
        ev = self.evaluator.evaluate_response(standalone_query, context, answer)

        self._trace(f"IMAGE-{'IMAGE' if is_image else 'TEXT'}", f"{len(results)} results in {time.time()-t0:.1f}s")
        self.memory.add_interaction(standalone_query, answer, metadata=ev, endpoint="/ask-image")
        return results, answer, ev


# ── Streamlit helpers ─────────────────────────────────────

def _get_engine():
    if "engine" not in st.session_state:
        st.session_state.engine = RAGEngine()
    return st.session_state.engine


def _format_eval_caption(ev: dict) -> str:
    return f"Faithful: {ev.get('is_faithful', '?')} | Confidence: {ev.get('confidence_score', '?')}%"


def _init_state():
    st.session_state.setdefault("selected_endpoint", "/ask")
    st.session_state.setdefault("ui_messages", {"/ask": [], "/ask-sql": [], "/ask-image": []})
    st.session_state.setdefault("csv_uploader_key", 0)


def _render_messages(endpoint):
    for msg in st.session_state.ui_messages[endpoint]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sql"):
                with st.expander("Generated SQL"):
                    st.code(msg["sql"], language="sql")
            if msg.get("results") is not None:
                if endpoint == "/ask-image":
                    _render_image_matches(msg["results"])
                else:
                    with st.expander("Result preview"):
                        st.write(msg["results"])
            if msg.get("eval"):
                st.caption(_format_eval_caption(msg["eval"]))


def _append_message(endpoint, role, content, sql=None, results=None, ev=None):
    st.session_state.ui_messages[endpoint].append(
        {"role": role, "content": content, "sql": sql, "results": results, "eval": ev}
    )


def _get_image_path(meta):
    raw_path = meta.get("filepath")
    if raw_path and os.path.exists(raw_path):
        return raw_path
    filename = meta.get("filename")
    fallback = os.path.join(BASE_DIR, "data", "images", filename) if filename else None
    return fallback if fallback and os.path.exists(fallback) else None


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
        st.caption(_format_eval_caption(ev))
    _append_message("/ask", "assistant", answer, ev=ev)


def _submit_ask_sql(engine, query):
    _append_message("/ask-sql", "user", query)
    with st.chat_message("assistant"):
        with st.spinner("Running SQL pipeline..."):
            answer, sql, results, ev = engine.ask_sql(query)
        st.markdown(answer)
        st.caption(_format_eval_caption(ev))
        with st.expander("Generated SQL"):
            st.code(sql, language="sql")
        with st.expander("Result preview"):
            st.write(results[:3] if isinstance(results, list) else results)
    _append_message("/ask-sql", "assistant", answer, sql=sql,
                    results=results[:3] if isinstance(results, list) else results, ev=ev)


def _submit_ask_image(engine, query, top_k, user_query=None):
    _append_message("/ask-image", "user", (user_query or query).strip())
    with st.chat_message("assistant"):
        with st.spinner("Searching similar images..."):
            results, answer, ev = engine.ask_image(query, top_k=top_k, user_query=user_query)
        st.markdown(answer)
        st.caption(_format_eval_caption(ev))
        _render_image_matches(results)
    _append_message("/ask-image", "assistant", answer, results=results, ev=ev)


def _render_csv_uploader(engine):
    """Compact CSV uploader rendered just above the chat input in col_left."""
    up_col, status_col = st.columns([3, 2])
    with up_col:
        csv_file = st.file_uploader(
            "Upload CSV",
            type=["csv"],
            key=f"csv_upload_{st.session_state.csv_uploader_key}",
            label_visibility="collapsed",
            help="Upload any CSV — a fresh in-memory SQLite DB is built from it immediately.",
        )
    with status_col:
        if engine._custom_csv_name:
            st.success(f"**{engine._custom_csv_name}**")
            if st.button("↩ Reset to default DB", use_container_width=True):
                engine.reset_custom_pipeline()
                st.session_state.csv_uploader_key += 1
                st.rerun()
        else:
            st.caption("Using default DB")

    if csv_file is not None and csv_file.name != engine._custom_csv_name:
        with st.spinner(f"Loading '{csv_file.name}' into database..."):
            try:
                engine.load_csv_as_pipeline(csv_file)
                st.rerun()
            except Exception as e:
                st.error(f"Failed to load CSV: {e}")


def _render_doc_uploader(engine):
    """Compact document uploader rendered just above the /ask chat input."""
    up_col, status_col = st.columns([3, 2])
    with up_col:
        doc_file = st.file_uploader(
            "Upload document",
            type=["pdf", "txt", "docx", "csv"],
            key=f"doc_upload_{st.session_state.get('doc_uploader_key', 0)}",
            label_visibility="collapsed",
            help="Upload a PDF, TXT, DOCX, or CSV — it will be ingested and the vectorstore updated.",
        )
    with status_col:
        last = st.session_state.get("last_ingested_doc")
        if last:
            st.success(f"**{last}** ingested")
        else:
            st.caption("No new doc uploaded")

    if doc_file is not None and doc_file.name != st.session_state.get("last_ingested_doc"):
        with st.spinner(f"Ingesting '{doc_file.name}' and rebuilding vectorstore..."):
            try:
                engine.ingest_document(doc_file)
                st.session_state["last_ingested_doc"] = doc_file.name
                st.session_state["doc_uploader_key"] = st.session_state.get("doc_uploader_key", 0) + 1
                st.rerun()
            except Exception as e:
                st.error(f"Ingestion failed: {e}")


def main():
    st.set_page_config(page_title="Week7 RAG Assistant", layout="wide")
    _init_state()
    engine = _get_engine()

    st.title("Week7 RAG Assistant")
    st.caption("Use Streamlit for endpoint chat. Backend traces continue in terminal logs.")

    col_left, col_right = st.columns([3, 1])

    with col_right:
        st.subheader("Controls")
        endpoint = st.radio("Endpoint", ["/ask", "/ask-sql", "/ask-image"], key="selected_endpoint")
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
                    st.write(f"[{msg.get('timestamp', '')[:19]}] {msg.get('role', 'unknown').upper()}: {msg.get('content', '')[:160]}")



    with col_left:
        _render_messages(endpoint)

        if endpoint in ["/ask", "/ask-sql"]:
            if endpoint == "/ask-sql":
                _render_csv_uploader(engine)
            elif endpoint == "/ask":
                _render_doc_uploader(engine)
            prompt = st.chat_input("Type your question")
            if prompt:
                try:
                    (_submit_ask if endpoint == "/ask" else _submit_ask_sql)(engine, prompt)
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

            uploaded = st.file_uploader("Upload image for /ask-image", type=["png", "jpg", "jpeg", "webp"], key="image_upload")
            uploaded_question = st.text_input("Question for uploaded image", placeholder="Ask something about the uploaded image", key="uploaded_image_question")
            if uploaded is not None and st.button("Submit Uploaded Image"):
                question = uploaded_question.strip()
                if not question:
                    st.warning("Please enter a question for the uploaded image.")
                else:
                    suffix = os.path.splitext(uploaded.name)[1] or ".png"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(uploaded.getbuffer())
                        temp_path = tmp.name
                    try:
                        _submit_ask_image(engine, temp_path, top_k, user_query=question)
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Uploaded image failed: {exc}")


if __name__ == "__main__":
    main()