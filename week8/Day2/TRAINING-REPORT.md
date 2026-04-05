# TRAINING-REPORT.md — Week 8 Day 2

> **Note**: Run `notebooks/lora_train_2.ipynb` on Google Colab (T4 GPU). Metrics will populate after training completes.

## Model
- **Base**: TinyLlama/TinyLlama-1.1B-Chat-v1.0
- **Method**: QLoRA (4-bit NF4 + LoRA)
- **Framework**: transformers + peft + bitsandbytes + accelerate
- **Trainer**: HuggingFace `Trainer` + `DataCollatorForLanguageModeling`

## LoRA Configuration
| Parameter | Value |
|-----------|-------|
| Rank (r) | 16 |
| Alpha | 32 |
| Dropout | 0.05 |
| Target Modules | q_proj, k_proj, v_proj, o_proj |
| Bias | none |
| Task Type | CAUSAL_LM |

## Quantization
| Parameter | Value |
|-----------|-------|
| Precision | 4-bit |
| Quant Type | NF4 |
| Compute Dtype | float16 |
| Double Quant | Yes |

## Training Configuration
| Parameter | Value |
|-----------|-------|
| Epochs | 3 |
| Batch Size | 4 |
| Gradient Accumulation | 1 |
| Effective Batch Size | 4 |
| Learning Rate | 2e-4 |
| Scheduler | Linear (default) |
| Optimizer | paged_adamw_8bit |
| Max Seq Length | 512 |
| FP16 | Yes |
| Gradient Checkpointing | Yes |
| Logging Steps | 50 |
| Save Steps | 200 |

## Prompt Format
Alpaca-style template:
```
### Instruction:
{instruction}

### Input:
{input}   ← omitted if empty

### Response:
{output}
```

## Dataset
| Split | Samples | Source |
|-------|---------|--------|
| Train | 1,451 | `/content/train.jsonl` |

## Trainable Parameters
- **Total**: ~1.1B
- **Trainable**: ~8.4M (q/k/v/o_proj only)
- **Trainable %**: ~0.77%

## Results
| Metric | Value |
|--------|-------|
| Final Train Loss | *(populated after training)* |
| Train Runtime (s) | *(populated after training)* |
| Samples/sec | *(populated after training)* |

## Adapter Output
- **Path**: `/content/adapters/`
- **Format**: PyTorch binary (`adapter_model.bin`) via `safe_serialization=False`
- **Files**: `adapter_model.bin`, `adapter_config.json`, `tokenizer.json`, `tokenizer_config.json`

## Loss Curve

![alt text](Day2/training_loss.png)

## Adapter Output
- `adapter_model.safetensors`
- `adapter_config.json`
