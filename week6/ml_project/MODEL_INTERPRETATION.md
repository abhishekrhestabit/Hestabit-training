# Model Interpretation & Tuning Report

## 1. Optimization Results (Optuna)
We moved from a baseline model to a highly tuned version using Bayesian Optimization (Optuna).

### Hyperparameter Search Space
* **Learning Rate:** Tuned between 0.01 and 0.3.
* **Max Depth:** Tuned between 3 and 10.
* **Regularization (L1/L2):** Applied to reduce overfitting.

### Best Parameters Found
```json
{
    "learning_rate": 0.07628847136718027,
    "max_depth": 3,
    "lambda": 0.03962380725939751,
    "alpha": 0.0010904173921767151,
    "subsample": 0.8514831231293083,
    "colsample_bytree": 0.6902529955804836,
    "n_estimators": 100
}