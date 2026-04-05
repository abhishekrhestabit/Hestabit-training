# Day 2 Feature engineering

## What is feature engineering

The objective of Day 2 was to transform raw data into a rich feature set capable of capturing complex, non-linear relationships. We expanded the feature space from ~8 columns to **20+ features** using domain logic, interaction terms, and polynomial expansion.

## Feature Creation Strategy

We engineered three categories of features to expose hidden patterns to the model.

- FamilySize  `SibSp + Parch + 1`  Large families struggle to evacuate; solo travelers have different risk profiles. 

- IsAlone `1` if `FamilySize == 1` else `0`  Solitary travelers may have higher agility but lower priority for lifeboats. 

- Is_Large_Family `1` if `FamilySize > 4` else `0` Families > 4 often had significantly lower survival rates. 

- Fare_Per_Person `Fare / FamilySize`  Normalizes ticket price to reveal true socio-economic status per individual. 

- Is_Child `1` if `Age < 10` else `0` Captures the "Women and Children First" policy explicitly. 

- Is_Senior `1` if `Age > 60` else `0` Captures physical vulnerability of the elderly. 
 
this was the part where we added the domain logic feature. 

Then we moved on to the Mathematical Transformation

- Fare_Log `log(Fare + 1)` `Fare` was highly right-skewed. Log-transforming normalizes the distribution for linear stability. 

- Age_Sq `Age^2` Captures non-linear risk (e.g., survival might drop sharply at very old ages). 

- Fare_Sq `Fare_Log^2` Captures non-linear wealth effects. 

Then we came to the interaction features

- Age_Class `Age * Pclass` Differentiates "Rich Young" vs. "Poor Old". A wealthy child has a different survival rate than a wealthy adult. 

- Age_Fare `Age * Fare_Log` Combines maturity with economic status. 

## Data processing pipeline

### Encoding Strategy

For the encoding strategy, I decided to use sklearn.OneHotEncoder since it is the industry standard for production pipelines. I applied this to Sex, Embarked, and Pclass, converting them into proper binary features like Sex_male. Crucially, I set drop='first' to avoid the Dummy Variable Trap, ensuring we don't introduce multicollinearity that would confuse the model.

### Scaling Strategy

I adopted StandardScaler to apply Z-Score normalization across the board for all numerical features, including the new interaction terms. This forces the data to center around a mean of 0 with a standard deviation of 1. It’s a crucial step because, without it, features with broad ranges like Age (0-80) would drown out features with smaller ranges like Fare_Log (0-6), effectively biasing the model.

--- 

## 4. Feature Selection Report (RFE)
We used `Recursive Feature Elimination` with a Random Forest estimator to select the optimal subset.

`Total Features Generated`: 20+
`Target Selection Count`: 11
`Selection Criterion`: Model Accuracy & Gini Importance

### The Top 11 Selected Features

1.  `Sex_male` (Top predictor - "Women and children first")
2.  `Fare_Per_Person` (Better wealth indicator than raw Fare)
3.  `Age_Class` (Strong interaction between status and age)
4.  `Age` (Physical capacity)
5.  `FamilySize` (Group dynamics)
6.  `Fare_Log`
7.  `Pclass_3` (Lower class indicator)
8.  `Age_Fare`
9.  `Is_Child`
10. `Fare_Sq`
11. `Embarked_S`

---