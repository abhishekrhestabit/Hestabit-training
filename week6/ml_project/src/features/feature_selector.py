import pandas as pd
import json
import os
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import RFE 

class FeatureSelector:
    def __init__(self, train_path, output_dir):
        self.train_path = train_path
        self.output_dir = output_dir
        self.X_train = None
        self.y_train = None

    def load_data(self):
        # We only need Training data for selection! 
        # Never look at Test data here (Cheating/Leakage).
        self.X_train = pd.read_csv(f"{self.train_path}/X_train.csv")
        self.y_train = pd.read_csv(f"{self.train_path}/y_train.csv").values.ravel()
        print(f"✅ Loaded Training Data: {self.X_train.shape}")

    def select_features(self, n_features=10):
        """
        Uses RFE (Recursive Feature Elimination) to pick best features.
        """
        print(f"🔍 Selecting Top {n_features} features...")
        
        # Estimator: Random Forest (Good at finding non-linear relationships)
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        
        # RFE: Recursively removes weakest features until n_features remain
        rfe = RFE(estimator=model, n_features_to_select=n_features)
        rfe.fit(self.X_train, self.y_train)

        # Get the selected feature names
        selected_cols = self.X_train.columns[rfe.support_].tolist()
        
        print(f"✨ Selected Features: {selected_cols}")
        return selected_cols, rfe

    def save_results(self, selected_cols):
        """
        Saves the list of best features to a JSON file.
        """
        output_path = f"{self.output_dir}/feature_list.json"
        with open(output_path, 'w') as f:
            json.dump({"selected_features": selected_cols}, f, indent=4)
        print(f"💾 Feature list saved to {output_path}")

    def plot_importance(self, rfe_model):
        """
        Optional: Plots the importance of selected features.
        """
        # RFE doesn't give "importance" directly, but the internal model does
        # We re-fit the model on just the selected features to get importances
        selected_X = self.X_train.loc[:, rfe_model.support_]
        model = rfe_model.estimator_
        model.fit(selected_X, self.y_train)

        importances = pd.Series(model.feature_importances_, index=selected_X.columns)
        importances.sort_values().plot(kind='barh', color='teal')
        plt.title("Feature Importance (Top Selected)")
        plt.xlabel("Importance Score")
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/feature_importance.png")
        print("📊 Importance plot saved.")

if __name__ == "__main__":
    TRAIN_DIR = "src/data/processed"
    
    # Run the Selector
    selector = FeatureSelector(TRAIN_DIR, TRAIN_DIR)
    selector.load_data()
    
    # Select Top 7 features (You can change this number)
    best_features, rfe_model = selector.select_features(n_features=7)
    
    selector.save_results(best_features)
    selector.plot_importance(rfe_model)