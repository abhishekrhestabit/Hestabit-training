#!/usr/bin/env python3
"""Day 4 — Inference Optimisation & Benchmarking for TinyLlama fine-tuned models.
Run on Colab (T4 GPU) or locally with appropriate packages installed.
Outputs: benchmarks/results.csv + console summary table.
"""

import os, sys, time, csv, json, random
import torch  # type: ignore
import psutil  # type: ignore
from transformers import AutoModelForCausalLM, AutoTokenizer, TextStreamer  # type: ignore
from peft import PeftModel  # type: ignore
from llama_cpp import Llama  # type: ignore

# ─── Config ───
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_CSV = os.path.join(ROOT, "benchmarks", "results.csv")
VAL_FILE = os.path.join(ROOT, "data", "val.jsonl")
MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
ADAPTER_PATH = os.path.join(ROOT, "adapters")
GGUF_Q8 = os.path.join(ROOT, "quantized", "model-q8_0.gguf")
GGUF_Q4 = os.path.join(ROOT, "quantized", "model-q4_k_m.gguf")
MAX_NEW_TOKENS = 128

N_PROMPTS = 5  # number of val samples to test


# ─── Helpers ───

def fmt_prompt(instruction, inp=""):
    """Alpaca-style prompt template."""
    if inp.strip():
        return f"### Instruction:\n{instruction}\n\n### Input:\n{inp}\n\n### Response:\n"
    return f"### Instruction:\n{instruction}\n\n### Response:\n"


def load_val_samples(n=5):
    """Load n random samples from val.jsonl with prompts and reference outputs."""
    all_lines = open(VAL_FILE).readlines()
    selected = random.sample(all_lines, min(n, len(all_lines)))
    return [
        {"prompt": fmt_prompt(d["instruction"], d.get("input", "")), "reference": d["output"]}
        for d in (json.loads(l) for l in selected)
    ]


def word_f1(pred, ref):
    """Word-overlap F1 between prediction and reference."""
    pred_toks = set(pred.lower().split())
    ref_toks = set(ref.lower().split())
    if not pred_toks or not ref_toks:
        return 0.0
    common = pred_toks & ref_toks
    if not common:
        return 0.0
    p = len(common) / len(pred_toks)
    r = len(common) / len(ref_toks)
    return 2 * p * r / (p + r)


def vram_mb():
    """Current GPU VRAM allocated in MB."""
    return torch.cuda.memory_allocated() / 1024**2 if torch.cuda.is_available() else 0.0


def ram_mb():
    """Current process RSS in MB."""
    return psutil.Process().memory_info().rss / 1024**2


def sync_cuda():
    """Synchronize CUDA if available."""
    if torch.cuda.is_available():
        torch.cuda.synchronize()


# ─── HuggingFace inference ───

def hf_generate(model, tokenizer, prompt):
    """Single-prompt generation. Returns (text, n_tokens, elapsed_s)."""
    ids = tokenizer(prompt, return_tensors="pt").to(model.device)
    sync_cuda()
    t0 = time.perf_counter()
    with torch.no_grad():
        out = model.generate(**ids, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)
    sync_cuda()
    elapsed = time.perf_counter() - t0
    n_new = out.shape[1] - ids["input_ids"].shape[1]
    text = tokenizer.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)
    return text, n_new, elapsed


def hf_batch_generate(model, tokenizer, samples):
    """Batched generation. Returns (texts, total_new_tokens, elapsed_s)."""
    tokenizer.pad_token = tokenizer.eos_token
    prompts = [s["prompt"] for s in samples]
    ids = tokenizer(prompts, return_tensors="pt", padding=True, truncation=True).to(model.device)
    input_len = ids["input_ids"].shape[1]
    sync_cuda()
    t0 = time.perf_counter()
    with torch.no_grad():
        out = model.generate(**ids, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)
    sync_cuda()
    elapsed = time.perf_counter() - t0
    texts = [tokenizer.decode(o[input_len:], skip_special_tokens=True) for o in out]
    total = sum(len(o) - input_len for o in out)
    return texts, total, elapsed


def hf_stream(model, tokenizer, prompt):
    """Streaming token output demo. Returns (n_tokens, elapsed_s)."""
    ids = tokenizer(prompt, return_tensors="pt").to(model.device)
    streamer = TextStreamer(tokenizer, skip_special_tokens=True)
    print("\n--- Streaming ---")
    t0 = time.perf_counter()
    with torch.no_grad():
        out = model.generate(**ids, max_new_tokens=MAX_NEW_TOKENS, do_sample=False, streamer=streamer)
    elapsed = time.perf_counter() - t0
    n_new = out.shape[1] - ids["input_ids"].shape[1]
    print(f"--- {n_new} tokens in {elapsed:.2f}s ---\n")
    return n_new, elapsed


# ─── GGUF / llama-cpp inference ───

def gguf_generate(model, prompt):
    """Single-prompt GGUF generation. Returns (text, n_tokens, elapsed_s)."""
    # Truncate prompt to leave room for generated tokens within context window
    max_prompt_tokens = model.n_ctx() - MAX_NEW_TOKENS - 4
    tokens = model.tokenize(prompt.encode())
    if len(tokens) > max_prompt_tokens:
        prompt = model.detokenize(tokens[:max_prompt_tokens]).decode("utf-8", errors="ignore")
    t0 = time.perf_counter()
    out = model(prompt, max_tokens=MAX_NEW_TOKENS, echo=False)
    elapsed = time.perf_counter() - t0
    return out["choices"][0]["text"], out["usage"]["completion_tokens"], elapsed


def gguf_stream(model, prompt):
    """Streaming GGUF output. Returns (n_tokens, elapsed_s)."""
    print("\n--- Streaming (GGUF) ---")
    t0 = time.perf_counter()
    n = 0
    for chunk in model(prompt, max_tokens=MAX_NEW_TOKENS, echo=False, stream=True):
        print(chunk["choices"][0]["text"], end="", flush=True)
        n += 1
    elapsed = time.perf_counter() - t0
    print(f"\n--- {n} tokens in {elapsed:.2f}s ---\n")
    return n, elapsed


# ─── Benchmark runners ───

def bench_hf(name, model, tokenizer, samples):
    """Full HF benchmark: single, batch, stream + accuracy. Returns list of result dicts."""
    print(f"\n{'='*60}\n  {name}\n{'='*60}")
    rows, f1_scores = [], []
    prompts = [s["prompt"] for s in samples]

    # Single-prompt inference with accuracy
    toks, secs = 0, 0
    for s in samples:
        txt, n, t = hf_generate(model, tokenizer, s["prompt"])
        f1 = word_f1(txt, s["reference"])
        f1_scores.append(f1)
        toks += n; secs += t
        print(f"  [{n:3d} tok / {t:.2f}s / F1={f1:.2f}] {s['prompt'].split(chr(10))[1][:50]}...")
    rows.append(_row(name, "single", len(samples), toks, secs, f1_scores))

    # Batch inference with accuracy
    texts, bt, bs = hf_batch_generate(model, tokenizer, samples)
    batch_f1 = [word_f1(t, s["reference"]) for t, s in zip(texts, samples)]
    print(f"  Batch: {bt} tokens in {bs:.2f}s ({bt/bs:.1f} tok/s) avg F1={sum(batch_f1)/len(batch_f1):.2f}")
    rows.append(_row(name, "batch", len(samples), bt, bs, batch_f1))

    # Streaming demo (first prompt)
    hf_stream(model, tokenizer, prompts[0])
    return rows


def bench_gguf(name, path, samples):
    """Full GGUF benchmark: single + stream + accuracy. Returns list of result dicts."""
    print(f"\n{'='*60}\n  {name}\n{'='*60}")

    model = Llama(model_path=path, n_ctx=2048, verbose=False)
    rows, f1_scores = [], []

    toks, secs = 0, 0
    for s in samples:
        txt, n, t = gguf_generate(model, s["prompt"])
        f1 = word_f1(txt, s["reference"])
        f1_scores.append(f1)
        toks += n; secs += t
        print(f"  [{n:3d} tok / {t:.2f}s / F1={f1:.2f}] {s['prompt'].split(chr(10))[1][:50]}...")
    rows.append(_row(name, "single", len(samples), toks, secs, f1_scores))

    # Streaming demo
    gguf_stream(model, samples[0]["prompt"])
    del model
    return rows


def _row(name, mode, n_prompts, total_tok, total_sec, f1_scores=None):
    """Build a result row dict."""
    avg_f1 = round(sum(f1_scores) / len(f1_scores), 3) if f1_scores else ""
    return {
        "model": name,
        "mode": mode,
        "prompts": n_prompts,
        "total_tokens": total_tok,
        "total_time_s": round(total_sec, 2),
        "tokens_per_sec": round(total_tok / total_sec, 2) if total_sec > 0 else 0,
        "avg_latency_s": round(total_sec / n_prompts, 2),
        "vram_mb": round(vram_mb(), 1),
        "ram_mb": round(ram_mb(), 1),
        "avg_f1": avg_f1,
    }


# ─── Main ───

def main():
    os.makedirs(os.path.join(ROOT, "benchmarks"), exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}\n")

    samples = load_val_samples(N_PROMPTS)
    print(f"Loaded {len(samples)} prompts from val.jsonl\n")
    all_results = []

    # 1. Base model (FP16)
    print("Loading base model (FP16)...")
    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    base = AutoModelForCausalLM.from_pretrained(MODEL_NAME, torch_dtype=torch.float16, device_map="auto")
    all_results += bench_hf("Base-FP16", base, tok, samples)
    del base; torch.cuda.empty_cache()

    # 2. Fine-tuned model (LoRA merged)
    if os.path.exists(ADAPTER_PATH):
        print("Loading fine-tuned model (LoRA merge)...")
        base = AutoModelForCausalLM.from_pretrained(MODEL_NAME, torch_dtype=torch.float16, device_map="auto")
        ft = PeftModel.from_pretrained(base, ADAPTER_PATH).merge_and_unload()
        all_results += bench_hf("FineTuned-FP16", ft, tok, samples)
        del ft; torch.cuda.empty_cache()

    # 3. GGUF Q8_0 (llama.cpp)
    if os.path.exists(GGUF_Q8) and os.path.getsize(GGUF_Q8) > 1_000_000:
        all_results += bench_gguf("GGUF-Q8_0", GGUF_Q8, samples)

    # 4. GGUF Q4_K_M (llama.cpp)
    if os.path.exists(GGUF_Q4) and os.path.getsize(GGUF_Q4) > 1_000_000:
        all_results += bench_gguf("GGUF-Q4_K_M", GGUF_Q4, samples)

    # Save CSV
    if all_results:
        with open(RESULTS_CSV, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=all_results[0].keys())
            w.writeheader()
            w.writerows(all_results)
        print(f"\nResults saved to {RESULTS_CSV}")

    # Summary table
    print(f"\n{'Model':<18} {'Mode':<7} {'Tok/s':>7} {'Latency':>8} {'VRAM':>7} {'RAM':>7} {'F1':>6}")
    print("-" * 68)
    for r in all_results:
        f1 = r['avg_f1'] if r['avg_f1'] != '' else 'N/A'
        print(f"{r['model']:<18} {r['mode']:<7} {r['tokens_per_sec']:>7} {r['avg_latency_s']:>8} {r['vram_mb']:>7} {r['ram_mb']:>7} {f1:>6}")


if __name__ == "__main__":
    main()
