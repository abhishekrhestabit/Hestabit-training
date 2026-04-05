# Week 8 — Local LLM Training, Quantisation & Deployment

End-to-end workflow: fine-tune TinyLlama-1.1B with QLoRA, quantise to GGUF/INT4/INT8, benchmark, and deploy as a local Streamlit app.

## Project Structure

```
adapters/          QLoRA adapter weights (LoRA r=16, α=32)
benchmarks/        Inference benchmark results
data/              Training & validation JSONL
deploy/            Streamlit inference app (Day 5 capstone)
  streamlit_app.py Streamlit UI with Chat + Generate tabs
  model_loader.py  Singleton model loader with prompt formatting
  config.py        Environment-configurable settings
  requirements.txt Python dependencies
inference/         Day 4 benchmark scripts
notebooks/         QLoRA training & quantisation notebooks
quantized/         GGUF + bitsandbytes quantised models
utils/             Data cleaning utilities
Dockerfile         Container deployment
```

## Quick Start

```bash
cd deploy
pip install -r requirements.txt

# Start Streamlit app
streamlit run streamlit_app.py
```

## Streamlit Features

- Chat tab with rolling conversation memory (last 10 turns)
- Generate tab for single instruction/input prompt generation
- Adjustable generation controls: max_tokens, temperature, top_p, top_k
- Local inference (no FastAPI dependency at runtime)

## Generation Controls

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `max_tokens` | 256 | 1–2048 | Maximum tokens to generate |
| `temperature` | 0.7 | 0.0–2.0 | Sampling randomness |
| `top_p` | 0.9 | 0.0–1.0 | Nucleus sampling threshold |
| `top_k` | 40 | 0+ | Top-K sampling |

## Docker

```bash
docker build -t tinyllama-streamlit .
docker run -p 8501:8501 tinyllama-streamlit
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_PATH` | `quantized/model-q4_k_m.gguf` | Path to GGUF model |
| `N_CTX` | 2048 | Context window size |
| `N_THREADS` | CPU count | Inference threads |
| `MAX_TOKENS` | 256 | Default max generation tokens |
| `STREAMLIT_SERVER_ADDRESS` | 0.0.0.0 | Streamlit bind address |
| `STREAMLIT_SERVER_PORT` | 8501 | Streamlit port |
