import pandas as pd
import numpy as np
import os
import joblib  # <--- NEW: Required for saving artifacts
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder

class FeatureEngineer:
    def __init__(self, input_path, output_dir, model_dir="src/models"):
        self.input_path = input_path
        self.output_dir = output_dir
        self.model_dir = model_dir  # <--- NEW: Where to save scaler/encoder
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
        # log1p handles Fare=0 gracefully
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
        Encodes categoricals and Scales numericals.
        SAVES the fitted Encoder and Scaler for deployment.
        """
        # Ensure model directory exists
        os.makedirs(self.model_dir, exist_ok=True)

        # 1. Identify Categorical & Numerical Columns
        # Force Pclass to be string so it is treated as a category
        self.df['Pclass'] = self.df['Pclass'].astype(str)
        
        # Define strict lists
        cat_cols = ['Sex', 'Embarked', 'Pclass']
        
        # Get all other columns that are not 'Survived' and not in cat_cols
        # This ensures we capture all the new features we just created
        num_cols = [c for c in self.df.columns if c not in cat_cols and c != 'Survived']

        # --- 2. ONE-HOT ENCODING ---
        print("⚙️  Fitting OneHotEncoder...")
        encoder = OneHotEncoder(sparse_output=False, drop='first', handle_unknown='ignore')
        
        # Fit on the categorical columns
        encoded_data = encoder.fit_transform(self.df[cat_cols])
        
        # Save the Encoder!
        joblib.dump(encoder, os.path.join(self.model_dir, 'encoder.pkl'))
        
        # Create DataFrame from encoded data
        encoded_cols = encoder.get_feature_names_out(cat_cols)
        encoded_df = pd.DataFrame(encoded_data, columns=encoded_cols, index=self.df.index)
        
        # Merge: Drop old cats, add new encoded
        self.df = self.df.drop(columns=cat_cols)
        self.df = pd.concat([self.df, encoded_df], axis=1)

        # --- 3. SCALING ---
        print("⚙️  Fitting StandardScaler...")
        scaler = StandardScaler()
        
        # We need to scale the original numerical cols PLUS the new encoded cols
        features_to_scale = num_cols + list(encoded_cols)
        
        # Fit and Transform
        self.df[features_to_scale] = scaler.fit_transform(self.df[features_to_scale])
        
        # Save the Scaler!
        joblib.dump(scaler, os.path.join(self.model_dir, 'scaler.pkl'))
        
        # ALSO Save the list of feature names (Crucial for API alignment)
        joblib.dump(features_to_scale, os.path.join(self.model_dir, 'features_list.pkl'))

        print(f"✅ Data Encoded & Scaled. Artifacts saved to {self.model_dir}/")
        return self.df

    def save_split_data(self):
        target = 'Survived'
        X = self.df.drop(columns=[target])
        y = self.df[target]

        # Use stratify to ensure fair split of survivors
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        os.makedirs(self.output_dir, exist_ok=True)
        X_train.to_csv(f"{self.output_dir}/X_train.csv", index=False)
        X_test.to_csv(f"{self.output_dir}/X_test.csv", index=False)
        y_train.to_csv(f"{self.output_dir}/y_train.csv", index=False)
        y_test.to_csv(f"{self.output_dir}/y_test.csv", index=False)
        print(f"💾 Saved splits to {self.output_dir}/")

if __name__ == "__main__":
    INPUT_FILE = "src/data/processed/final.csv"
    OUTPUT_DIR = "src/data/features"

    engineer = FeatureEngineer(INPUT_FILE, OUTPUT_DIR)
    engineer.load_data()
    engineer.create_features()
    engineer.encode_and_scale()
    engineer.save_split_data()