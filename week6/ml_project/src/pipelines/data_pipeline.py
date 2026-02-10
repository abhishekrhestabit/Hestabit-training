import pandas as pd
import numpy as np
import os

class DataPipeline:
    def __init__(self, raw_path, processed_path, drop_cols=None):
        """
        Initialize the pipeline with file paths and columns to drop.
        :param drop_cols: List of column names to remove (Generic)
        """
        self.raw_path = raw_path
        self.processed_path = processed_path
        self.data = None
        # Ensure drop_cols is a list, defaulting to empty if None
        self.drop_cols = drop_cols if drop_cols else []

    def load_data(self):
        """
        Step 1: Load dataset from /data/raw
        """
        if not os.path.exists(self.raw_path):
            raise FileNotFoundError(f"File not found at {self.raw_path}")
        
        self.data = pd.read_csv(self.raw_path)
        print(f"✅ Data loaded successfully. Shape: {self.data.shape}")
        return self.data

    def clean_data(self):
        """
        Step 2: Clean data (missing, duplicates, outliers, irrelevant columns)
        """
        if self.data is None:
            raise ValueError("Data not loaded. Call load_data() first.")

        # 1. Remove Duplicates (First pass to catch exact row duplicates)
        self.data.drop_duplicates(inplace=True)
        
        # 2. Drop Unneeded Columns (GENERIC LOGIC)
        # We use self.drop_cols which was passed during initialization
        if self.drop_cols:
            # Only drop columns that actually exist in the dataframe
            existing_cols_to_drop = [c for c in self.drop_cols if c in self.data.columns]
            
            if existing_cols_to_drop:
                self.data.drop(columns=existing_cols_to_drop, inplace=True)
                print(f"🗑️ Dropped columns: {existing_cols_to_drop}")
            else:
                print(f"⚠️ Warning: None of the columns in {self.drop_cols} were found in the dataset.")

        # 3. Handle Missing Values
        numeric_cols = self.data.select_dtypes(include=[np.number]).columns
        categorical_cols = self.data.select_dtypes(include=['object']).columns

        # Fill numeric with Median
        for col in numeric_cols:
            self.data[col] = self.data[col].fillna(self.data[col].median())
        
        # Fill categorical with Mode (Most Frequent)
        for col in categorical_cols:
            if not self.data[col].mode().empty:
                self.data[col] = self.data[col].fillna(self.data[col].mode()[0])

        print(f"✅ Data cleaned. Final Shape: {self.data.shape}")
        return self.data

    def save_data(self):
        """
        Step 3: Save to /data/processed/final.csv
        """
        if self.data is None:
            raise ValueError("Data is empty. Cannot save.")
            
        os.makedirs(os.path.dirname(self.processed_path), exist_ok=True)
        
        self.data.to_csv(self.processed_path, index=False)
        print(f"💾 Processed data saved to {self.processed_path}")

if __name__ == "__main__":
    # CONFIGURATION
    RAW_FILE = "data/raw/dataset.csv" 
    PROCESSED_FILE = "data/processed/final.csv"
    
    # --- HERE IS WHERE YOU DEFINE THE SPECIFICS ---
    # Since we are using Titanic right now, we pass the Titanic specific cols here.
    TITANIC_DROP_COLS = ['PassengerId', 'Name', 'Ticket', 'Cabin']

    pipeline = DataPipeline(RAW_FILE, PROCESSED_FILE, drop_cols=TITANIC_DROP_COLS)
    pipeline.load_data()
    pipeline.clean_data()
    pipeline.save_data()