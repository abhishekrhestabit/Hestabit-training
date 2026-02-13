import pandas as pd
import numpy as np
import pickle
import json
import os
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import confusion_matrix, classification_report

class ModelTrainer:
    def __init__(self, input_dir, output_model_dir, output_eval_dir):
        self.input_dir = input_dir
        self.model_dir = output_model_dir
        self.eval_dir = output_eval_dir
        self.models = {
            'LogisticRegression': LogisticRegression(max_iter=1000, random_state=42),
            'RandomForest': RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42),
            'XGBoost': XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42),
            'LightGBM': LGBMClassifier(random_state=42, verbose=-1)
        }
        self.results = {}
        
        # Ensure directories exist
        os.makedirs(self.model_dir, exist_ok=True)
        os.makedirs(self.eval_dir, exist_ok=True)

    def load_data(self):
        """Loads the processed X_train and y_train from Day 2."""
        self.X_train = pd.read_csv(f"{self.input_dir}/X_train.csv")
        self.y_train = pd.read_csv(f"{self.input_dir}/y_train.csv").values.ravel()
        
        # Load test set for final confusion matrix (optional but good practice)
        self.X_test = pd.read_csv(f"{self.input_dir}/X_test.csv")
        self.y_test = pd.read_csv(f"{self.input_dir}/y_test.csv").values.ravel()
        
        # Select only the features chosen in Day 2 (if feature_list.json exists)
        try:
            with open(f"{self.input_dir}/feature_list.json", 'r') as f:
                selected_features = json.load(f)['selected_features']
                self.X_train = self.X_train[selected_features]
                self.X_test = self.X_test[selected_features]
                print(f"✅ filtered to top {len(selected_features)} features.")
        except FileNotFoundError:
            print("⚠️ No feature list found. Using all columns.")

    def train_and_evaluate(self):
        """
        Trains 4 models using 5-Fold Cross-Validation.
        Returns: A dictionary of metrics.
        """
        print("🚀 Starting Cross-Validation Training...")
        
        # 5-Fold Stratified CV (Ensures balanced classes in every fold)
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        
        # Metrics to track
        scoring = ['accuracy', 'precision', 'recall', 'f1', 'roc_auc']

        for name, model in self.models.items():
            print(f"   ... Training {name}")
            scores = cross_validate(model, self.X_train, self.y_train, cv=cv, scoring=scoring)
            
            # Store mean scores
            self.results[name] = {
                'Accuracy': np.mean(scores['test_accuracy']),
                'Precision': np.mean(scores['test_precision']),
                'Recall': np.mean(scores['test_recall']),
                'F1_Score': np.mean(scores['test_f1']),
                'ROC_AUC': np.mean(scores['test_roc_auc'])
            }
            
        print("✅ Training Complete.")
        return self.results

    def save_best_model(self):
        """
        Selects the best model based on ROC_AUC and saves it.
        """
        # Find best model based on ROC_AUC
        best_name = max(self.results, key=lambda x: self.results[x]['ROC_AUC'])
        best_score = self.results[best_name]['ROC_AUC']
        
        print(f"🏆 BEST MODEL: {best_name} (ROC-AUC: {best_score:.4f})")
        
        # Retrain best model on FULL training data
        best_model = self.models[best_name]
        best_model.fit(self.X_train, self.y_train)
        
        # Save .pkl
        model_path = f"{self.model_dir}/best_model.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(best_model, f)
        print(f"💾 Saved model to {model_path}")
        
        return best_name, best_model

    def save_metrics(self):
        """Saves the comparison metrics to JSON."""
        metrics_path = f"{self.eval_dir}/metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump(self.results, f, indent=4)
        print(f"📊 Saved metrics to {metrics_path}")

    def plot_confusion_matrix(self, model, model_name):
        """Plots the Confusion Matrix for the Best Model on Test Data."""
        y_pred = model.predict(self.X_test)
        cm = confusion_matrix(self.y_test, y_pred)
        
        plt.figure(figsize=(6,5))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False)
        plt.title(f"Confusion Matrix: {model_name}")
        plt.ylabel("Actual")
        plt.xlabel("Predicted")
        
        plot_path = f"{self.eval_dir}/confusion_matrix.png"
        plt.savefig(plot_path)
        print(f"🖼️ Saved confusion matrix to {plot_path}")

if __name__ == "__main__":
    # Define Paths
    INPUT_DIR = "src/data/features"
    MODEL_DIR = "src/models"     # Maps to /models
    EVAL_DIR = "src/evaluation"  # Maps to /evaluation
    
    trainer = ModelTrainer(INPUT_DIR, MODEL_DIR, EVAL_DIR)
    trainer.load_data()
    trainer.train_and_evaluate()
    trainer.save_metrics()
    best_name, best_model = trainer.save_best_model()
    trainer.plot_confusion_matrix(best_model, best_name)