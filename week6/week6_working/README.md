

# Titanic Survival Prediction: End-to-End MLOps Pipeline

A production-ready Machine Learning API that predicts passenger survival on the Titanic. This project demonstrates a complete MLOps lifecycle, including feature engineering pipelines, model serving with FastAPI, containerization with Docker, and automated data drift monitoring.

---

## Key Features
* **Production API:** High-performance REST API built with FastAPI.
* **Robust Preprocessing:** Automated feature engineering pipeline (Scaling, Encoding, Interaction Features).
* **Containerized:** Fully Dockerized for "write once, run anywhere" deployment.
* **Monitoring System:** Real-time request logging and statistical drift detection (KS-Test).
* **Batch Processing:** Optimized endpoint for bulk predictions.

---

## Project Structure


ml_project/
├── src/
│   ├── deployment/
│   │   ├── api.py           # Main FastAPI application
│   │   └── Dockerfile       # Container configuration
│   ├── features/
│   │   └── build_features.py # Feature engineering pipeline
│   ├── models/              # Trained artifacts (best_model.pkl, scaler.pkl)
│   └── monitoring/
│       ├── drift_checker.py # Data drift detection script
│       └── dashboard.py     # (Optional) Streamlit monitor
├── prediction_logs.csv      # Live production logs
├── drift_report.json        # Drift analysis results
├── requirements.txt         # Project dependencies
└── DEPLOYMENT-NOTES.md      # Detailed operations manual



---

## Quick Start Guide

### 1. Prerequisite: Installation

Clone the repository and install the required packages.

```bash
# Create virtual environment (Optional)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

```

### 2. Build Artifacts (First Run Only)

Before running the API, generate the Scaler, Encoder, and Model artifacts.

```bash
python src/features/build_features.py
# (Optional) python src/training/train.py

```

### 3. Run Locally (FastAPI)

Start the server on port 8000.

```bash
uvicorn src.deployment.api:app --reload

```

* **Swagger Documentation:** [http://127.0.0.1:8000/docs]()

---

## 🐳 Docker Deployment

To run the application in an isolated container:

**1. Build the Image**

```bash
docker build -t titanic-api:v1 .

```

**2. Run the Container**

```bash
docker run -p 8000:8000 titanic-api:v1

```

The API is now accessible at `http://localhost:8000`.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| **GET** | `/` | Health check. Returns API status and version. |
| **POST** | `/predict` | Predict survival for a single passenger. |

### Example Request (JSON)

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

---

## 🔍 Monitoring & Observability

### 1. Live Logs

Every request is logged to **`prediction_logs.csv`** with timestamp, inputs, and prediction probability.

### 2. Drift Detection

Run the drift checker to compare production traffic against training data distributions.

```bash
python src/monitoring/drift_checker.py

```

* **Output:** Generates `drift_report.json`.
* **Logic:** Uses Kolmogorov-Smirnov test to detect significant distribution shifts (p-value < 0.05).


```