
# 4. Random Forest Model Interpretation (Day 4)

### **Model Configuration**

After running **Optuna** for hyperparameter tuning, the Random Forest model converged on the following optimal configuration:

```json
{
    "n_estimators": 83,
    "max_depth": 5,
    "min_samples_split": 5,
    "min_samples_leaf": 1,
    "max_features": "log2",
    "bootstrap": true,
    "criterion": "entropy"
}

```

### **Parameter Analysis: Why did these win?**

#### **1. `n_estimators`: 83**

* **What it means:** The model built exactly 83 separate decision trees.
* **Interpretation:** This is a "Goldilocks" number. It is high enough to stabilize the variance (ensuring the model isn't just guessing based on one tree's opinion) but low enough to keep prediction speed fast for the API. It suggests the Titanic dataset doesn't need thousands of trees to capture its patterns.

#### **2. `max_depth`: 5**

* **What it means:** No tree was allowed to grow deeper than 5 levels of decision-making.
* **Interpretation:**  This is the **primary guard against overfitting**.
* A depth of 5 allows the model to capture the main interactions: *Likely "Sex" -> "Pclass" -> "Age" -> "FamilySize" -> "Fare"*.
* It prevents the model from memorizing specific, rare cases (e.g., "Male, 3rd Class, Age 29, Fare 7.89").
* This shallow depth explains why the model generalizes well to the Test set.



#### **3. `max_features`: "log2"**

* **What it means:** At each split, the tree was only allowed to look at a small random subset of features (specifically,  features).
* **Interpretation:** This is critical for **Decorrelation**.
* If every tree saw "Sex" (the strongest feature), every tree would split on "Sex" first, making them all look the same.
* By forcing trees to look at random subsets (e.g., only "Age", "Fare", and "Embarked"), some trees become experts on *subtler* patterns. When voted together, this creates a much more robust "Crowd Wisdom."



#### **4. `criterion`: "entropy"**

* **What it means:** The model used **Information Gain** (Entropy) instead of Gini Impurity to decide splits.
* **Interpretation:** Entropy tends to create slightly more balanced trees. In the context of Titanic, where survival is somewhat imbalanced (~38% survived), Entropy likely did a better job of identifying splits that purely separated Survivors from Victims early in the tree.

### **Behavioral Insights**

* **Stability:** With `bootstrap: true`, each tree was trained on a slightly different random sample of passengers. This means the model is robust to outliers; a single weird passenger (e.g., a rich person in 3rd class) wouldn't ruin the entire model.
* **Conservative Predictions:** Because `min_samples_split` is 5, the model refuses to make decisions based on tiny groups of people (less than 5). This prevents it from creating "rules" for unique individuals.

### **Performance Context**

* **Validation AUC:** ~0.87 (Excellent separation between classes)
* **Accuracy:** ~83.3%
* **Summary:** The Random Forest has successfully prioritized **Generalization over Memorization**. It gives up a tiny bit of training accuracy to ensure it performs consistently on unseen data.