import uuid
import json

import requests
import streamlit as st

from config import DEFAULT_TEMPERATURE, DEFAULT_TOP_K, DEFAULT_TOP_P, MAX_TOKENS, PORT


st.set_page_config(page_title="TinyLlama Chat", layout="wide")

st.title("TinyLlama Streamlit Chat")
st.caption("Local chat UI with CLI-style rolling history (last 10 turns).")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "system" not in st.session_state:
    st.session_state.system = "You are a helpful assistant."
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

with st.sidebar:
    st.subheader("Generation Settings")
    api_url = st.text_input("API URL", value=f"http://localhost:{PORT}/chat")
    st.session_state.system = st.text_area("System Prompt", value=st.session_state.system, height=120)
    temperature = st.slider("Temperature", min_value=0.0, max_value=2.0, value=float(DEFAULT_TEMPERATURE), step=0.1)
    top_p = st.slider("Top P", min_value=0.0, max_value=1.0, value=float(DEFAULT_TOP_P), step=0.05)
    top_k = st.number_input("Top K", min_value=0, value=int(DEFAULT_TOP_K), step=1)
    max_tokens = st.number_input("Max Tokens", min_value=1, max_value=2048, value=int(MAX_TOKENS), step=16)
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


user_input = st.chat_input("Ask something...")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    payload = {
        "session_id": st.session_state.session_id,
        "messages": [{"role": "user", "content": user_input}],
        "system": st.session_state.system,
        "max_tokens": int(max_tokens),
        "temperature": float(temperature),
        "top_p": float(top_p),
        "top_k": int(top_k),
        "stream": True,
    }

    assistant_text = ""
    error_text = ""
    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            response = requests.post(api_url, json=payload, timeout=300, stream=True)
            response.raise_for_status()
            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                if not raw_line.startswith("data: "):
                    continue

                data_line = raw_line[len("data: "):].strip()
                if data_line == "[DONE]":
                    break

                try:
                    event = json.loads(data_line)
                except json.JSONDecodeError:
                    continue

                token = event.get("token", "")
                if token:
                    assistant_text += token
                    placeholder.markdown(assistant_text)
        except requests.RequestException as exc:
            error_text = f"API error: {exc}"
            st.error(error_text)
        finally:
            if assistant_text:
                placeholder.markdown(assistant_text)

    if assistant_text:
        st.session_state.messages.append({"role": "assistant", "content": assistant_text})
