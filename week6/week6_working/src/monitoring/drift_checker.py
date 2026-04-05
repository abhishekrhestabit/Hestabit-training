import pandas as pd
import numpy as np
from scipy.stats import ks_2samp
import json
import os

class DriftChecker:
    def __init__(self, train_path, log_path, report_path):
        self.train_path = train_path
        self.log_path = log_path
        self.report_path = report_path
        
    def check_drift(self):
        print("Checking for Data Drift...")
        
        # 1. Load Data
        try:
            # Reference Data (Baseline)
            # We must load the RAW data to compare with RAW logs
            if not os.path.exists(self.train_path):
                print(f"Training data not found at {self.train_path}")
                print("   Please update TRAIN_DATA in the script to point to your original 'train.csv'.")
                return

            train_df = pd.read_csv(self.train_path)
            
            # Current Data (Production Logs)
            if not os.path.exists(self.log_path):
                print("No prediction logs found yet. Skipping check.")
                return
            
            log_df = pd.read_csv(self.log_path)
            
            # Filter out empty rows or headers just in case
            log_df = log_df.dropna(subset=['age', 'fare'])
            
            if len(log_df) < 10:
                print(f"Not enough log data (Found {len(log_df)} samples, need > 10).")
                return
                
        except Exception as e:
            print(f"Error loading data: {e}")
            return

        # 2. Define features to monitor
        # Key = Column Name in Train.csv (Usually Title Case)
        # Value = Column Name in prediction_logs.csv (Lowercase)
        monitor_cols = {
            'Age': 'age',
            'Fare': 'fare',
            'Pclass': 'pclass'
        }
        
        drift_report = {}
        drift_detected = False

        print(f"📊 Comparing {len(train_df)} training samples vs {len(log_df)} production samples.")

        # 3. Statistical Test (Kolmogorov-Smirnov Test)
        for train_col, log_col in monitor_cols.items():
            
            # Check if columns exist
            if train_col not in train_df.columns:
                print(f"Column '{train_col}' missing in Training Data. Skipping.")
                continue
            if log_col not in log_df.columns:
                print(f"Column '{log_col}' missing in Logs. Skipping.")
                continue
                
            # Get the two distributions (Cleaned)
            train_dist = train_df[train_col].dropna().astype(float)
            log_dist = log_df[log_col].dropna().astype(float)

            # Run KS Test
            # p-value < 0.05 means "significantly different" (Drift Detected)
            statistic, p_value = ks_2samp(train_dist, log_dist)
            
            is_drift = p_value < 0.05
            
            drift_report[train_col] = {
                "p_value": float(round(p_value, 4)),
                "drift_detected": bool(is_drift),
                "train_mean": float(round(train_dist.mean(), 2)),
                "prod_mean": float(round(log_dist.mean(), 2)),
                "train_std": float(round(train_dist.std(), 2)),
                "prod_std": float(round(log_dist.std(), 2))
            }
            
            if is_drift:
                drift_detected = True
                print(f"DRIFT DETECTED in {train_col}! (p={p_value:.4f})")
                print(f"   Train Mean: {train_dist.mean():.2f} vs Prod Mean: {log_dist.mean():.2f}")
            else:
                print(f"{train_col} is stable. (p={p_value:.4f})")

        # 4. Save Report
        with open(self.report_path, "w") as f:
            json.dump(drift_report, f, indent=4)
        
        print(f"Drift report saved to {self.report_path}")

if __name__ == "__main__":
    # --- CONFIGURATION ---
    # 1. Point this to your ORIGINAL RAW DATA (Not X_train.csv!)
    #    This file should have real ages (22, 30) and real fares (7.25, 50.0).
    TRAIN_DATA = "src/data/raw/train.csv" 
    
    # If "src/data/raw/train.csv" doesn't exist, try "src/data/processed/final.csv"
    if not os.path.exists(TRAIN_DATA):
        TRAIN_DATA = "src/data/processed/final.csv"

    # 2. Path to your logs
    LOG_DATA = "prediction_logs.csv" 
    
    # 3. Output file
    REPORT_FILE = "drift_report.json"

    checker = DriftChecker(TRAIN_DATA, LOG_DATA, REPORT_FILE)
    checker.check_drift()