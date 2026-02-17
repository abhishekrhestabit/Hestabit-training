import pandas as pd
import numpy as np
import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
import datetime
import os

# 1. Initialize App
app = FastAPI(title="Titanic Survival API", version="1.0.0")

# 2. Load Artifacts (The Brains)
try:
    print("⏳ Loading artifacts...")
    model = joblib.load('src/models/best_model.pkl')
    scaler = joblib.load('src/models/scaler.pkl')
    encoder = joblib.load('src/models/encoder.pkl')
    
    # CRITICAL: Get the exact list of 11 features the model learned
    # This attribute is built-in to sklearn/XGBoost models
    if hasattr(model, 'feature_names_in_'):
        model_features = list(model.feature_names_in_)
    else:
        # Fallback: If you saved the JSON from feature_selector.py, we could load it here
        # For now, we assume the model has this attribute (standard in recent sklearn)
        raise ValueError("Model does not have 'feature_names_in_'. Please re-train model.")

    print(f"✅ Loaded. Model expects these {len(model_features)} features: {model_features}")

except Exception as e:
    print(f"❌ FATAL: Could not load artifacts. {e}")
    model_features = [] # Prevent crash on startup

# 3. Define Input Schema
class Passenger(BaseModel):
    Pclass: int
    Sex: str
    Age: float
    Fare: float
    SibSp: int = 0      # Default 0
    Parch: int = 0      # Default 0
    Embarked: str = 'S' # Default Southampton

# 4. Logging Setup
LOG_FILE = "prediction_logs.csv"
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w") as f:
        f.write("request_id,timestamp,pclass,sex,age,fare,prediction,probability\n")

# --- HELPER: FEATURE ENGINEERING (Must match build_features.py) ---
def engineer_features(df):
    # 1. Family Features
    df['FamilySize'] = df['SibSp'] + df['Parch'] + 1
    df['IsAlone'] = (df['FamilySize'] == 1).astype(int)
    df['Is_Large_Family'] = (df['FamilySize'] > 4).astype(int)

    # 2. Fare Transforms
    df['Fare_Log'] = np.log1p(df['Fare'])
    df['Fare_Per_Person'] = df['Fare'] / df['FamilySize']

    # 3. Age Transforms
    df['Is_Child'] = (df['Age'] < 10).astype(int)
    df['Is_Senior'] = (df['Age'] > 60).astype(int)
    
    # 4. Interactions
    df['Age_Class'] = df['Age'] * df['Pclass'] 
    df['Age_Fare'] = df['Age'] * df['Fare_Log']

    # 5. Polynomials
    df['Age_Sq'] = df['Age'] ** 2
    df['Fare_Sq'] = df['Fare_Log'] ** 2
    
    return df

# 5. The Prediction Endpoint
@app.post("/predict")
def predict_survival(passenger: Passenger):
    request_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now().isoformat()
    
    try:
        # A. Create Initial DataFrame
        input_data = pd.DataFrame([{
            'Pclass': passenger.Pclass,
            'Sex': passenger.Sex,
            'Age': passenger.Age,
            'Fare': passenger.Fare,
            'SibSp': passenger.SibSp,
            'Parch': passenger.Parch,
            'Embarked': passenger.Embarked
        }])
        
        # B. Feature Engineering (Creates 20+ features)
        engineered_data = engineer_features(input_data)
        
        # C. OneHotEncoding
        engineered_data['Pclass'] = engineered_data['Pclass'].astype(str)
        cat_cols = ['Sex', 'Embarked', 'Pclass']
        
        encoded_array = encoder.transform(engineered_data[cat_cols])
        encoded_cols = encoder.get_feature_names_out(cat_cols)
        encoded_df = pd.DataFrame(encoded_array, columns=encoded_cols, index=engineered_data.index)
        
        # Drop old cats and attach new ones
        engineered_data = engineered_data.drop(columns=cat_cols)
        final_df = pd.concat([engineered_data, encoded_df], axis=1)
        
        # D. Align & Scale
        # 1. Ensure columns are in the order the Scaler expects
        if hasattr(scaler, 'feature_names_in_'):
            scaler_cols = list(scaler.feature_names_in_)
            # If we are missing columns (rare), fill with 0
            for col in scaler_cols:
                if col not in final_df.columns:
                    final_df[col] = 0
            final_df = final_df[scaler_cols]
            
        # 2. Scale Everything (20 features)
        scaled_array = scaler.transform(final_df)
        scaled_df = pd.DataFrame(scaled_array, columns=final_df.columns, index=final_df.index)
        
        # --- THE FINAL FIX ---
        # E. Filter Down to the "Chosen 11"
        # We discard the 9 features the model doesn't care about
        model_input = scaled_df[model_features]

        # F. Predict
        prediction = model.predict(model_input)[0]
        prob = model.predict_proba(model_input)[0][1]
        
        result = "Survived" if prediction == 1 else "Died"

        # G. Log it
        with open(LOG_FILE, "a") as f:
            f.write(f"{request_id},{timestamp},{passenger.Pclass},{passenger.Sex},{passenger.Age},{passenger.Fare},{result},{prob:.4f}\n")

        return {
            "request_id": request_id,
            "prediction": result,
            "probability": round(prob, 4),
            "used_features": model_features # Optional: Shows you what was used
        }

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=400, detail=f"Processing error: {str(e)}")

# 6. Health Check
@app.get("/")
def home():
    return {"status": "online", "model_version": "v1.0.0"}