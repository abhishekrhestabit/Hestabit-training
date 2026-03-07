# Week 8 — Local LLM Training, Quantisation & Deployment

End-to-end workflow: fine-tune TinyLlama-1.1B with QLoRA, quantise to GGUF/INT4/INT8, benchmark, and deploy as a local API.

## Project Structure

```
adapters/          QLoRA adapter weights (LoRA r=16, α=32)
benchmarks/        Inference benchmark results
data/              Training & validation JSONL
deploy/            FastAPI inference server (Day 5 capstone)
  app.py           API server with /generate, /chat, CLI mode
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

# Start API server
python app.py

# Or interactive CLI chat
python app.py --cli
```

## API Endpoints

### POST /generate
Single-prompt generation with Alpaca-style formatting.
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain quantum computing in simple terms", "max_tokens": 128, "temperature": 0.7}'
```

### POST /chat
Multi-turn chat with system prompt and conversation history.
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is machine learning?"}],
    "system": "You are a helpful AI tutor.",
    "temperature": 0.7
  }'
```

### Streaming
Set `"stream": true` in either endpoint to get SSE token-by-token output.

### GET /health
Returns model status.

## Generation Controls

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `max_tokens` | 256 | 1–2048 | Maximum tokens to generate |
| `temperature` | 0.7 | 0.0–2.0 | Sampling randomness |
| `top_p` | 0.9 | 0.0–1.0 | Nucleus sampling threshold |
| `top_k` | 40 | 0+ | Top-K sampling |

## Docker

```bash
docker build -t tinyllama-api .
docker run -p 8000:8000 tinyllama-api
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_PATH` | `quantized/model-q4_k_m.gguf` | Path to GGUF model |
| `N_CTX` | 2048 | Context window size |
| `N_THREADS` | CPU count | Inference threads |
| `MAX_TOKENS` | 256 | Default max generation tokens |
| `HOST` | 0.0.0.0 | Server bind address |
| `PORT` | 8000 | Server port |
