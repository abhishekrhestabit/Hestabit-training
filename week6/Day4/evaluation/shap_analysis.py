import shap
import pandas as pd
import matplotlib.pyplot as plt
import joblib

# Load Data
X = pd.read_csv('src/data/features/X_train.csv')
y = pd.read_csv('src/data/features/y_train.csv').values.ravel()
print(f"✅ Loaded feature data: {X.shape}")

# Load the best tuned model
model = joblib.load('src/models/best_tuned_model.pkl')
print("✅ Loaded best tuned model")

# Initialize SHAP Explainer
explainer = shap.Explainer(model)
shap_values = explainer(X)

# 1. Feature Importance Chart
plt.figure()
shap.plots.bar(shap_values, show=False)
plt.title("Feature Importance")
plt.savefig('src/evaluation/shap_importance.png', bbox_inches='tight')
print("✅ Saved feature importance chart")

# 2. SHAP Summary Plot
plt.figure()
shap.plots.beeswarm(shap_values, show=False)
plt.title("SHAP Summary Plot")
plt.savefig('src/evaluation/shap_summary.png', bbox_inches='tight')
print("✅ Saved SHAP summary plot")