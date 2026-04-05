"""Singleton model loader with caching for GGUF models."""
import logging
from llama_cpp import Llama
from config import MODEL_PATH, N_CTX, N_THREADS

logger = logging.getLogger(__name__)

_model: Llama | None = None


def get_model() -> Llama:
    """Return cached model instance, loading on first call."""
    global _model
    if _model is None:
        logger.info(f"Loading model from {MODEL_PATH} (ctx={N_CTX}, threads={N_THREADS})")
        _model = Llama(model_path=MODEL_PATH, n_ctx=N_CTX, n_threads=N_THREADS, verbose=False)
        logger.info("Model loaded successfully")
    return _model


def format_prompt(instruction: str, input_text: str = "", system: str = "") -> str:
    """Build Alpaca-style prompt matching the fine-tuned format."""
    parts = []
    if system:
        parts.append(f"### System:\n{system}\n")
    if input_text.strip():
        parts.append(f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n")
    else:
        parts.append(f"### Instruction:\n{instruction}\n\n### Response:\n")
    return "\n".join(parts)


def format_chat(messages: list[dict], system: str = "") -> str:
    """Convert chat messages list into a single prompt string."""
    parts = []
    if system:
        parts.append(f"### System:\n{system}\n")
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            parts.append(f"### Instruction:\n{content}\n")
        elif role == "assistant":
            parts.append(f"### Response:\n{content}\n")
    parts.append("### Response:\n")
    return "\n".join(parts)
