"""Application configuration."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Model settings
MODEL_PATH = os.environ.get("MODEL_PATH", os.path.join(ROOT, "quantized", "model-q4_k_m.gguf"))
N_CTX = int(os.environ.get("N_CTX", 2048))
N_THREADS = int(os.environ.get("N_THREADS", os.cpu_count() or 4))
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", 256))

# Generation defaults
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TOP_P = 0.9
DEFAULT_TOP_K = 40

# Server
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8000))

# Prompt template (Alpaca-style, matching training format)
SYSTEM_TEMPLATE = "### System:\n{system}\n\n"
USER_TEMPLATE = "### Instruction:\n{instruction}\n\n### Response:\n"
USER_INPUT_TEMPLATE = "### Instruction:\n{instruction}\n\n### Input:\n{input}\n\n### Response:\n"
