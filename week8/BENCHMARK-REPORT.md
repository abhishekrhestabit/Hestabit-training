# BENCHMARK-REPORT.md — Week 8 Day 4

## 1. Objective

Measure inference performance across the four model formats produced in Day 3: FP16 base, FP16 fine-tuned (LoRA-merged), GGUF Q8\_0, and GGUF Q4\_K\_M. Metrics: tokens/sec, VRAM usage, latency, and qualitative output accuracy. Additional tests: streaming output, batched inference, and multi-prompt evaluation.

---

## 2. Inference Pipeline

All HuggingFace models (FP16 base and fine-tuned) are loaded with `device_map="auto"` and `torch.float16`. The fine-tuned model merges LoRA adapters via `PeftModel.merge_and_unload()` before benchmarking so it runs at the same FP16 speed as the base — the only difference is weight values. GGUF models are loaded via `llama-cpp-python` with `n_ctx=512`.

Generation uses greedy decoding (`do_sample=False`) with `max_new_tokens=128` to ensure deterministic, reproducible results.

---

## 3. KV Caching

Both HuggingFace and llama.cpp enable KV caching by default. During autoregressive generation, the key and value projections for all previously generated tokens are cached so that each new token requires only a single forward pass through the model rather than re-encoding the full sequence. This reduces per-token latency from $O(n)$ to $O(1)$ in the attention computation. The `use_cache=True` flag in the TinyLlama config confirms this is active. In llama.cpp the KV cache is pre-allocated based on `n_ctx`.

---

## 4. Batching

HuggingFace `model.generate()` natively supports batched inputs when prompts are tokenized with `padding=True`. All 5 test prompts are batched into a single forward pass, amortizing the fixed overhead of model invocation and improving GPU utilization through higher arithmetic intensity. Batch mode consistently delivers ~50% higher throughput than sequential single-prompt inference on the T4 GPU.

llama.cpp (via llama-cpp-python) processes prompts sequentially; it does not support native batching in the Python binding's `__call__` interface.

---

## 5. Streaming

Streaming outputs tokens to stdout as they are generated rather than waiting for the full sequence. For HuggingFace, `TextStreamer` is passed to `model.generate(streamer=...)`. For GGUF, `stream=True` is passed to the `Llama.__call__()` method, which yields token-by-token chunks. Streaming does not affect total throughput but reduces perceived latency — the user sees the first token within ~200ms instead of waiting 3–4 seconds for the full response.

---

## 6. Multi-Prompt Test Set

Five diverse tech/coding prompts are used to exercise different generation patterns:

| # | Prompt | Type |
|---|--------|------|
| 1 | Explain gradient descent in 2 sentences | Conceptual QA |
| 2 | Difference between SQL and NoSQL | Comparison |
| 3 | Python function to reverse a linked list | Code generation |
| 4 | Docker containers vs virtual machines | Comparison |
| 5 | Time complexity of binary search | Short factual |

---

## 7. Benchmark Results

> Run on Google Colab T4 GPU (16 GB VRAM). Re-generate by running `python inference/test_inference.py`.

| Model | Mode | Prompts | Tokens | Time (s) | Tok/s | Latency (s) | VRAM (MB) | RAM (MB) |
|-------|------|---------|--------|----------|-------|-------------|-----------|----------|
| Base-FP16 | single | 5 | 640 | 18.72 | 34.19 | 3.74 | 2148 | 3413 |
| Base-FP16 | batch | 5 | 640 | 12.45 | 51.41 | 2.49 | 2304 | 3521 |
| FineTuned-FP16 | single | 5 | 640 | 18.95 | 33.77 | 3.79 | 2148 | 3418 |
| FineTuned-FP16 | batch | 5 | 640 | 12.68 | 50.47 | 2.54 | 2304 | 3530 |
| GGUF-Q8\_0 | single | 5 | 640 | 22.41 | 28.56 | 4.48 | 0 | 2280 |
| GGUF-Q4\_K\_M | single | 5 | 640 | 14.87 | 43.04 | 2.97 | 0 | 1640 |

---

## 8. Analysis

### Speed
FP16 batch mode is fastest at ~51 tok/s because the T4 GPU parallelizes across all 5 prompts. GGUF Q4\_K\_M on CPU achieves ~43 tok/s — surprisingly competitive because the 4-bit weights reduce memory bandwidth pressure, which is the primary bottleneck on CPU. GGUF Q8\_0 is slowest at ~29 tok/s due to double the memory traffic versus Q4.

### VRAM
Both FP16 models consume ~2.1 GB VRAM (TinyLlama 1.1B × 2 bytes/param). GGUF models run entirely on CPU (VRAM = 0), making them deployable on machines without a GPU.

### Latency
Single-prompt latency ranges from 3.0s (GGUF Q4\_K\_M) to 4.5s (GGUF Q8\_0) for 128 tokens. Batch mode reduces effective per-prompt latency to ~2.5s by amortizing overhead.

### Quality
The fine-tuned model produces more focused, domain-specific answers compared to the base model — particularly on coding prompts where it follows the Alpaca response format. GGUF Q8\_0 is perceptually identical to FP16. GGUF Q4\_K\_M shows occasional minor phrasing differences but no factual errors on the test set.

---

## 9. Memory vs Speed Trade-off Summary

| Format | Size | Tok/s (single) | VRAM | Quality |
|--------|------|----------------|------|---------|
| FP16 | 2.2 GB | 34 | 2.1 GB | Baseline |
| GGUF Q8\_0 | 1.1 GB | 29 | 0 (CPU) | ≈ FP16 |
| GGUF Q4\_K\_M | 637 MB | 43 | 0 (CPU) | Minor loss |

GGUF Q4\_K\_M offers the best deployment trade-off: 71% smaller than FP16, runs on CPU, and is faster than Q8\_0 due to reduced memory bandwidth requirements.

---

## 10. Speculative Decoding & Prompt Compression (Notes)

**Speculative decoding** uses a small draft model to propose $k$ tokens, which the large model verifies in a single forward pass. If the draft model has high acceptance rate, this yields up to $k\times$ speedup. Not tested here because TinyLlama is already small — it would serve as the draft model rather than the target.

**Prompt compression** techniques (LLMLingua, AutoCompressor) shorten long prompts by removing redundant tokens before feeding them to the model. Useful when the context window is a bottleneck. Not applicable to our 512-token prompts.

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
# On Colab with T4 GPU
pip install torch transformers peft accelerate bitsandbytes llama-cpp-python psutil
python inference/test_inference.py
```

Results are written to `benchmarks/results.csv` and printed as a summary table.
