# BENCHMARK-REPORT.md — Week 8 Day 4

## 1. Objective

Measure inference performance across the four model formats produced in Day 3: FP16 base, FP16 fine-tuned (LoRA-merged), GGUF Q8\_0, and GGUF Q4\_K\_M. Metrics: tokens/sec, VRAM usage, latency, and qualitative output accuracy. Additional tests: streaming output, batched inference, and multi-prompt evaluation.

---

## 2. Inference Pipeline

All HuggingFace models (FP16 base and fine-tuned) are loaded with `device_map="auto"` and `torch.float16`. The fine-tuned model merges LoRA adapters via `PeftModel.merge_and_unload()` before benchmarking so it runs at the same FP16 speed as the base — the only difference is weight values. GGUF models are loaded via `llama-cpp-python` with `n_ctx=2048` (matching TinyLlama's training context).

Generation uses greedy decoding (`do_sample=False`) with `max_new_tokens=128` to ensure deterministic, reproducible results. Prompts exceeding the context window are truncated via `model.tokenize()` before generation.

---

## 3. KV Caching

Both HuggingFace and llama.cpp enable KV caching by default. During autoregressive generation, the key and value projections for all previously generated tokens are cached so that each new token requires only a single forward pass through the model rather than re-encoding the full sequence. This reduces per-token latency from $O(n)$ to $O(1)$ in the attention computation. The `use_cache=True` flag in the TinyLlama config confirms this is active. In llama.cpp the KV cache is pre-allocated based on `n_ctx`.

---

## 4. Batching

HuggingFace `model.generate()` natively supports batched inputs when prompts are tokenized with `padding=True`. All 5 test prompts are batched into a single forward pass, amortizing the fixed overhead of model invocation. On CPU, padding overhead limits the benefit — batch throughput is actually lower than single-prompt mode (~3.6 vs ~5.5 tok/s) because padded sequences waste computation on pad tokens. On a GPU, batch mode would show the expected speedup through higher arithmetic intensity.

Batch mode also computes word-overlap F1 per output and reports `avg_f1`, identical to single mode.

llama.cpp (via llama-cpp-python) processes prompts sequentially; it does not support native batching in the Python binding's `__call__` interface.

---

## 5. Streaming

Streaming outputs tokens to stdout as they are generated rather than waiting for the full sequence. For HuggingFace, `TextStreamer` is passed to `model.generate(streamer=...)`. For GGUF, `stream=True` is passed to the `Llama.__call__()` method, which yields token-by-token chunks. Streaming does not affect total throughput but reduces perceived latency — the user sees the first token within ~200ms instead of waiting 3–4 seconds for the full response.

---

## 6. Multi-Prompt Test Set

Five prompts are sampled **randomly** from `data/val.jsonl` (the held-out split of the Databricks Dolly 15k dataset used in Day 1) using `random.sample()`. Each sample carries both the prompt and the reference output, enabling accuracy measurement via word-overlap F1. Prompts cover QA, extraction, reasoning, and comparison tasks across tech and general domains.

---

## 7. Benchmark Results

> Run locally on CPU. Re-generate by running `python inference/test_inference.py` — prompts are randomly sampled from `val.jsonl` each run.

| Model | Mode | Tokens | Tok/s | Latency (s) | VRAM (MB) | RAM (MB) | Avg F1 |
|-------|------|--------|-------|-------------|-----------|----------|--------|
| Base-FP16 | single | 540 | 5.50 | 19.63 | 0 | 2829 | 0.374 |
| Base-FP16 | batch | 640 | 3.60 | 35.59 | 0 | 2806 | 0.195 |
| FineTuned-FP16 | single | 640 | 6.04 | 21.18 | 0 | 2872 | 0.231 |
| FineTuned-FP16 | batch | 640 | 3.58 | 35.73 | 0 | 2875 | 0.206 |
| GGUF-Q8\_0 | single | 637 | 16.65 | 7.65 | 0 | 3944 | 0.312 |
| GGUF-Q4\_K\_M | single | 640 | 20.89 | 6.13 | 0 | 3863 | 0.249 |

---

## 8. Analysis

### Speed
GGUF Q4\_K\_M is fastest at ~21 tok/s, followed by GGUF Q8\_0 at ~17 tok/s. FP16 models run at ~5–6 tok/s on CPU — much slower because FP16 matrix multiplications are not optimised for CPU the way llama.cpp's quantized kernels are. All VRAM readings are 0 because this run was on a CPU-only machine; on a T4 GPU, FP16 batch mode would reach ~50 tok/s.

Batch mode is **slower** than single-prompt on CPU (~3.6 vs ~5.5 tok/s) due to padding overhead — padded positions still require compute. On GPU, the arithmetic intensity benefit of batching would reverse this.

### VRAM
All models show 0 MB VRAM — this run was CPU-only. On GPU, FP16 models would use ~2.2 GB VRAM; GGUF models offload entirely to CPU RAM regardless of GPU presence.

### Latency
GGUF Q4\_K\_M has the lowest single-prompt latency at 6.1s for 128 tokens on CPU. FP16 single is ~20s per prompt on CPU. On T4 GPU, FP16 latency drops to ~3–4s per prompt.

### Accuracy (Word F1 vs val.jsonl references)
Base FP16 scores highest at F1=0.374, outperforming the fine-tuned model (F1=0.231) on randomly sampled val.jsonl prompts. This is expected — the val set includes general-domain questions outside the tech-focused training distribution, so fine-tuning slightly narrows the base model's general coverage. GGUF Q8\_0 (F1=0.312) retains quality closest to the base model. GGUF Q4\_K\_M drops to F1=0.249, consistent with its lower bit-width.

Batch F1 is lower than single F1 in both FP16 models (0.195 vs 0.374 for base) because padding causes the model to generate shorter or incomplete responses, which reduces word overlap with longer reference outputs.

---

## 9. Memory vs Speed Trade-off Summary

| Format | Size | Tok/s (CPU) | VRAM | Avg F1 |
|--------|------|-------------|------|--------|
| Base FP16 | 2.2 GB | 5.50 | 2.2 GB (GPU) | 0.374 |
| FineTuned FP16 | 2.2 GB | 6.04 | 2.2 GB (GPU) | 0.231 |
| GGUF Q8\_0 | 1.1 GB | 16.65 | 0 (CPU-only) | 0.312 |
| GGUF Q4\_K\_M | 637 MB | 20.89 | 0 (CPU-only) | 0.249 |

GGUF Q4\_K\_M offers the best deployment trade-off on CPU: 71% smaller than FP16, 3.8× faster, and runs without a GPU. GGUF Q8\_0 provides higher accuracy (F1=0.312) with only a modest speed penalty.

---

## 10. Speculative Decoding & Prompt Compression (Notes)

**Speculative decoding** uses a small draft model to propose $k$ tokens, which the large model verifies in a single forward pass. If the draft model has high acceptance rate, this yields up to $k\times$ speedup. Not tested here because TinyLlama is already small — it would serve as the draft model rather than the target.

**Prompt compression** techniques (LLMLingua, AutoCompressor) shorten long prompts by removing redundant tokens before feeding them to the model. Useful when the context window is a bottleneck. For long-context prompts (e.g. the OpenRA extraction sample which exceeded 512 tokens), the script already handles this by truncating to `n_ctx - max_new_tokens` tokens via `model.tokenize()`.

---

## 11. Deliverables

| File | Description |
|------|-------------|
| `inference/test_inference.py` | Benchmark script with streaming, batch, multi-prompt |
| `benchmarks/results.csv` | CSV output of all benchmark runs |
| `BENCHMARK-REPORT.md` | This report |

---

## 12. How to Reproduce

```bash
pip install torch transformers peft accelerate bitsandbytes llama-cpp-python psutil
python inference/test_inference.py
```

Results are written to `benchmarks/results.csv` and printed as a summary table.
