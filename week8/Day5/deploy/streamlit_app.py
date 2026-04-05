import uuid
from typing import Any, cast

import streamlit as st

from config import DEFAULT_TEMPERATURE, DEFAULT_TOP_K, DEFAULT_TOP_P, MAX_TOKENS
from model_loader import format_chat, format_prompt, get_model


STOP_SEQS = ["### Instruction:", "### System:", "### Input:", "\nYou:", "\nUser:"]
MAX_HISTORY_TURNS = 10


def trim_history(messages: list[dict]) -> list[dict]:
    max_messages = MAX_HISTORY_TURNS * 2
    if len(messages) > max_messages:
        return messages[-max_messages:]
    return messages


def local_generate(prompt: str, max_tokens: int, temperature: float, top_p: float, top_k: int) -> str:
    model = get_model()
    out = model(
        prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        echo=False,
        stream=False,
        stop=STOP_SEQS,
    )
    result = cast(dict[str, Any], out)
    return str(result["choices"][0]["text"]).strip()


st.set_page_config(page_title="TinyLlama Chat", layout="wide")

st.title("TinyLlama Streamlit Chat")
st.caption("Local-only chat and generation UI running directly in Streamlit.")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "system" not in st.session_state:
    st.session_state.system = "You are a helpful assistant."
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())


with st.sidebar:
    st.subheader("Generation Settings")
    st.session_state.system = st.text_area("System Prompt", value=st.session_state.system, height=120)
    temperature = st.slider("Temperature", min_value=0.0, max_value=2.0, value=float(DEFAULT_TEMPERATURE), step=0.1)
    top_p = st.slider("Top P", min_value=0.0, max_value=1.0, value=float(DEFAULT_TOP_P), step=0.05)
    top_k = st.number_input("Top K", min_value=0, value=int(DEFAULT_TOP_K), step=1)
    max_tokens = st.number_input("Max Tokens", min_value=1, max_value=2048, value=int(MAX_TOKENS), step=16)
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()


chat_tab, generate_tab = st.tabs(["Chat", "Generate"])

with chat_tab:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Ask something...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.messages = trim_history(st.session_state.messages)

        with st.chat_message("user"):
            st.markdown(user_input)

        assistant_text = ""
        with st.chat_message("assistant"):
            placeholder = st.empty()
            try:
                prompt = format_chat(st.session_state.messages, st.session_state.system)
                assistant_text = local_generate(
                    prompt,
                    max_tokens=int(max_tokens),
                    temperature=float(temperature),
                    top_p=float(top_p),
                    top_k=int(top_k),
                )
                placeholder.markdown(assistant_text)
            except Exception as exc:  # broad catch to show model/runtime issues in UI
                st.error(f"Inference error: {exc}")

        if assistant_text:
            st.session_state.messages.append({"role": "assistant", "content": assistant_text})
            st.session_state.messages = trim_history(st.session_state.messages)


with generate_tab:
    st.subheader("Single Prompt Generation")
    prompt_text = st.text_area("Instruction", height=140)
    input_text = st.text_area("Input (optional)", height=120)

    if st.button("Generate", use_container_width=True):
        if not prompt_text.strip():
            st.warning("Please enter an instruction.")
        else:
            with st.spinner("Generating..."):
                try:
                    formatted_prompt = format_prompt(prompt_text, input_text, st.session_state.system)
                    output_text = local_generate(
                        formatted_prompt,
                        max_tokens=int(max_tokens),
                        temperature=float(temperature),
                        top_p=float(top_p),
                        top_k=int(top_k),
                    )

                    st.markdown("### Output")
                    st.write(output_text)
                except Exception as exc:  # broad catch to show model/runtime issues in UI
                    st.error(f"Inference error: {exc}")
