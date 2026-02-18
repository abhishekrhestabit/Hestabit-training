import optuna
import xgboost as xgb
import pandas as pd
import json
import os
import joblib  # Standard tool for saving models
from sklearn.model_selection import StratifiedKFold, cross_val_score

# 1. Load Data
# We tune on X_train. We keep X_test for the final evaluation later.
X = pd.read_csv('src/data/features/X_train.csv')
y = pd.read_csv('src/data/features/y_train.csv').values.ravel()

print(f"✅ Loaded training data: {X.shape}")

# Apply Feature Selection
try:
    with open('src/data/features/feature_list.json', 'r') as f:
        selected_features = json.load(f)['selected_features']
        X = X[selected_features]
        print(f"✅ Filtered to top {len(selected_features)} features.")
except FileNotFoundError:
    print("⚠️ No feature list found. Using all columns.")

# 2. Define Objective Function (The Experiment)
def objective(trial):
    param = {
        'verbosity': 0,
        'objective': 'binary:logistic',
        'eval_metric': 'auc',
        'booster': 'gbtree',
        # Optimization Space
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'lambda': trial.suggest_float('lambda', 1e-8, 1.0, log=True),
        'alpha': trial.suggest_float('alpha', 1e-8, 1.0, log=True),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'n_estimators': 100
    }

    model = xgb.XGBClassifier(**param)
    
    # Stratified K-Fold CV (Robust Testing)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(model, X, y, cv=cv, scoring='roc_auc')
    
    return scores.mean()

# 3. Run Optimization
print("🚀 Starting Optuna with 5-Fold CV & ROC-AUC...")
study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=50)

print(f"\n✅ Optimization Complete!")
print(f"Best ROC-AUC: {study.best_value:.4f}")
print(f"Best Parameters: {study.best_params}")

# 4. Save Best Parameters
os.makedirs('src/tuning', exist_ok=True)
with open('src/tuning/results.json', 'w') as f:
    json.dump(study.best_params, f, indent=4)

print("✅ Best parameters saved to src/tuning/results.json")


print("\n🔄 Retraining final model with best parameters...")

# Initialize model with the best params found by Optuna
best_params = study.best_params
best_params['n_estimators'] = 100  # Ensure we keep this consistent
best_params['objective'] = 'binary:logistic'

final_model = xgb.XGBClassifier(**best_params)

# Fit on the FULL training data
final_model.fit(X, y)

# Save to .pkl
os.makedirs('src/models', exist_ok=True)
model_path = 'src/models/best_tuned_model.pkl'
joblib.dump(final_model, model_path)

print(f"💾 Final model saved to {model_path}")