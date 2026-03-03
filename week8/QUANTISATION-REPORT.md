# QUANTISATION-REPORT — Week 8 Day 3

## 1. What is Post-Training Quantisation?

Quantisation reduces the numerical precision of a model's weights after training is complete. A standard transformer stores each weight as a 16-bit float (FP16), consuming 2 bytes per parameter. Quantisation maps those values into lower-bit integer representations such as INT8 or INT4, shrinking memory footprint and accelerating matrix multiplications at the cost of a small, bounded accuracy loss.

Formally, a quantised weight $\hat{w}$ is obtained from the original weight $w$ via:

$$\hat{w} = \text{round}\!\left(\frac{w}{s}\right) \cdot s, \quad s = \frac{\max(|w|)}{2^{b-1} - 1}$$

where $s$ is the scale factor and $b$ is the target bit-width. The reconstruction error $\|w - \hat{w}\|$ grows as $b$ decreases, which is the fundamental accuracy–compression trade-off.

---

## 2. Static vs Dynamic Quantisation

There are three main quantisation strategies. Static quantisation computes the scale factor once from a calibration dataset before inference begins; it offers the highest throughput but requires representative data. Dynamic quantisation computes the scale per batch at inference time, needing no calibration but adding a small runtime overhead. Weight-only quantisation, which is most common for LLMs, quantises only the stored weight tensors statically while leaving activations in FP16 throughout inference. All four formats produced in this project use weight-only quantisation, which is why no calibration corpus is needed and why the output distribution remains close to the FP16 baseline.

---

## 3. FP16 → INT8 → INT4 Precision Spectrum

FP16 stores each weight as a 16-bit floating-point value (range ±65504), costing 2 bytes per parameter. INT8 uses 8 bits with a range of −128 to 127, halving memory to 1 byte per parameter with near-lossless quality. INT4 uses only 4 bits with a range of −8 to 7, reducing memory to 0.5 bytes per parameter and introducing a small but measurable quality drop. NF4 (Normal Float 4) is a special 4-bit variant used by BitsAndBytes that spaces its 16 quantisation levels non-uniformly according to the normal distribution. Because transformer weights are empirically approximately normally distributed ($w \sim \mathcal{N}(0, \sigma^2)$), NF4 is information-theoretically optimal for this data — a uniform INT4 grid would waste codebook capacity on extreme values that almost never occur.

---

## 4. Model and Preparation

The base model is TinyLlama/TinyLlama-1.1B-Chat-v1.0. Before any quantisation could be applied, the Day 2 LoRA adapter was merged back into the base weights using `PeftModel.merge_and_unload()`. This absorbs the low-rank update matrices $\Delta W = BA$ into the frozen weights $W_0$, producing a single dense FP16 model of approximately 2.2 GB with no PEFT overhead. Quantising a PEFT model without merging would compress the frozen base while leaving the adapter matrices in FP16, producing an inconsistent mixed-precision artefact with artificially inflated memory usage.

The merged FP16 model was then used as the common starting point for all four quantisation paths: BitsAndBytes INT8, BitsAndBytes INT4 NF4, GGUF Q8_0 via llama.cpp, and GGUF Q4_K_M via llama.cpp.

---

## 5. Quantisation Methods Applied

### 5.1 BitsAndBytes INT8 — LLM.int8()

The `bitsandbytes` LLM.int8() method uses mixed-precision decomposition rather than naive INT8 rounding. It first identifies the small subset of weight columns with unusually large magnitudes — so-called outlier features, which constitute roughly 0.1% of dimensions but cause catastrophic accuracy loss if quantised uniformly. Those columns are retained in FP16. The remaining ~99.9% of weights are quantised to INT8 using per-column absmax scaling. The result is a model that occupies 1.2 GB on disk (a 45% reduction versus FP16) with a perplexity increase typically below 0.5 points on standard benchmarks.

### 5.2 BitsAndBytes INT4 — NF4 with Double Quantisation

4-bit NF4 quantisation stores each weight in half a byte using a non-uniform normal-float codebook. The weight matrix is divided into blocks of 64 elements. Each block receives its own FP32 scale factor computed via absmax, and all values in the block are mapped to one of the 16 NF4 levels. Double quantisation then applies a second round of compression to the scale factors themselves: the FP32 scales are quantised to 8-bit, reducing scale overhead from 32 bits per block to 8 bits per block and saving approximately 0.5 additional bits per weight on average. The final model size is 771 MB (a 65% reduction), with a perplexity increase of roughly 1–3 points depending on model size and domain.

### 5.3 GGUF Q8_0

GGUF (GPT-Generated Unified Format) is the serialisation format used by llama.cpp, Ollama, and LM Studio. Before GGUF quantisation, the merged HuggingFace model was converted to an FP16 GGUF file using `convert_hf_to_gguf.py` from the llama.cpp repository, then compressed with the `llama-quantize` binary built via CMake.

Q8_0 is an 8-bit symmetric per-block scheme. The weight matrix is divided into blocks of 32 values. Each block receives one FP32 scale computed as $s = \max(|w_\text{block}|) / 127$, and each weight is rounded to the nearest INT8 via $q = \text{round}(w / s)$. Q8_0 is nearly lossless, producing a 1.1 GB file (50% reduction) that serves as the highest-fidelity GGUF format.

### 5.4 GGUF Q4_K_M

Q4_K_M is a k-quant: a mixed-precision scheme that allocates different bit-widths to different tensor types based on their measured sensitivity to quantisation error. Attention output projection and feed-forward down-projection weights — the layers most sensitive to rounding error — receive Q6_K (6-bit) quantisation. All other weight tensors receive Q4_K (4-bit) quantisation. The "K" suffix indicates that the per-block scale factors are themselves quantised to 6 bits rather than stored as full FP32 values, reducing the scale overhead further. The block size is 256 weights, and the effective average bit-width across the model is approximately 4.5 bits per weight. The resulting file is 637 MB, a 71% reduction from FP16, and represents the best quality-per-megabyte ratio for CPU-based deployment via `llama.cpp` or `llama-cpp-python`.

---

## 6. Memory vs Accuracy Trade-off

The core tension in quantisation is that each halving of bit-width doubles compression and speeds up arithmetic but increases the quantisation error and therefore the perplexity of the model. Moving from FP16 to INT8 is nearly free in quality terms because the mixed-precision outlier handling in LLM.int8() absorbs almost all the error. Moving from INT8 to INT4 introduces a more noticeable but still acceptable degradation for most practical applications. Going below 4 bits — to 2-bit or 1-bit — causes quality to collapse sharply for models at the 1B parameter scale because there is insufficient parameter redundancy to absorb the error. For larger models (7B and above) the threshold shifts: INT4 is well-tolerated and even 3-bit formats remain usable. At TinyLlama's 1.1B scale, INT4 and Q4_K_M represent the practical compression floor without additional calibration-based techniques such as GPTQ or AWQ.

---

## 7. Deliverables

Four quantised models were produced and saved locally. The HuggingFace INT8 model is saved at `quantized/model-int8/` and occupies 1.2 GB. The HuggingFace INT4 NF4 model is saved at `quantized/model-int4/` and occupies 771 MB. The GGUF Q8_0 model is saved at `quantized/model-q8_0.gguf` and occupies 1.1 GB. The GGUF Q4_K_M model is saved at `quantized/model-q4_k_m.gguf` and occupies 637 MB. The full pipeline is documented in `notebooks/quantization.ipynb`. Large binary model files are excluded from Git version control; run the notebook on Colab with a T4 GPU to regenerate all outputs.

---

## 8. Key Takeaways

Weight-only quantisation is the correct approach for LLMs because it requires no calibration data, is straightforward to apply at load time, and preserves the FP16 activation distribution that the model was trained with. NF4 is theoretically superior to uniform INT4 for transformer weights precisely because the normal distribution is a good prior for those weights — non-uniform spacing concentrates precision where the probability mass actually lies. GGUF Q4_K_M achieves the best quality-per-megabyte ratio by selectively protecting the most sensitive layers with higher precision rather than applying a single fixed bit-width globally. Merging the LoRA adapter before quantisation is not optional — it ensures the fine-tuned behaviour is baked into the base weights and compressed uniformly, rather than leaving a FP16 adapter sitting on top of an INT4 base. At 1.1B parameters, INT4 is the practical floor below which coherence degrades without specialised calibrated quantisation methods.
