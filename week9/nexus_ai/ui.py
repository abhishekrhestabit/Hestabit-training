"""
nexus_ai/ui.py  —  NEXUS AI Streamlit Chat UI
Run from week9/:  streamlit run nexus_ai/ui.py
"""

import asyncio, sys, time, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from nexus_ai.config       import get_model_client, get_runtime_model, get_runtime_provider
from nexus_ai.orchestrator import NexusOrchestrator


st.set_page_config(
    page_title="NEXUS AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* Sidebar */
[data-testid="stSidebar"] { background-color: #0f1117; }
[data-testid="stSidebar"] * { color: #e0e0e0 !important; }

/* User message bubble */
.user-bubble {
    background: #2d2d44;
    border-radius: 18px 18px 4px 18px;
    padding: 12px 16px;
    margin: 4px 0 4px 80px;
    color: #f0f0f0;
    font-size: 15px;
}

/* Meta bar under NEXUS response */
.meta-bar {
    font-size: 11px;
    color: #555;
    margin-top: 8px;
    padding-top: 6px;
    border-top: 1px solid #222;
}
.agent-tag {
    display: inline-block;
    background: #0d2137;
    color: #4a9eff;
    border-radius: 8px;
    padding: 1px 7px;
    font-size: 11px;
    margin: 1px;
    font-weight: 600;
}
.agent-tag.fix    { background: #1a2200; color: #aaff44; }
.agent-tag.memory { background: #1a0033; color: #cc88ff; }
.score-pass { color: #44ff88; font-weight: bold; }
.score-fail { color: #ff6b6b; font-weight: bold; }

/* Nexus response container */
.nexus-response {
    background: #1a2744;
    border-radius: 0 18px 18px 18px;
    padding: 16px 20px 10px 20px;
    margin: 4px 80px 4px 0;
    border-left: 3px solid #4a9eff;
}
.nexus-response.flagged {
    border-left: 3px solid #ff6b6b;
    background: #2a1a1a;
}

[data-testid="stChatMessage"] {
    background: transparent !important;
    padding: 0 !important;
}

.agent-step {
    background: #0d1117;
    border-left: 2px solid #333;
    padding: 4px 10px;
    margin: 2px 0;
    font-size: 12px;
    color: #aaa;
    font-family: monospace;
    border-radius: 0 4px 4px 0;
}

.main .block-container { max-width: 900px; padding-top: 1rem; }

/* Removed 'header' from hidden visibility to restore Streamlit's native sidebar toggle */
#MainMenu, footer { visibility: hidden; }
/* Make header transparent so the area still looks clean */
[data-testid="stHeader"] { background: transparent !important; }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────
for k, v in {
    "messages": [], "orchestrator": None,
    "last_trace": [], "mem_stats": {"session": 0, "vectors": 0, "facts": 0},
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


def get_nexus():
    if st.session_state.orchestrator is None:
        with st.spinner("Initialising NEXUS AI..."):
            st.session_state.orchestrator = NexusOrchestrator(get_model_client())
            _refresh_mem_stats()
    return st.session_state.orchestrator


def _refresh_mem_stats():
    n = st.session_state.orchestrator
    if n and n.session:
        st.session_state.mem_stats = {
            "session": n.session.turn_count,
            "vectors": n.vector.count if n.vector else 0,
            "facts":   n.ltm.count    if n.ltm    else 0,
        }


def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except Exception:
        return asyncio.run(coro)


def _tag(agent):
    css = "fix" if "(fix)" in agent or "post-fix" in agent else \
          "memory" if agent == "Memory" else ""
    return f'<span class="agent-tag {css}">{agent}</span>'


def _meta_bar(agents_used, score, duration, saved, approved):
    tags      = "".join(_tag(a) for a in agents_used)
    score_css = "score-pass" if str(score).isdigit() and int(score) >= 7 else "score-fail"
    flag      = "✅" if approved else "⚠️"
    saved_str = "&nbsp;|&nbsp;💾 Saved" if saved else ""
    return (
        f'<div class="meta-bar">{tags}'
        f'&nbsp;|&nbsp;<span class="{score_css}">{flag} {score}/10</span>'
        f'&nbsp;|&nbsp;{duration}s{saved_str}</div>'
    )


def _render_message(msg):
    """Render a single chat message — user or assistant."""
    if msg["role"] == "user":
        st.markdown(
            f'<div class="user-bubble">👤 &nbsp;{msg["content"]}</div>',
            unsafe_allow_html=True,
        )
    else:
        approved    = msg.get("approved", True)
        agents_used = msg.get("agents_used", [])
        bubble_cls  = "nexus-response" + ("" if approved else " flagged")

        # Generate the meta bar 
        meta_html = _meta_bar(
            agents_used, 
            msg.get("score","?"),
            msg.get("duration","?"), 
            msg.get("saved", False), 
            approved
        )
        
        # Wrapping in a single st.markdown call with empty lines ensures
        # Streamlit continues to render nested markdown (code blocks, tables, etc.)
        full_content = f"""<div class="{bubble_cls}">

{msg['content']}

{meta_html}
</div>"""
        
        st.markdown(full_content, unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 NEXUS AI")
    st.markdown("*Autonomous Multi-Agent System*")
    st.divider()

    model_label = get_runtime_model()
    st.markdown(f"**Provider:** `{get_runtime_provider().upper()}`")
    st.markdown(f"**Model:** `{model_label}`")
    st.divider()

    st.markdown("### 🧠 Memory")
    ms = st.session_state.mem_stats
    c1, c2, c3 = st.columns(3)
    c1.metric("Session", ms["session"])
    c2.metric("Vectors", ms["vectors"])
    c3.metric("Facts",   ms["facts"])

    if st.button("🗑️ Clear memory", use_container_width=True):
        n = st.session_state.orchestrator
        if n:
            if n.session: n.session.clear()
            if n.vector:  n.vector.clear()
            if n.ltm:     n.ltm.clear()
            _refresh_mem_stats()
            st.success("Memory cleared.")

    n = st.session_state.orchestrator
    if n and n.ltm and n.ltm.count > 0:
        with st.expander(f"📋 Stored facts ({n.ltm.count})", expanded=False):
            for f in n.ltm.get_recent(n=10):
                st.caption(f"• {f['fact'][:80]}")
    st.divider()

    st.markdown("### ⚙️ Options")
    uploaded_file = st.file_uploader(
        "Attach file", type=["csv","txt","md","json","py","db","yaml"],
        help="Passed to Researcher and Analyst"
    )
    save_report = st.checkbox("💾 Auto-save report", value=False)
    st.divider()

    st.markdown("### 💬 Conversation")
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.messages   = []
        st.session_state.last_trace = []
        st.rerun()

    if st.session_state.last_trace:
        with st.expander(f"🔍 Trace ({len(st.session_state.last_trace)} steps)"):
            for step in st.session_state.last_trace:
                a = step["agent"]
                o = str(step.get("output",""))
                st.markdown(f"**[{a}]**")
                st.code(o[:400] + ("..." if len(o)>400 else ""), language=None)

    st.divider()
    st.caption("NEXUS AI — Week 9 Capstone")


# ── Main ──────────────────────────────────────────────────────────
st.markdown("# 🤖 NEXUS AI")
st.markdown("*Planner · Researcher · Coder · Analyst · Critic · Optimizer · Validator · Reporter*")
st.divider()

# Render chat history
for msg in st.session_state.messages:
    _render_message(msg)

# ── Input ─────────────────────────────────────────────────────────
st.divider()
user_input = st.chat_input("Ask NEXUS AI anything...")

if user_input:
    nexus = get_nexus()

    # File handling
    file_path = None
    if uploaded_file:
        from nexus_ai.config import OUTPUT_DIR
        tmp = OUTPUT_DIR / uploaded_file.name
        tmp.write_bytes(uploaded_file.getvalue())
        file_path = str(tmp)
    if not file_path:
        KNOWN_EXTS = {"csv","txt","md","json","db","py","yaml","yml","log","html"}
        m = re.search(r'(?:(?:[\w\-]+/)*)[\w\-]+\.(?:' + '|'.join(KNOWN_EXTS) + r')\b',
                      user_input, re.I)
        if m:
            candidate = m.group(0)
            root = Path(__file__).resolve().parent.parent
            for p in [candidate, str(root/candidate), str(root/"data"/candidate)]:
                if Path(p).exists():
                    file_path = p; break

    save_to = None
    if save_report:
        from nexus_ai.config import OUTPUT_DIR
        safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in user_input[:40]).strip()
        save_to = str(OUTPUT_DIR / f"{safe}.md")
    else:
        m2 = re.search(r'[\w./\-]+\.(?:md|txt)', user_input, re.I)
        if m2 and m2.group(0) != file_path:
            save_to = str(Path(__file__).resolve().parent.parent / m2.group(0))

    # Show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    _render_message({"role": "user", "content": user_input})

    # Live progress
    progress_box = st.empty()
    agent_steps  = []

    def on_update(step, content, output=""):
        icon = {"Critic":"🔍","Optimizer":"🔧","Validator":"✅","Planner":"📋",
                "Researcher":"🔎","Coder":"💻","Analyst":"📊","Reporter":"📝",
                "Memory":"🧠","NEXUS":"⚡"}.get(step.split(" ")[0], "·")
        agent_steps.append({"agent": step, "output": content})
        lines = "\n".join(
            f'<div class="agent-step">{icon} <b>[{s["agent"]}]</b> {s["output"][:100]}</div>'
            for s in agent_steps[-6:]
        )
        progress_box.markdown(f"**🔄 Running...**\n{lines}", unsafe_allow_html=True)

    # Run
    t0 = time.time()
    try:
        result = run_async(nexus.run(
            task=user_input, file_path=file_path,
            save_to=save_to, on_update=on_update,
        ))
    except Exception as e:
        result = {
            "answer": f"**Error:** {e}", "trace": [],
            "score": 0, "approved": False,
            "duration_s": time.time()-t0, "plan": {},
        }

    progress_box.empty()
    duration    = round(time.time()-t0, 1)
    agents_used = [s["agent"] for s in result["trace"]]
    approved    = result.get("approved", True)
    score       = result.get("score", "?")

    msg = {
        "role": "assistant", "content": result["answer"],
        "agents_used": agents_used, "score": score,
        "duration": duration, "approved": approved,
        "saved": bool(save_to),
    }
    st.session_state.messages.append(msg)
    st.session_state.last_trace = result["trace"]
    _refresh_mem_stats()

    _render_message(msg)
    st.rerun()
