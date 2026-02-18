
# Titanic Survival API - Deployment & Operations Manual

## 1. System Overview
This project serves a Machine Learning model that predicts the survival probability of Titanic passengers. It is built for production environments using **FastAPI** for high performance and **Docker** for containerization.

### Key Components
* **Model:** Random Forest Classifier (Tuned with Optuna)
* **Serving Framework:** FastAPI + Uvicorn
* **Containerization:** Docker (Python 3.9 Slim)
* **Monitoring:** Custom Drift Detection (KS-Test) & Request Logging

---

## 2. Project Structure
```text
/
├── src/
│   ├── deployment/
│   │   ├── api.py           # The FastAPI Application
│   │   └── Dockerfile       # Container Instructions
│   ├── monitoring/
│   │   ├── drift_checker.py # Data Drift Detection Script
│   │   └── dashboard.py     # (Optional) Streamlit Dashboard
│   ├── models/              # Artifacts (Model, Scaler, Encoder)
│   └── features/            # Feature Engineering Logic
├── prediction_logs.csv      # Live Request Logs (Auto-generated)
├── drift_report.json        # Drift Analysis Report (Auto-generated)
├── requirements.txt         # Python Dependencies
└── .env.example             # Environment Configuration Template

```

---

## 3. Local Installation & Setup

### Prerequisites

* Python 3.9+
* Docker (Optional, for containerization)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt

```

### Step 2: Prepare Artifacts

Ensure the model and preprocessors are built and saved in `src/models/`:

```bash
python src/features/build_features.py
# Then train your model (if not already done)

```

### Step 3: Run the API

```bash
uvicorn src.deployment.api:app --reload --host 0.0.0.0 --port 8000

```

* **Swagger UI:** [http://localhost:8000/docs]()
* **ReDoc:** [http://localhost:8000/redoc]()

---

## 4. Docker Deployment

### Step 1: Build the Image

```bash
docker build -t titanic-api:v1 .

```

### Step 2: Run the Container

```bash
docker run -p 8001:8000 titanic-api:v1

```

### Step 3: Verify Health

Visit `http://localhost:8001/` to see the API status:

```json
{"status": "online", "model_version": "v1.0.0"}

```

---

## 5. API Reference

### Endpoint: `POST /predict`

Predicts survival for a single passenger.

**Request Body:**

```json
{
  "Pclass": 3,
  "Sex": "male",
  "Age": 22,
  "Fare": 7.25,
  "SibSp": 0,
  "Parch": 0,
  "Embarked": "S"
}

```

**Response:**

```json
{
  "request_id": "a1b2c3d4-e5f6...",
  "prediction": "Died",
  "probability": 0.0451,
  "used_features": ["Age", "Fare", "FamilySize", "Sex_male", ...]
}
```

---

## 6. Monitoring & Maintenance

### Logging

All predictions are automatically logged to `prediction_logs.csv` with timestamps and request IDs.

* **Format:** `request_id, timestamp, pclass, sex, age, fare, prediction, probability`

### Drift Detection

To check if production data deviates significantly from training data:

```bash
python src/monitoring/drift_checker.py

```

* **Input:** Compares `src/data/raw/train.csv` vs `prediction_logs.csv`
* **Output:** Generates `drift_report.json`
* **Alert:** Prints `DRIFT DETECTED` if p-value < 0.05 (KS-Test).


---

## 7. Troubleshooting

**Error: "Address already in use"**

* **Fix:** Kill the process running on port 8000.
```bash
fuser -k 8000/tcp

```



**Error: "Model artifacts not found"**

* **Fix:** Run `python src/features/build_features.py` to regenerate the scaler and encoder.

**Error: "Drift Report is empty"**

* **Fix:** There was a Feature value Metadata mismatch, so it was no table to fetch it.
