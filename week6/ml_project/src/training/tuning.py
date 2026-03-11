import optuna
import pandas as pd
import json
import os
import joblib  # Standard tool for saving models
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score

# 1. Load Data
# We tune on X_train. We keep X_test for the final evaluation later.
try:
    X = pd.read_csv('src/data/features/X_train.csv')
    y = pd.read_csv('src/data/features/y_train.csv').values.ravel()
    print(f"Loaded training data: {X.shape}")
except FileNotFoundError:
    print("Data not found! Run src/features/build_features.py first.")
    exit()

# Apply Feature Selection (Filter to the Chosen 11 or similar)
try:
    feature_list_path = 'src/data/features/feature_list.json'
    if os.path.exists(feature_list_path):
        with open(feature_list_path, 'r') as f:
            data = json.load(f)
            # Handle both list format and dict format just in case
            selected_features = data['selected_features'] if isinstance(data, dict) else data
            
        # Ensure we only keep columns that actually exist in X
        valid_features = [f for f in selected_features if f in X.columns]
        X = X[valid_features]
        print(f"Filtered to top {len(valid_features)} features.")
    else:
        print("No feature list found. Using all columns.")
except Exception as e:
    print(f"Warning loading features: {e}. Using all columns.")

# 2. Define Objective Function (The Experiment)
def objective(trial):
    # Random Forest Hyperparameters
    param = {
        'n_estimators': trial.suggest_int('n_estimators', 50, 300),
        'max_depth': trial.suggest_int('max_depth', 3, 20),
        'min_samples_split': trial.suggest_int('min_samples_split', 2, 15),
        'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 10),
        'max_features': trial.suggest_categorical('max_features', ['sqrt', 'log2', None]),
        'bootstrap': trial.suggest_categorical('bootstrap', [True, False]),
        'criterion': trial.suggest_categorical('criterion', ['gini', 'entropy']),
        'random_state': 42,
        'n_jobs': -1  # Use all CPU cores
    }

    model = RandomForestClassifier(**param)
    
    # Stratified K-Fold CV (Robust Testing)
    # We use 5 folds to be sure the score is stable
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    # We optimize for ROC-AUC (Area Under Curve)
    scores = cross_val_score(model, X, y, cv=cv, scoring='roc_auc')
    
    return scores.mean()

# 3. Run Optimization
print("Starting Optuna with Random Forest (5-Fold CV)...")
study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=30)  # 30 trials is usually enough for RF

print(f"\nOptimization Complete!")
print(f"Best ROC-AUC: {study.best_value:.4f}")
print(f"Best Parameters: {study.best_params}")

# 4. Save Best Parameters
os.makedirs('src/tuning', exist_ok=True)
with open('src/tuning/results.json', 'w') as f:
    json.dump(study.best_params, f, indent=4)

print("Best parameters saved to src/tuning/results.json")

# 5. Retrain Final Model
print("\nRetraining final model with best parameters...")

best_params = study.best_params
# Add fixed params back in
best_params['random_state'] = 42
best_params['n_jobs'] = -1

final_model = RandomForestClassifier(**best_params)

# Fit on the FULL training data (X_train)
final_model.fit(X, y)

# Save to .pkl
os.makedirs('src/models', exist_ok=True)
model_path = 'src/models/best_tuned_model.pkl'  # Overwrite best_model.pkl so API uses it
joblib.dump(final_model, model_path)

print(f"Final model saved to {model_path}")