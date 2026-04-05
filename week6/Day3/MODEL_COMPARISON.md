# Model Comparison Report

## 1. Executive Summary
We trained and evaluated four distinct models to predict Titanic survival. The goal was to balance accuracy with generalization (avoiding overfitting).

**Winner:** **Random Forest**
* **Accuracy:** 0.8329
* **ROC-AUC:** 0.8745
* **Reason for selection:** It achieved the highest scores across every single metric (Accuracy, Precision, Recall, F1, and AUC). It outperformed the boosting models (XGBoost/LightGBM) in this specific configuration, likely due to its ability to handle non-linear interactions without requiring extensive tuning.

---

## 2. Model Performance Table (5-Fold CV)

| Model | Accuracy | Precision | Recall | F1-Score | ROC-AUC |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Logistic Regression** | 0.7964 | 0.7617 | 0.6888 | 0.7213 | 0.8563 |
| **Random Forest** | **0.8329** | **0.8099** | **0.7399** | **0.7728** | **0.8745** |
| **XGBoost** | 0.8146 | 0.7777 | 0.7254 | 0.7504 | 0.8685 |
| **LightGBM** | 0.8160 | 0.7803 | 0.7290 | 0.7530 | 0.8710 |

---

## 3. Analysis by Model

### A. Logistic Regression (Baseline)
* **Strengths:** Simple and fast.
* **Weaknesses:** Lowest performance across the board (Accuracy ~79%).
* **Verdict:** Good baseline, but fails to capture the complex relationships between Age, Class, and Survival.

### B. Random Forest (The Champion)
* **Strengths:** Excellent at capturing non-linearities.
* **Performance:** It is the clear winner here. An ROC-AUC of **0.8745** is very strong for this dataset. It correctly identified 74% of survivors (Recall) while maintaining high precision (81%).

### C. XGBoost
* **Strengths:** Strong performance (Accuracy ~81.5%).
* **Weaknesses:** Slightly underperformed compared to Random Forest. This suggests it might need more hyperparameter tuning (e.g., depth, learning rate) to reach its full potential.

### D. LightGBM
* **Strengths:** Very close runner-up to Random Forest.
* **Performance:** Beat XGBoost in every metric. It is faster and often more robust out-of-the-box.

---

## 4. Visualizations

### Confusion Matrix (Best Model: Random Forest)
![Confusion Matrix](src/evaluation/confusion_matrix.png)
*Insight: The model has a high Precision (81%), meaning when it predicts "Survived", it is usually right. However, check the False Negatives—are we missing many survivors?*

