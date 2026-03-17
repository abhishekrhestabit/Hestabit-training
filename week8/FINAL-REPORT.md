# FINAL REPORT — Week 8: Local LLM Training & Deployment

## Overview

Complete end-to-end pipeline for fine-tuning, quantising, benchmarking, and deploying TinyLlama-1.1B as a local inference microservice.

## Pipeline Summary

| Day | Task | Output |
|-----|------|--------|
| 1 | Dataset preparation & cleaning | `data/train.jsonl`, `data/val.jsonl` |
| 2 | QLoRA fine-tuning (r=16, α=32) | `adapters/adapter_config.json` + weights |
| 3 | Quantisation (GGUF Q4/Q8, BnB INT4/INT8) | `quantized/` directory |
| 4 | Inference benchmarking & optimisation | `benchmarks/results.csv` |
| 5 | FastAPI deployment as local microservice | `deploy/` directory |

## Model Details

- **Base**: TinyLlama/TinyLlama-1.1B-Chat-v1.0 (LlamaForCausalLM, 22 layers, GQA 4 KV heads)
- **Fine-tuning**: QLoRA with LoRA rank=16, alpha=32, dropout=0.05 on q/k/v/o projections
- **Deployed model**: GGUF Q4_K_M (~637 MB) — best size/quality trade-off for local deployment
- **Prompt format**: Alpaca-style (`### Instruction / ### Input / ### Response`)

## Day 5 — Deployment Architecture

### API Design

```
POST /generate  — Single-prompt generation with system/input support
POST /chat      — Multi-turn conversation with message history
GET  /health    — Service health check
```

### Features Implemented

| Feature | Status |
|---------|--------|
| Quantised GGUF model (Q4_K_M) | Done |
| Infinite chat mode (conversation history) | Done |
| System + user prompt support | Done |
| Top-k, top-p, temperature controls | Done |
| Request ID logging | Done |
| SSE streaming generation | Done |
| Model caching (singleton loader) | Done |
| CLI interactive chat mode | Done |
| Dockerfile for containerisation | Done |
| RAG/Agent-ready architecture | Done |

### RAG / Agent Readiness

The API is designed for easy integration with RAG pipelines and agent frameworks:
- **System prompt injection**: Pass retrieval context via the `system` field
- **Structured endpoints**: Standard JSON request/response for tool-use agents
- **Streaming**: SSE support for real-time agent pipelines
- **Stateless**: Each request is self-contained; conversation state managed client-side
- **Configurable generation**: All sampling parameters exposed per-request

### File Structure

```
deploy/
  app.py           — FastAPI server (120 lines) with /generate, /chat, CLI
  model_loader.py  — Singleton GGUF loader + Alpaca prompt formatter
  config.py        — Environment-driven configuration
  requirements.txt — Minimal dependencies (fastapi, uvicorn, llama-cpp-python)
Dockerfile         — Production container image
README.md          — Usage documentation
```

## Quantisation Comparison

| Format | Size | Use Case |
|--------|------|----------|
| FP16 (base) | ~2.2 GB | Training, high-accuracy inference |
| GGUF Q8_0 | ~1.1 GB | High-quality local inference |
| GGUF Q4_K_M | ~637 MB | **Deployed** — optimal size/quality for API |
| BnB INT8 | ~1.1 GB | GPU inference with bitsandbytes |
| BnB INT4 | ~600 MB | Minimal GPU memory footprint |

## Production Considerations

- **Model caching**: Loaded once at startup, reused across requests
- **Logging**: Every request gets a UUID, logged with timing and token counts
- **Configuration**: All settings via environment variables (12-factor app)
- **Containerisation**: Single Dockerfile bundles model + server
- **Resource efficiency**: GGUF Q4 runs on CPU with ~1GB RAM, no GPU required

## How to Run

```bash
cd deploy && pip install -r requirements.txt && python app.py

docker build -t tinyllama-api . && docker run -p 8000:8000 tinyllama-api

cd deploy && python app.py --cli
```

## Conclusion

The pipeline demonstrates a complete local LLM workflow: from dataset preparation through QLoRA fine-tuning, multi-format quantisation, systematic benchmarking, to production-ready API deployment. The GGUF Q4_K_M model provides an excellent balance of size (~637 MB) and quality for local microservice use, running efficiently on CPU without GPU requirements.
        return embeddings.squeeze().cpu().numpy().tolist()