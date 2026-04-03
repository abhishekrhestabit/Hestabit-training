import sys
import os
import asyncio
from pathlib import Path

# ── Disable Streamlit file watcher (conflicts with PyTorch) ──────────────────
os.environ.setdefault("STREAMLIT_SERVER_FILE_WATCHER_TYPE", "none")

# ── Path setup (must happen before any local imports) ────────────────────────

DAY5_ROOT = Path(__file__).resolve().parent
if str(DAY5_ROOT) not in sys.path:
    sys.path.insert(0, str(DAY5_ROOT))
os.chdir(DAY5_ROOT)  # run_nexus uses relative paths (logs/, memory/)

import streamlit as st
from nexus_ai.main import run_nexus, build_memory_tools
from memory.session_memory import MemorySystem
from config import describe_active_model


# ── Helpers ──────────────────────────────────────────────────────────────────

def run_async(coro):
    """Bridge async coroutines into Streamlit's sync world."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@st.cache_resource
def init_memory():
    """Initialize MemorySystem + tools once (expensive: loads SentenceTransformer + FAISS)."""
    mem = MemorySystem(
        db_path=str(DAY5_ROOT / "memory" / "long_term.db"),
        vector_dir=str(DAY5_ROOT / "memory" / "vector_store"),
    )
    tools = build_memory_tools(mem)
    return mem, tools


def execute_query(query: str, memory: MemorySystem, mem_tools: list) -> str:
    """Run the full NEXUS pipeline — all output goes to terminal (CLI)."""
    return run_async(run_nexus(query, memory, mem_tools))


# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="NEXUS AI", page_icon="🧠", layout="wide")

memory, mem_tools = init_memory()

if "messages" not in st.session_state:
    st.session_state.messages = []


# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🧠 NEXUS AI")
    st.caption("Plan → Execute → Critique → Validate → Report")
    st.divider()

    try:
        st.caption(f"**Model:** {describe_active_model()}")
    except Exception:
        st.caption("**Model:** not configured")

    st.subheader("Memory")
    stats = memory.stats()
    c1, c2, c3 = st.columns(3)
    c1.metric("Session", stats["session_entries"])
    c2.metric("Vector", stats["vector_entries"])
    c3.metric("Facts", stats["long_term_facts"])

    if st.button("🗑️ Clear Memory", use_container_width=True):
        run_async(memory.clear())
        st.toast("Memory cleared!")
        st.rerun()

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption("Workers: researcher · analyst · coder")
    st.caption("All agent activity streams to the terminal")


# ── Main area ────────────────────────────────────────────────────────────────

st.title("NEXUS AI")
st.caption("Multi-agent orchestration — ask anything")

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ── Chat input & execution ───────────────────────────────────────────────────

if query := st.chat_input("Ask NEXUS anything..."):
    # Display user message
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # Process with NEXUS — all agent output prints to the terminal
    with st.chat_message("assistant"):
        with st.spinner("NEXUS is working... (watch the terminal for live agent activity)"):
            run_async(memory.store_turn("user", query))
            result = execute_query(query, memory, mem_tools)
            run_async(memory.store_turn("agent", result))

        # Display only the final answer
        st.markdown(result)

    # Save to history
    st.session_state.messages.append({"role": "assistant", "content": result})

    # Refresh sidebar stats
    st.rerun()
