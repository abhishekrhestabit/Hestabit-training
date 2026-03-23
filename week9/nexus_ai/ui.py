"""
nexus_ai/ui.py  —  NEXUS AI Streamlit Chat UI
Run from week9/:  streamlit run nexus_ai/ui.py
"""

import asyncio, sys, time, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from nexus_ai.config       import get_model_client, ACTIVE_PROVIDER, OLLAMA_MODEL, GEMINI_MODEL
from nexus_ai.orchestrator import NexusOrchestrator


# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="NEXUS AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #0f1117; }
[data-testid="stSidebar"] * { color: #e0e0e0 !important; }

.user-bubble {
    background: #2d2d44;
    border-radius: 18px 18px 4px 18px;
    padding: 12px 16px;
    margin: 8px 0 8px 80px;
    color: #f0f0f0;
    font-size: 15px;
    line-height: 1.5;
}
.nexus-bubble {
    background: #1a2744;
    border-radius: 18px 18px 18px 4px;
    padding: 14px 18px;
    margin: 8px 80px 8px 0;
    color: #e8f4fd;
    font-size: 15px;
    border-left: 3px solid #4a9eff;
    line-height: 1.6;
}
.nexus-bubble.flagged {
    border-left: 3px solid #ff6b6b;
    background: #2a1a1a;
}
.agent-tag {
    display: inline-block;
    background: #0d2137;
    color: #4a9eff;
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 11px;
    margin: 2px 1px;
    font-weight: 600;
}
.agent-tag.fix    { background: #1a2200; color: #aaff44; }
.agent-tag.memory { background: #1a0033; color: #cc88ff; }
.meta-bar {
    font-size: 12px;
    color: #666;
    margin-top: 8px;
    padding-top: 6px;
    border-top: 1px solid #222;
}
.score-pass  { color: #44ff88; font-weight: bold; }
.score-fail  { color: #ff6b6b; font-weight: bold; }
.agent-step {
    background: #0d1117;
    border-left: 2px solid #333;
    padding: 6px 10px;
    margin: 3px 0;
    font-size: 12px;
    color: #aaa;
    font-family: monospace;
}
.main .block-container { max-width: 900px; padding-top: 1rem; }
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────
defaults = {
    "messages":     [],
    "orchestrator": None,
    "last_trace":   [],
    "agent_steps":  [],   # live agent steps for current run
    "mem_stats":    {"session": 0, "vectors": 0, "facts": 0},
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Helpers ───────────────────────────────────────────────────────
def get_nexus() -> NexusOrchestrator:
    if st.session_state.orchestrator is None:
        with st.spinner("Initialising NEXUS AI..."):
            client = get_model_client()
            st.session_state.orchestrator = NexusOrchestrator(client)
            _refresh_mem_stats()
    return st.session_state.orchestrator


def _refresh_mem_stats():
    nexus = st.session_state.orchestrator
    if nexus and nexus.session:
        st.session_state.mem_stats = {
            "session": nexus.session.turn_count,
            "vectors": nexus.vector.count if nexus.vector else 0,
            "facts":   nexus.ltm.count    if nexus.ltm    else 0,
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


def _tag(agent: str) -> str:
    css = "fix" if "(fix)" in agent or "post-fix" in agent else \
          "memory" if agent == "Memory" else ""
    return f'<span class="agent-tag {css}">{agent}</span>'


# ── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 NEXUS AI")
    st.markdown("*Autonomous Multi-Agent System*")
    st.divider()

    # Model info
    model_label = OLLAMA_MODEL if ACTIVE_PROVIDER == "ollama" else GEMINI_MODEL
    st.markdown(f"**Provider:** `{ACTIVE_PROVIDER.upper()}`")
    st.markdown(f"**Model:** `{model_label}`")
    st.divider()

    # Memory panel
    st.markdown("### 🧠 Memory")
    ms = st.session_state.mem_stats
    col1, col2, col3 = st.columns(3)
    col1.metric("Session", ms["session"])
    col2.metric("Vectors", ms["vectors"])
    col3.metric("Facts",   ms["facts"])

    if st.button("🗑️ Clear memory", use_container_width=True):
        nexus = st.session_state.orchestrator
        if nexus:
            if nexus.session: nexus.session.clear()
            if nexus.vector:  nexus.vector.clear()
            if nexus.ltm:     nexus.ltm.clear()
            _refresh_mem_stats()
            st.success("Memory cleared.")

    # Show memory contents
    nexus = st.session_state.orchestrator
    if nexus and nexus.ltm and nexus.ltm.count > 0:
        with st.expander(f"📋 Stored facts ({nexus.ltm.count})", expanded=False):
            facts = nexus.ltm.get_recent(n=10)
            for f in facts:
                st.caption(f"• {f['fact'][:80]}")
    st.divider()

    # Options
    st.markdown("### ⚙️ Options")
    uploaded_file = st.file_uploader(
        "Attach file", type=["csv","txt","md","json","py","db","yaml"],
        help="Passed to Researcher and Analyst agents"
    )
    save_report = st.checkbox(
        "💾 Auto-save report", value=False,
        help="Saves Reporter output to nexus_ai/outputs/"
    )
    st.divider()

    # Conversation controls
    st.markdown("### 💬 Conversation")
    if st.button("🗑️ Clear chat history", use_container_width=True):
        st.session_state.messages   = []
        st.session_state.last_trace = []
        st.rerun()

    # Last run trace
    if st.session_state.last_trace:
        with st.expander(f"🔍 Last trace ({len(st.session_state.last_trace)} steps)"):
            for step in st.session_state.last_trace:
                a   = step["agent"]
                out = str(step.get("output", ""))
                st.markdown(f"**[{a}]**")
                st.code(out[:400] + ("..." if len(out) > 400 else ""), language=None)

    st.divider()
    st.caption("NEXUS AI — Week 9 Capstone")


# ── Main area ─────────────────────────────────────────────────────
st.markdown("# 🤖 NEXUS AI")
st.markdown("*Multi-agent AI — Planner · Researcher · Coder · Analyst · Critic · Optimizer · Validator · Reporter*")
st.divider()

# Render chat history
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f'<div class="user-bubble">👤 &nbsp;{msg["content"]}</div>',
            unsafe_allow_html=True,
        )
    else:
        approved    = msg.get("approved", True)
        agents_used = msg.get("agents_used", [])
        score       = msg.get("score", "?")
        duration    = msg.get("duration", "?")
        saved       = msg.get("saved", False)

        tags      = "".join(_tag(a) for a in agents_used)
        score_css = "score-pass" if str(score).isdigit() and int(score) >= 7 else "score-fail"
        bubble_cls = "nexus-bubble" + ("" if approved else " flagged")
        flag_icon  = "✅" if approved else "⚠️"

        meta = (
            f'<div class="meta-bar">'
            f'{tags}'
            f'&nbsp;|&nbsp;<span class="{score_css}">{flag_icon} {score}/10</span>'
            f'&nbsp;|&nbsp;{duration}s'
            f'{"&nbsp;|&nbsp;💾 Saved" if saved else ""}'
            f'</div>'
        )
        # Render markdown content inside the bubble
        content_html = msg["content"].replace("\n", "<br>")
        st.markdown(
            f'<div class="{bubble_cls}">🤖 &nbsp;{content_html}{meta}</div>',
            unsafe_allow_html=True,
        )

# ── Input ─────────────────────────────────────────────────────────
st.divider()
user_input = st.chat_input("Ask NEXUS AI anything...")

if user_input:
    nexus = get_nexus()

    # Handle uploaded file
    file_path = None
    if uploaded_file:
        from nexus_ai.config import OUTPUT_DIR
        tmp = OUTPUT_DIR / uploaded_file.name
        tmp.write_bytes(uploaded_file.getvalue())
        file_path = str(tmp)

    # Auto-detect file path from query text (like CLI)
    if not file_path:
        KNOWN_EXTS = {"csv","txt","md","json","db","py","yaml","yml","log","html"}
        m = re.search(r'(?:(?:[\w\-]+/)*)[\w\-]+\.(?:' + '|'.join(KNOWN_EXTS) + r')\b',
                      user_input, re.I)
        if m:
            candidate = m.group(0)
            root = Path(__file__).resolve().parent.parent
            for p in [candidate, str(root/candidate), str(root/"data"/candidate)]:
                if Path(p).exists():
                    file_path = p
                    break

    # Auto-detect save path
    save_to = None
    if save_report:
        from nexus_ai.config import OUTPUT_DIR
        safe = "".join(c if c.isalnum() or c in " _-" else "_"
                       for c in user_input[:40]).strip()
        save_to = str(OUTPUT_DIR / f"{safe}.md")
    else:
        # Auto-detect .md / .txt output mentioned in query
        m2 = re.search(r'[\w./\-]+\.(?:md|txt)', user_input, re.I)
        if m2 and m2.group(0) != file_path:
            root = Path(__file__).resolve().parent.parent
            save_to = str(root / m2.group(0))

    # Show user message immediately
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.markdown(
        f'<div class="user-bubble">👤 &nbsp;{user_input}</div>',
        unsafe_allow_html=True,
    )

    # Live agent progress
    progress_box  = st.empty()
    agent_steps   = []

    def on_update(step: str, content: str, output: str = ""):
        if step == "__output__":
            agent_steps.append({
                "agent":  content,
                "output": output[:300] + ("..." if len(output) > 300 else ""),
            })
            lines = "\n".join(
                f'<div class="agent-step">✅ <b>[{s["agent"]}]</b> '
                f'{s["output"][:80]}...</div>'
                for s in agent_steps[-5:]
            )
        else:
            icon = {"Critic":"🔍","Optimizer":"🔧","Validator":"✅",
                    "Planner":"📋","Researcher":"🔎","Coder":"💻",
                    "Analyst":"📊","Reporter":"📝","Memory":"🧠"}.get(step, "·")
            agent_steps.append({"agent": step, "output": content})
            lines = "\n".join(
                f'<div class="agent-step">{icon} <b>[{s["agent"]}]</b> '
                f'{s["output"][:100]}</div>'
                for s in agent_steps[-6:]
            )
        progress_box.markdown(
            f"**🔄 Pipeline running...**\n{lines}",
            unsafe_allow_html=True,
        )

    # Run pipeline
    t0 = time.time()
    try:
        result = run_async(nexus.run(
            task      = user_input,
            file_path = file_path,
            save_to   = save_to,
            on_update = on_update,
        ))
    except Exception as e:
        import traceback
        result = {
            "answer":     f"**Pipeline error:**\n```\n{e}\n```",
            "trace":      [],
            "score":      0,
            "approved":   False,
            "duration_s": time.time() - t0,
            "plan":       {},
        }

    progress_box.empty()
    duration    = round(time.time() - t0, 1)
    agents_used = [s["agent"] for s in result["trace"]]
    approved    = result.get("approved", True)
    score       = result.get("score", "?")

    # Persist message
    st.session_state.messages.append({
        "role":        "assistant",
        "content":     result["answer"],
        "agents_used": agents_used,
        "score":       score,
        "duration":    duration,
        "approved":    approved,
        "saved":       bool(save_to),
    })
    st.session_state.last_trace = result["trace"]
    _refresh_mem_stats()

    # Render answer
    score_css  = "score-pass" if str(score).isdigit() and int(score) >= 7 else "score-fail"
    bubble_cls = "nexus-bubble" + ("" if approved else " flagged")
    flag_icon  = "✅" if approved else "⚠️"
    tags       = "".join(_tag(a) for a in agents_used)
    meta = (
        f'<div class="meta-bar">'
        f'{tags}'
        f'&nbsp;|&nbsp;<span class="{score_css}">{flag_icon} {score}/10</span>'
        f'&nbsp;|&nbsp;{duration}s'
        f'{"&nbsp;|&nbsp;💾 Saved" if save_to else ""}'
        f'</div>'
    )
    content_html = result["answer"].replace("\n", "<br>")
    st.markdown(
        f'<div class="{bubble_cls}">🤖 &nbsp;{content_html}{meta}</div>',
        unsafe_allow_html=True,
    )
    st.rerun()