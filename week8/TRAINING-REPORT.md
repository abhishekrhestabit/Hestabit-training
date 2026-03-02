# TRAINING-REPORT.md — Week 8 Day 2

> **Note**: This is a template. Run `notebooks/lora_train.ipynb` on Google Colab — the final cell auto-generates this report with actual metrics and downloads it.

## Model
- **Base**: TinyLlama/TinyLlama-1.1B-Chat-v1.0
- **Method**: QLoRA (4-bit NF4 + LoRA)
- **Framework**: transformers + peft + trl + bitsandbytes

## LoRA Configuration
| Parameter | Value |
|-----------|-------|
| Rank (r) | 16 |
| Alpha | 32 |
| Dropout | 0.05 |
| Target Modules | q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj |
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
| Gradient Accumulation | 4 |
| Effective Batch Size | 16 |
| Learning Rate | 2e-4 |
| Scheduler | Cosine |
| Warmup Ratio | 0.03 |
| Optimizer | paged_adamw_32bit |
| Max Seq Length | 512 |
| FP16 | Yes |
| Gradient Checkpointing | Yes |

## Dataset
| Split | Samples |
|-------|---------|
| Train | 1,451 |
| Val | 162 |

## Trainable Parameters
- **Total**: ~1.1B
- **Trainable**: ~13.9M
- **Trainable %**: ~1.26%

## Results
| Metric | Value |
|--------|-------|
| Final Train Loss | *(populated after training)* |
| Eval Loss | *(populated after training)* |
| Train Runtime (s) | *(populated after training)* |
| Samples/sec | *(populated after training)* |

## Loss Curve
![Training Loss](training_loss.png)

## Adapter Output
- `adapter_model.safetensors`
- `adapter_config.json`
