import os
import pandas as pd
import json
import matplotlib.pyplot as plt
from datasets import load_dataset
from transformers import AutoTokenizer

# Paths relative to the script file so they work regardless of cwd
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(ROOT_DIR, 'data')

def main():
    print("1. Downloading Asclepius Medical Dataset...")
    # Load the full dataset so we can filter it properly
    dataset = load_dataset("starmpcc/Asclepius-Synthetic-Clinical-Notes", split="train")
    df = dataset.to_pandas()
    assert isinstance(df, pd.DataFrame)

    print("2. Filtering for QA, Reasoning, and Extraction...")
    # Swapped to 'Relation Extraction' since it actually exists in Asclepius!
    allowed_tasks = ["Question Answering", "Named Entity Recognition", "Relation Extraction"]
    df = df[df['task'].isin(allowed_tasks)]

    # Map the official task names to your required Day 1 types
    def map_task(task_name):
        if task_name == "Question Answering": return "QA"
        if task_name == "Named Entity Recognition": return "Extraction"
        if task_name == "Relation Extraction": return "Reasoning"
        
    df['type'] = df['task'].apply(map_task)

    # Balance the dataset (600 of each type = 1,800 total samples)
    df = df.groupby('type').head(600)

    # Map Asclepius columns to the exact Day 1 JSONL format requirements
    df = df[['question', 'note', 'answer', 'type']]
    df.columns = ['instruction', 'input', 'output', 'type']

    print("3. Analyzing Token Lengths...")
    tokenizer = AutoTokenizer.from_pretrained("TinyLlama/TinyLlama-1.1B-Chat-v1.0")
    
    def get_token_length(row):
        text = f"{row['instruction']} {row['input']} {row['output']}"
        return len(tokenizer.encode(text, truncation=False))

    df['token_length'] = df.apply(get_token_length, axis=1)

    print("4. Removing Outliers...")
    initial_count = len(df)
    df = df[(df['token_length'] >= 20) & (df['token_length'] <= 1024)]
    print(f"Removed {initial_count - len(df)} outliers. Total remaining: {len(df)}")

    print("5. Generating Distribution Graph...")
    plt.figure(figsize=(10, 6))
    plt.hist(df['token_length'], bins=50, color='lightcoral', edgecolor='black')
    plt.title('Token Length Distribution (Asclepius Medical Dataset)')
    plt.xlabel('Number of Tokens')
    plt.ylabel('Frequency')
    plt.grid(axis='y', alpha=0.75)
    graph_path = os.path.join(ROOT_DIR, 'token_distribution.png')
    plt.savefig(graph_path)
    print(f"Saved graph as {graph_path}")

    print("6. Splitting and Saving Deliverables...")
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    # We will do an 85/15 split on our ~1,800 samples
    split_index = int(len(df) * 0.85)
    train_df = df.iloc[:split_index]
    val_df = df.iloc[split_index:]

    # Save to JSONL keeping ONLY the three required keys
    def save_jsonl(dataframe, filepath):
        records = dataframe[['instruction', 'input', 'output']].to_dict(orient='records')
        with open(filepath, 'w', encoding='utf-8') as f:
            for record in records:
                f.write(json.dumps(record) + '\n')

    os.makedirs(DATA_DIR, exist_ok=True)
    save_jsonl(train_df, os.path.join(DATA_DIR, 'train.jsonl'))
    save_jsonl(val_df, os.path.join(DATA_DIR, 'val.jsonl'))

    print(f"Success! Saved {len(train_df)} train and {len(val_df)} val samples.")

if __name__ == "__main__":
    main()