import pandas as pd
import numpy as np
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder

class FeatureEngineer:
    def __init__(self, input_path, output_dir):
        self.input_path = input_path
        self.output_dir = output_dir
        self.df = None

    def load_data(self):
        self.df = pd.read_csv(self.input_path)
        print(f"✅ Loaded Data. Shape: {self.df.shape}")

    def create_features(self):
        """
        Generates 20+ features using Interactions and Polynomials.
        """
        # --- 1. Basic Family Features ---
        self.df['FamilySize'] = self.df['SibSp'] + self.df['Parch'] + 1
        self.df['IsAlone'] = (self.df['FamilySize'] == 1).astype(int)
        self.df['Is_Large_Family'] = (self.df['FamilySize'] > 4).astype(int)

        # --- 2. Fare Transformations ---
        self.df['Fare_Log'] = np.log1p(self.df['Fare'])
        self.df['Fare_Per_Person'] = self.df['Fare'] / self.df['FamilySize']

        # --- 3. Age Transformations ---
        self.df['Is_Child'] = (self.df['Age'] < 10).astype(int)
        self.df['Is_Senior'] = (self.df['Age'] > 60).astype(int)
        
        # --- 4. Interactions ---
        self.df['Age_Class'] = self.df['Age'] * self.df['Pclass']
        self.df['Age_Fare'] = self.df['Age'] * self.df['Fare_Log']

        # --- 5. Polynomials ---
        self.df['Age_Sq'] = self.df['Age'] ** 2
        self.df['Fare_Sq'] = self.df['Fare_Log'] ** 2
        
        print("✅ Feature Engineering Complete.")
        return self.df

    def encode_and_scale(self):
        """
        Uses sklearn OneHotEncoder instead of pd.get_dummies.
        """
        # 1. Identify Categorical & Numerical Columns
        # We explicitly cast Pclass to string so it gets encoded as a category
        self.df['Pclass'] = self.df['Pclass'].astype(str)
        
        cat_cols = ['Sex', 'Embarked', 'Pclass']
        num_cols = [c for c in self.df.columns if c not in cat_cols and c != 'Survived']

        # --- 2. ONE-HOT ENCODING (The Sklearn Way) ---
        # sparse_output=False gives us a dense array (easier to use)
        # handle_unknown='ignore' prevents crashes if new data has unknown categories
        encoder = OneHotEncoder(sparse_output=False, drop='first', handle_unknown='ignore')
        
        # Fit and Transform
        encoded_data = encoder.fit_transform(self.df[cat_cols])
        
        # Get the new column names (e.g., Sex_male, Embarked_Q)
        encoded_cols = encoder.get_feature_names_out(cat_cols)
        
        # Convert back to DataFrame
        encoded_df = pd.DataFrame(encoded_data, columns=encoded_cols, index=self.df.index)
        
        # --- 3. MERGE & CLEANUP ---
        # Drop old categorical columns and attach new one-hot columns
        self.df = self.df.drop(columns=cat_cols)
        self.df = pd.concat([self.df, encoded_df], axis=1)

        # --- 4. SCALING ---
        scaler = StandardScaler()
        # Scale only the numerical features (excluding the new binary one-hot cols if you prefer, 
        # but scaling everything is standard for SVM/Linear models)
        features_to_scale = num_cols + list(encoded_cols)
        
        self.df[features_to_scale] = scaler.fit_transform(self.df[features_to_scale])

        print(f"✅ Data Encoded (Sklearn) & Scaled. New Feature Count: {self.df.shape[1] - 1}")
        return self.df

    def save_split_data(self):
        target = 'Survived'
        X = self.df.drop(columns=[target])
        y = self.df[target]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        os.makedirs(self.output_dir, exist_ok=True)
        X_train.to_csv(f"{self.output_dir}/X_train.csv", index=False)
        X_test.to_csv(f"{self.output_dir}/X_test.csv", index=False)
        y_train.to_csv(f"{self.output_dir}/y_train.csv", index=False)
        y_test.to_csv(f"{self.output_dir}/y_test.csv", index=False)
        print(f"💾 Saved X_train with {X_train.shape[1]} columns.")

if __name__ == "__main__":
    INPUT_FILE = "src/data/processed/final.csv"
    OUTPUT_DIR = "src/data/features"

    engineer = FeatureEngineer(INPUT_FILE, OUTPUT_DIR)
    engineer.load_data()
    engineer.create_features()
    engineer.encode_and_scale()
    engineer.save_split_data()