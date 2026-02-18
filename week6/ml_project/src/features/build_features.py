import pandas as pd
import joblib
import os
import sys
import json
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.features.transformers import TitanicFeatureCreator

if __name__ == "__main__":
    # 1. Load Data
    
    raw_path = "src/data/processed/final.csv"

    print(f"⏳ Loading data from {raw_path}...")
    df = pd.read_csv(raw_path)
    
    # 2. Determine Features (Draft vs Production Logic)
    feature_list_path = "src/data/features/feature_list.json"
    
    if os.path.exists(feature_list_path):
        # PRODUCTION MODE: Use the optimized list from Selector
        with open(feature_list_path, 'r') as f:
            feature_config = json.load(f)
            selected_features = feature_config['selected_features']
        print(f"✅ PRODUCTION MODE: Using top {len(selected_features)} features from JSON.")
    else:
        # DRAFT MODE: Use EVERYTHING so the Selector can choose
        print("⚠️  DRAFT MODE: feature_list.json not found.")
        print("   Selecting ALL candidate features for RFE analysis.")
        
        # We manually list everything our Transformer creates
        selected_features = [
            'Age', 'Fare', 'FamilySize', 'Fare_Log', 'Fare_Per_Person', 
            'Age_Class', 'Age_Fare', 'Age_Sq', 'Fare_Sq', 'IsAlone', 
            'Is_Child', 'Is_Senior', 
            'Sex_male', 
            'Pclass_1', 'Pclass_2', 'Pclass_3', 
            'Embarked_C', 'Embarked_Q', 'Embarked_S'
        ]
    
    # 3. Build Pipeline
    print("⚙️  Building Pipeline...")
    
    # We use ColumnTransformer to keep ONLY the selected features and scale them
    preprocessor = ColumnTransformer(
        transformers=[
            ('select_and_scale', StandardScaler(), selected_features)
        ],
        remainder='drop'  # Drop anything not in the list
    )
    
    pipeline = Pipeline(steps=[
        ('engineer', TitanicFeatureCreator()),
        ('preprocessor', preprocessor)
    ])
    
    # 4. Fit & Save
    X = df.drop('Survived', axis=1, errors='ignore')
    y = df['Survived']
    
    print("⚙️  Fitting Pipeline...")
    pipeline.fit(X, y)
    
    os.makedirs("src/models", exist_ok=True)
    joblib.dump(pipeline, "src/models/pipeline.pkl")
    print("✅ Pipeline Saved.")
    
    # 5. Save Data for Training/Selector
    X_processed = pipeline.transform(X)
    
    try:
        # Get feature names from the scaler
        feat_names = pipeline.named_steps['preprocessor'].get_feature_names_out()
        # Clean up names (StandardScaler adds "select_and_scale__" prefix sometimes)
        feat_names = [f.split('__')[-1] for f in feat_names]
    except:
        feat_names = selected_features
        
    X_df = pd.DataFrame(X_processed, columns=feat_names)
    
    X_train, X_test, y_train, y_test = train_test_split(X_df, y, test_size=0.2, random_state=42)
    
    os.makedirs("src/data/features", exist_ok=True)
    X_train.to_csv("src/data/features/X_train.csv", index=False)
    X_test.to_csv("src/data/features/X_test.csv", index=False)
    y_train.to_csv("src/data/features/y_train.csv", index=False)
    y_test.to_csv("src/data/features/y_test.csv", index=False)
    print("✅ Done.")