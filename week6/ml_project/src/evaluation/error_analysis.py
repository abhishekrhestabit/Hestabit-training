import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

# Load Data
X = pd.read_csv('src/data/features/X_train.csv')
y = pd.read_csv('src/data/features/y_train.csv').values.ravel()
print(f"✅ Loaded feature data: {X.shape}")

# Load the best tuned model
model = joblib.load('src/models/best_tuned_model.pkl')
print("✅ Loaded best tuned model")

# Generate predictions and calculate errors
probs = model.predict_proba(X)[:, 1] 
preds = model.predict(X)

analysis_df = X.copy()
analysis_df['Truth'] = y
analysis_df['Prediction'] = preds
analysis_df['Probability'] = probs
analysis_df['Abs_Error'] = abs(analysis_df['Truth'] - analysis_df['Probability'])

# Generate Error Analysis Heatmap
analysis_df['Age_Bin'] = pd.cut(analysis_df['Age'], bins=5)
analysis_df['Fare_Bin'] = pd.qcut(analysis_df['Fare_Log'], q=5, duplicates='drop')

heatmap_data = analysis_df.pivot_table(
    index='Age_Bin', 
    columns='Fare_Bin', 
    values='Abs_Error', 
    aggfunc='mean'
)

plt.figure(figsize=(10, 8))
sns.heatmap(heatmap_data, annot=True, cmap='coolwarm', fmt=".2f")
plt.title("Error Analysis Heatmap")
plt.xlabel("Fare Group (Quantiles)")
plt.ylabel("Age Group")
plt.savefig('src/evaluation/error_heatmap.png')
print("✅ Saved error analysis heatmap")