import pandas as pd
import json
import os
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import RFE

class FeatureSelector:
    def __init__(self, train_path, output_dir):
        self.train_path = train_path
        self.output_dir = output_dir
        self.X_train = None
        self.y_train = None

    def load_data(self):
        try:
            self.X_train = pd.read_csv(f"{self.train_path}/X_train.csv")
            self.y_train = pd.read_csv(f"{self.train_path}/y_train.csv").values.ravel()
            print(f"✅ Loaded Training Data. Total Features Available: {self.X_train.shape[1]}")
        except FileNotFoundError:
            print("❌ File not found. Run build_features.py first.")
            exit()

    def select_features(self, n_features=11):
        """
        Selects the Top 11 Features.
        """
        print(f"🔍 Starting RFE to find top {n_features} features...")
        
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        rfe = RFE(estimator=model, n_features_to_select=n_features)
        rfe.fit(self.X_train, self.y_train)

        selected_cols = self.X_train.columns[rfe.support_].tolist()
        
        print(f"✨ The Chosen 11: {selected_cols}")
        return selected_cols, rfe

    def save_results(self, selected_cols):
        output_path = f"{self.output_dir}/feature_list.json"
        with open(output_path, 'w') as f:
            json.dump({"selected_features": selected_cols}, f, indent=4)
        print(f"💾 Saved list to {output_path}")

    def plot_importance(self, rfe_model):
        selected_X = self.X_train.loc[:, rfe_model.support_]
        model = rfe_model.estimator_
        model.fit(selected_X, self.y_train)
        
        importances = pd.Series(model.feature_importances_, index=selected_X.columns)
        
        plt.figure(figsize=(10, 8))
        importances.sort_values().plot(kind='barh', color='#ff6b6b')
        plt.title("Top 11 Features by Importance")
        plt.xlabel("Importance Score")
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/feature_importance.png")
        print("📊 Plot saved.")

if __name__ == "__main__":
    TRAIN_DIR = "src/data/features"
    
    selector = FeatureSelector(TRAIN_DIR, TRAIN_DIR)
    selector.load_data()
    # Explicitly asking for 11 features
    best_features, rfe_model = selector.select_features(n_features=11)
    selector.save_results(best_features)
    selector.plot_importance(rfe_model)