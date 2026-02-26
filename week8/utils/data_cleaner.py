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
    print("1. Downloading Free Dataset...")
    # Dolly 15k is free and already has categories like QA, Extraction, and Brainstorming (Reasoning)
    dataset = load_dataset("databricks/databricks-dolly-15k", split="train")
    df = dataset.to_pandas()
    assert isinstance(df, pd.DataFrame)

    print("2. Filtering for Domain & Task Types...")
    # Filter for QA, Reasoning (brainstorming), and Extraction
    allowed_categories = ["open_qa", "closed_qa", "information_extraction", "brainstorming"]
    df = df[df['category'].isin(allowed_categories)]

    # Map Dolly categories to our required 3 types
    def map_type(cat):
        if "qa" in cat: return "QA"
        if cat == "information_extraction": return "Extraction"
        if cat == "brainstorming": return "Reasoning"
    
    df['type'] = df['category'].apply(map_type)

    # Filter for Tech/Coding domain using keywords across all text columns
    tech_keywords = [
        'software', 'code', 'python', 'computer', 'data', 'algorithm', 'web', 'network',
        'program', 'technology', 'tech', 'internet', 'database', 'server', 'api', 'function',
        'system', 'application', 'app', 'developer', 'programming', 'engineer', 'digital',
        'machine learning', 'artificial intelligence', 'model', 'neural', 'cloud', 'security',
        'hardware', 'linux', 'windows', 'git', 'framework', 'library', 'class', 'variable',
        'operating system', 'processor', 'memory', 'storage', 'binary', 'javascript', 'java',
        'sql', 'html', 'css', 'pipeline', 'deploy', 'container', 'docker', 'kubernetes',
        'encryption', 'firewall', 'bandwidth', 'protocol', 'compiler', 'debugging', 'runtime',
        'microservice', 'machine', 'robot', 'automation', 'script', 'repository', 'version',
        'CPU', 'GPU', 'RAM', 'virtual', 'device', 'mobile', 'open source', 'software engineer',
        'file', 'directory', 'command', 'terminal', 'bash', 'shell', 'regex', 'parse', 'format',
        'string', 'array', 'list', 'dictionary', 'object', 'method', 'interface', 'module',
        'import', 'library', 'package', 'install', 'error', 'exception', 'debug', 'test',
        'machine', 'compute', 'byte', 'bit', 'logic', 'sensor', 'chip', 'circuit', 'process'
    ]
    kw_pattern = '|'.join(tech_keywords)
    mask = (
        df['instruction'].str.contains(kw_pattern, case=False, na=False) |
        df['context'].str.contains(kw_pattern, case=False, na=False) |
        df['response'].str.contains(kw_pattern, case=False, na=False)
    )
    df = df[mask]

    # Cap per type to keep the dataset balanced (up to 600 each = 1,800 before outlier removal)
    df = df.groupby('type').head(600)

    # Rename columns to match the required JSONL format
    df = df[['instruction', 'context', 'response', 'type']]
    df.columns = ['instruction', 'input', 'output', 'type']

    print("3. Analyzing Token Lengths...")
    # Use a fast, free local tokenizer (GPT-2 is lightweight and downloads instantly)
    tokenizer = AutoTokenizer.from_pretrained("gpt2")
    
    def get_token_length(row):
        text = f"{row['instruction']} {row['input']} {row['output']}"
        return len(tokenizer.encode(text, truncation=False))

    df['token_length'] = df.apply(get_token_length, axis=1)

    print("4. Removing Outliers...")
    # Keep samples between 20 and 512 tokens (covers most instruction samples without truncation)
    initial_count = len(df)
    df = df[(df['token_length'] >= 20) & (df['token_length'] <= 512)]
    print(f"Removed {initial_count - len(df)} outliers. Total remaining: {len(df)}")

    print("5. Generating Distribution Graph...")
    plt.figure(figsize=(10, 6))
    plt.hist(df['token_length'], bins=50, color='skyblue', edgecolor='black')
    plt.title('Token Length Distribution (Cleaned Dataset)')
    plt.xlabel('Number of Tokens')
    plt.ylabel('Frequency')
    plt.grid(axis='y', alpha=0.75)
    graph_path = os.path.join(ROOT_DIR, 'token_distribution.png')
    plt.savefig(graph_path)
    print(f"Saved graph as {graph_path}")

    print("6. Splitting and Saving Deliverables...")
    # Shuffle the dataset
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    # 90% Train, 10% Validation
    split_index = int(len(df) * 0.9)
    train_df = df.iloc[:split_index]
    val_df = df.iloc[split_index:]

    # Save to JSONL
    def save_jsonl(dataframe, filepath):
        records = dataframe[['instruction', 'input', 'output']].to_dict(orient='records')
        with open(filepath, 'w') as f:
            for record in records:
                f.write(json.dumps(record) + '\n')

    os.makedirs(DATA_DIR, exist_ok=True)
    save_jsonl(train_df, os.path.join(DATA_DIR, 'train.jsonl'))
    save_jsonl(val_df, os.path.join(DATA_DIR, 'val.jsonl'))

    print(f"✅ Success! Saved {len(train_df)} train and {len(val_df)} val samples.")

if __name__ == "__main__":
    main()