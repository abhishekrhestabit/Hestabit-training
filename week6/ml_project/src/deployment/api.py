import pandas as pd
import joblib
import uuid
import datetime
import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# --- IMPORT THE CLASS ---
# We import the class so joblib can reconstruct the pipeline logic
from src.features.transformers import TitanicFeatureCreator

app = FastAPI(title="Titanic Survival API (Pipeline Version)")

# 1. Load Artifacts
try:
    print("⏳ Loading Pipeline and Model...")
    pipeline = joblib.load('src/models/pipeline.pkl')
    
    # Use best_model.pkl (Original RandomForest - 83.29% accuracy)
    model = joblib.load('src/models/best_tuned_model.pkl')
    print("✅ Loaded best_tuned_model.pkl (RandomForest - Acc: 83.29%, ROC: 0.8745)")
    print(f"✅ Model expects 11 features - Pipeline outputs: {pipeline.transform(pd.DataFrame([{'Pclass': 3, 'Sex': 'male', 'Age': 22, 'SibSp': 1, 'Parch': 0, 'Fare': 7.25, 'Embarked': 'S'}])).shape[1]} features")
    
    print("✅ Pipeline and Model Ready.")
except Exception as e:
    print(f"❌ Error loading artifacts: {e}")
    import traceback
    traceback.print_exc()
    pipeline = None
    model = None

# 2. Input Schema
class Passenger(BaseModel):
    Pclass: int
    Sex: str
    Age: float
    Fare: float
    SibSp: int = 0
    Parch: int = 0
    Embarked: str = 'S'

# 3. Logging Setup
LOG_FILE = "prediction_logs.csv"
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w") as f:
        # Headers match drift_checker.py requirements
        f.write("request_id,timestamp,pclass,sex,age,fare,prediction,probability\n")

# 4. Predict Endpoint
@app.post("/predict")
def predict(passenger: Passenger):
    if not model or not pipeline:
        raise HTTPException(status_code=503, detail="Model not loaded")

    req_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now().isoformat()
    
    try:
        # A. Create Raw DataFrame (No manual math!)
        input_dict = passenger.dict()
        input_df = pd.DataFrame([input_dict])
        
        # B. Transform Data using the Pipeline
        # This single line handles ALL math, encoding, and scaling
        processed_data = pipeline.transform(input_df)
        
        # C. Predict
        prediction = int(model.predict(processed_data)[0])
        prob = float(model.predict_proba(processed_data)[0][1])
        
        result = "Survived" if prediction == 1 else "Died"
        
        # D. Log Inputs + Outputs
        with open(LOG_FILE, "a") as f:
            f.write(f"{req_id},{timestamp},{passenger.Pclass},{passenger.Sex},{passenger.Age},{passenger.Fare},{result},{prob:.4f}\n")
            
        return {
            "request_id": req_id,
            "prediction": result,
            "probability": round(prob, 4)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def health_check():
    return {"status": "online", "model_version": "pipeline_v1"}