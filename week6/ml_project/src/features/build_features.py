import pandas as pd
import numpy as np
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

class FeatureEngineer:
    def __init__(self, input_path, output_dir):
        self.input_path = input_path
        self.output_dir = output_dir
        self.df = None

    def load_data(self):
        # Load the clean data from Day 1
        self.df = pd.read_csv(self.input_path)
        print(f"✅ Loaded Data. Shape: {self.df.shape}")

    def create_features(self):
        """
        Create domain-specific features.
        """
        # 1. FamilySize: Combine Siblings + Parents + Self
        if 'SibSp' in self.df.columns and 'Parch' in self.df.columns:
            self.df['FamilySize'] = self.df['SibSp'] + self.df['Parch'] + 1
            
        # 2. IsAlone: Binary flag (1 if alone, 0 if with family)
        if 'FamilySize' in self.df.columns:
            self.df['IsAlone'] = (self.df['FamilySize'] == 1).astype(int)

        # 3. Log Transform Fare: Fix skewness (handle log(0) by adding +1)
        if 'Fare' in self.df.columns:
            self.df['Fare_Log'] = np.log1p(self.df['Fare']) 
            # Drop original skewed column to avoid multicollinearity
            self.df.drop(columns=['Fare'], inplace=True) 

        print("✅ New Features Created: FamilySize, IsAlone, Fare_Log")
        return self.df

    def encode_and_scale(self):
        """
        1. One-Hot Encode Categorical Vars
        2. Scale Numerical Vars
        """
        # --- A. Encoding (Categorical -> Numbers) ---
        # Get all categorical columns automatically
        cat_cols = self.df.select_dtypes(include=['object']).columns
        
        # One-Hot Encoding (drop_first=True avoids dummy variable trap)
        self.df = pd.get_dummies(self.df, columns=cat_cols, drop_first=True)
        
        # Force Booleans (True/False) to 1/0
        bool_cols = self.df.select_dtypes(include=['bool']).columns
        self.df[bool_cols] = self.df[bool_cols].astype(int)

        # --- B. Scaling (Numbers -> Z-Scores) ---
        # Identify columns to scale (all remaining numeric columns except target)
        target = 'Survived' 
        features_to_scale = [c for c in self.df.columns if c != target]
        
        # NOTE: In production, we fit scaler on TRAIN and transform TEST.
        # For this specific script, we apply it globally for simplicity before splitting.
        # (Day 3 will cover pipelines which is the "Strict" way).
        scaler = StandardScaler()
        self.df[features_to_scale] = scaler.fit_transform(self.df[features_to_scale])

        print(f"✅ Data Encoded & Scaled. New Shape: {self.df.shape}")
        return self.df

    def save_split_data(self):
        """
        Save X_train, X_test, y_train, y_test
        """
        target = 'Survived'
        
        # Separate Features (X) and Target (y)
        X = self.df.drop(columns=[target])
        y = self.df[target]

        # Split 80/20
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Save to disk
        os.makedirs(self.output_dir, exist_ok=True)
        X_train.to_csv(f"{self.output_dir}/X_train.csv", index=False)
        X_test.to_csv(f"{self.output_dir}/X_test.csv", index=False)
        y_train.to_csv(f"{self.output_dir}/y_train.csv", index=False)
        y_test.to_csv(f"{self.output_dir}/y_test.csv", index=False)

        print(f"💾 Files saved to {self.output_dir}")

if __name__ == "__main__":
   
    INPUT_FILE = "src/data/processed/final.csv"
    OUTPUT_DIR = "src/data/processed" 
    engineer = FeatureEngineer(INPUT_FILE, OUTPUT_DIR)
    engineer.load_data()
    engineer.create_features()
    engineer.encode_and_scale()
    engineer.save_split_data()