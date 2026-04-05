# DATASET-ANALYSIS.md — Week 8 Day 1

## Source

The dataset used is **Databricks Dolly 15k**, an open-source instruction-following dataset containing 15,011 human-generated prompt-response pairs across multiple task categories. It is freely available on the Hugging Face Hub under the `databricks/databricks-dolly-15k` identifier and requires no authentication to download.

## Domain

The domain selected for this project is **Tech / Coding / Software Engineering**. Samples were filtered by matching a broad set of domain-relevant keywords (such as `python`, `algorithm`, `database`, `API`, `machine learning`, `docker`, `compiler`, `debugging`, and others) across all three text fields — instruction, context, and response — to maximise recall while staying within the domain.

## Task Types

Three task types are required by the curriculum: QA, Reasoning, and Extraction. Dolly 15k provides native category labels that map directly to these:

- **QA** — sourced from `open_qa` and `closed_qa` categories, covering factual and context-grounded question answering.
- **Reasoning** — sourced from `brainstorming`, which requires the model to generate ideas, explain concepts, or think through problems.
- **Extraction** — sourced from `information_extraction`, where the model must identify and retrieve specific facts from a given context.

## Data Cleaning Pipeline

After downloading the full dataset, samples were restricted to the four relevant Dolly categories. The domain keyword filter was then applied across all text columns to retain only tech-relevant samples. Each type was capped at 600 samples to prevent class imbalance.

Token lengths were computed using the GPT-2 tokenizer by concatenating the instruction, input, and output fields for each sample. GPT-2 was chosen because it is lightweight, runs fully locally without authentication, and provides a reliable approximation of subword token counts. Samples with fewer than 20 tokens (too short to be meaningful) or more than 512 tokens (likely to cause truncation during fine-tuning) were removed as outliers.

The cleaned dataset was shuffled with a fixed random seed (42) for reproducibility and split 90/10 into train and validation sets.

## Final Statistics

After the full pipeline, 1,613 samples remained from an initial pool of approximately 1,800 pre-filter candidates. 187 samples were discarded as outliers. The train set contains 1,451 samples and the validation set contains 162 samples. Token lengths across the retained samples range from 20 to 512, with the majority of samples concentrated in the 50–250 token range.

## Output Format

Each sample is saved in JSONL format with three fields:

- `instruction` — the task or question posed to the model
- `input` — optional context provided alongside the instruction (empty string if none)
- `output` — the expected model response

Train and validation splits are saved to `data/train.jsonl` and `data/val.jsonl` respectively.
