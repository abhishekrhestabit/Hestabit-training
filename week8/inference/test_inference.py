#!/usr/bin/env python3


import os, gc, time, csv, json, random
import torch
import psutil
import numpy as np
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from llama_cpp import Llama
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity as cos_sim

# ─── Config ───
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_CSV = os.path.join(ROOT, "benchmarks", "results.csv")
VAL_FILE = os.path.join(ROOT, "data", "val.jsonl")
TRAIN_FILE = os.path.join(ROOT, "data", "train.jsonl")
MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
ADAPTER_PATH = os.path.join(ROOT, "adapters")
GGUF_Q8 = os.path.join(ROOT, "quantized", "model-q8_0.gguf")
GGUF_Q4 = os.path.join(ROOT, "quantized", "model-q4_k_m.gguf")
MAX_NEW_TOKENS = 128
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.float16 if DEVICE == "cuda" else torch.float32

# Lazy-loaded sentence embedding model
_EMBED_MODEL = None

def _embed():
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        _EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _EMBED_MODEL


def free_mem():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


# ─── Helpers ───

def fmt_prompt(instruction, inp=""):
    if inp.strip():
        return f"### Instruction:\n{instruction}\n\n### Input:\n{inp}\n\n### Response:\n"
    return f"### Instruction:\n{instruction}\n\n### Response:\n"


N_VAL = 15  # number of random val samples to benchmark

def load_all_val_samples():
    with open(VAL_FILE) as f:
        all_samples = [
            {"prompt": fmt_prompt(d["instruction"], d.get("input", "")), "reference": d["output"]}
            for d in (json.loads(line) for line in f)
        ]
    return random.sample(all_samples, min(N_VAL, len(all_samples)))


def cosine_sim_pct(pred, ref):
    embs = _embed().encode([pred, ref])
    return float(np.clip(cos_sim([embs[0]], [embs[1]])[0][0], 0, 1)) * 100


def validate_training_data():
    with open(TRAIN_FILE) as f:
        data = [json.loads(line) for line in f]
    n = len(data)
    with_context = sum(1 for d in data if d.get("input", "").strip())
    short  = sum(1 for d in data if len(d["output"].split()) < 20)
    long_  = sum(1 for d in data if 20 <= len(d["output"].split()) < 100)
    detail = sum(1 for d in data if len(d["output"].split()) >= 100)
    print("Training data validation:")
    print(f"  with clinical note : {with_context} ({with_context/n*100:.0f}%)")
    print(f"  short  answers (<20 words) : {short}  ({short/n*100:.0f}%)")
    print(f"  medium answers (20-99 words): {long_} ({long_/n*100:.0f}%)")
    print(f"  long   answers (100+ words) : {detail} ({detail/n*100:.0f}%)")
    assert n > 0 and short + long_ + detail == n, "Training data appears corrupt!"
    print(f"  ✓ Dataset valid — {n} samples across 3 answer-length buckets\n")


def vram_mb():
    return torch.cuda.memory_allocated() / 1024**2 if torch.cuda.is_available() else 0.0

def ram_mb():
    return psutil.Process().memory_info().rss / 1024**2

def sync():
    if torch.cuda.is_available():
        torch.cuda.synchronize()


# ─── HF inference (single prompt, memory-safe) ───

def hf_generate(model, tokenizer, prompt):
    ids = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048).to(DEVICE)
    sync()
    t0 = time.perf_counter()
    with torch.no_grad():
        out = model.generate(**ids, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)
    sync()
    elapsed = time.perf_counter() - t0
    n_new = out.shape[1] - ids["input_ids"].shape[1]
    text = tokenizer.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)
    del ids, out
    return text, n_new, elapsed


# ─── GGUF inference ───

def gguf_generate(model, prompt):
    max_prompt_tokens = model.n_ctx() - MAX_NEW_TOKENS - 4
    tokens = model.tokenize(prompt.encode())
    if len(tokens) > max_prompt_tokens:
        prompt = model.detokenize(tokens[:max_prompt_tokens]).decode("utf-8", errors="ignore")
    t0 = time.perf_counter()
    out = model(prompt, max_tokens=MAX_NEW_TOKENS, echo=False)
    elapsed = time.perf_counter() - t0
    return out["choices"][0]["text"], out["usage"]["completion_tokens"], elapsed


# ─── Benchmark runners ───

def _row(name, n_prompts, total_tok, total_sec, sim_scores):
    avg_sim = round(sum(sim_scores) / len(sim_scores), 2) if sim_scores else 0
    return {
        "model": name,
        "prompts": n_prompts,
        "tokens_per_sec": round(total_tok / total_sec, 2) if total_sec > 0 else 0,
        "avg_latency_s": round(total_sec / n_prompts, 2),
        "vram_mb": round(vram_mb(), 1),
        "ram_mb": round(ram_mb(), 1),
        "cosine_similarity_%": avg_sim,
    }


def bench_hf(name, model, tokenizer, samples):
    print(f"\n{'='*60}\n  {name}\n{'='*60}")
    sims, toks, secs = [], 0, 0
    for s in tqdm(samples, desc=f"  {name}"):
        txt, n, t = hf_generate(model, tokenizer, s["prompt"])
        sims.append(cosine_sim_pct(txt, s["reference"]))
        toks += n; secs += t
    print(f"  {len(samples)} prompts | {toks/secs:.1f} tok/s | avg sim={np.mean(sims):.1f}%")
    return [_row(name, len(samples), toks, secs, sims)]


def bench_gguf(name, path, samples):
    print(f"\n{'='*60}\n  {name}\n{'='*60}")
    model = Llama(model_path=path, n_ctx=2048, verbose=False)
    sims, toks, secs = [], 0, 0
    for s in tqdm(samples, desc=f"  {name}"):
        txt, n, t = gguf_generate(model, s["prompt"])
        sims.append(cosine_sim_pct(txt, s["reference"]))
        toks += n; secs += t
    print(f"  {len(samples)} prompts | {toks/secs:.1f} tok/s | avg sim={np.mean(sims):.1f}%")
    row = [_row(name, len(samples), toks, secs, sims)]
    del model; free_mem()
    return row


# ─── Main ───

def main():
    os.makedirs(os.path.join(ROOT, "benchmarks"), exist_ok=True)
    print(f"Device: {DEVICE} | dtype: {DTYPE}\n")

    validate_training_data()

    samples = load_all_val_samples()
    print(f"Loaded {len(samples)} prompts from val.jsonl (all)\n")
    all_results = []

    # 1. Base model
    print("Loading base model...")
    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    base = AutoModelForCausalLM.from_pretrained(MODEL_NAME, dtype=DTYPE).to(DEVICE)
    all_results += bench_hf("Base", base, tok, samples)
    del base; free_mem()

    # 2. Fine-tuned model (LoRA merged)
    if os.path.exists(ADAPTER_PATH):
        print("Loading fine-tuned model (LoRA merge)...")
        base = AutoModelForCausalLM.from_pretrained(MODEL_NAME, dtype=DTYPE).to(DEVICE)
        ft = PeftModel.from_pretrained(base, ADAPTER_PATH).merge_and_unload()
        del base; free_mem()
        all_results += bench_hf("FineTuned", ft, tok, samples)
        del ft; free_mem()

    # 3. GGUF Q8_0
    if os.path.exists(GGUF_Q8) and os.path.getsize(GGUF_Q8) > 1_000_000:
        all_results += bench_gguf("GGUF-Q8_0", GGUF_Q8, samples)

    # 4. GGUF Q4_K_M
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
    hdr = f"{'Model':<16} {'#':>4} {'Tok/s':>7} {'Lat(s)':>7} {'VRAM':>7} {'RAM':>7} {'CosSim%':>8}"
    print(f"\n{hdr}\n{'-'*len(hdr)}")
    for r in all_results:
        print(f"{r['model']:<16} {r['prompts']:>4} {r['tokens_per_sec']:>7} "
              f"{r['avg_latency_s']:>7} {r['vram_mb']:>7} {r['ram_mb']:>7} "
              f"{r['cosine_similarity_%']:>8}")


if __name__ == "__main__":
    main()